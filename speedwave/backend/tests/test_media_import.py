"""Platform import (yt-dlp) tests. yt-dlp is replaced by a fake, so no network is used."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import media_import, url_import
from app.config import settings
from app.main import app
from tests.signals import stereo_test_signal, write_audio


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    old = settings.data_dir
    settings.data_dir = tmp_path_factory.mktemp("data")
    with TestClient(app) as c:
        yield c
    settings.data_dir = old


@pytest.fixture(scope="module")
def webm(tmp_path_factory) -> Path:
    d = tmp_path_factory.mktemp("src")
    return write_audio(d / "clip.webm", stereo_test_signal(6.0), codec_args=["-c:a", "libopus", "-b:a", "160k"])


class FakeYDL:
    """Stands in for yt_dlp.YoutubeDL: returns `info`, 'downloads' `file`, raises `error`."""

    info: dict = {}
    file: Path | None = None
    error: Exception | None = None

    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=False):
        if FakeYDL.error:
            raise FakeYDL.error
        return dict(FakeYDL.info)

    def process_ie_result(self, info, download=True):
        assert self.opts["allowed_extractors"] == ["default", "-generic"]
        assert self.opts["noplaylist"] is True and "cookiefile" not in self.opts
        dest = Path(self.opts["outtmpl"]["default"].replace("%(ext)s", FakeYDL.file.suffix.lstrip(".")))
        size = FakeYDL.file.stat().st_size
        for hook in self.opts["progress_hooks"]:
            hook({"status": "downloading", "downloaded_bytes": size // 2, "total_bytes": size, "speed": 1e6, "eta": 1})
            time.sleep(0.2)
        shutil.copy(FakeYDL.file, dest)
        return info


@pytest.fixture
def fake_ydl(monkeypatch, webm):
    FakeYDL.info = {"title": "Lagu Raya. ", "duration": 6, "uploader": "Someone"}
    FakeYDL.file, FakeYDL.error = webm, None
    monkeypatch.setattr(media_import.yt_dlp, "YoutubeDL", FakeYDL)
    monkeypatch.setattr(url_import, "_check_host_is_public", lambda host, port: None)
    return FakeYDL


def wait(client, import_id):
    for _ in range(200):
        t = client.get(f"/api/imports/{import_id}").json()
        if t["status"] not in ("downloading", "analyzing"):
            return t
        time.sleep(0.05)
    raise AssertionError("import did not finish")


@pytest.mark.parametrize(
    "url,name",
    [
        ("https://www.youtube.com/watch?v=jNQXAC9IVRw", "YouTube"),
        ("https://youtu.be/jNQXAC9IVRw", "YouTube"),
        ("https://soundcloud.com/artist/some-track", "SoundCloud"),
        ("https://vimeo.com/76979871", "Vimeo"),
        ("https://archive.org/details/MLKDream", "Archive.org"),
    ],
)
def test_platform_detection(url, name):
    assert url_import.source_kind(url) == ("platform", name)


def test_non_platform_links_stay_direct():
    assert url_import.source_kind("https://cdn.example.com/a.mp3") == ("direct", None)
    assert url_import.source_kind("https://drive.google.com/file/d/1AbCdEfGhIjKlMnOp/view")[1] == "Google Drive"


@pytest.mark.parametrize("url", ["https://open.spotify.com/track/123", "https://music.apple.com/us/album/x/1",
                                 "https://www.deezer.com/track/1", "https://tidal.com/browse/track/1"])
def test_drm_services_refused(client, url):
    r = client.post("/api/imports", json={"url": url})
    assert r.status_code == 422 and "drm" in r.json()["detail"].lower()


def test_youtube_import_flow_then_convert(client, fake_ydl):
    r = client.post("/api/imports", json={"url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"})
    assert r.status_code == 202
    first = r.json()
    assert first["kind"] == "platform" and first["platform"] == "YouTube"
    t = wait(client, first["id"])
    assert t["status"] == "completed", t["error"]
    src = t["source"]
    assert src["filename"] == "Lagu Raya.webm" and src["format"] == "WEBM" and src["origin"] == "platform"
    assert src["duration"] == pytest.approx(6.0, abs=0.1)
    assert client.get(src["preview_url"]).headers["content-type"] == "audio/webm"
    job = client.post("/api/jobs", json={"source_id": src["id"], "formats": ["mp3"]}).json()
    for _ in range(300):
        job = client.get(f"/api/jobs/{job['id']}").json()
        if job["status"] in ("completed", "failed"):
            break
        time.sleep(0.05)
    assert job["status"] == "completed"
    assert job["outputs"]["mp3"]["filename"] == "Lagu Raya_2x.mp3"
    assert job["outputs"]["mp3"]["duration"] == pytest.approx(3.0, abs=0.1)


def test_import_reports_progress(client, fake_ydl):
    t = client.post("/api/imports", json={"url": "https://youtu.be/jNQXAC9IVRw"}).json()
    time.sleep(0.1)
    mid = client.get(f"/api/imports/{t['id']}").json()
    assert mid["progress"] == pytest.approx(0.5, abs=0.01) or mid["status"] != "downloading"
    assert wait(client, t["id"])["status"] == "completed"


@pytest.mark.parametrize(
    "info,fragment",
    [
        ({"_type": "playlist", "entries": []}, "playlist"),
        ({"title": "x", "is_live": True}, "live"),
        ({"title": "x", "_has_drm": True}, "drm"),
        ({"title": "x", "duration": 10**7}, "limit"),
    ],
)
def test_rejected_media(client, fake_ydl, info, fragment):
    fake_ydl.info = info
    t = wait(client, client.post("/api/imports", json={"url": "https://youtu.be/jNQXAC9IVRw"}).json()["id"])
    assert t["status"] == "failed" and fragment in t["error"].lower()


@pytest.mark.parametrize(
    "message,fragment",
    [
        ("ERROR: [youtube] x: Sign in to confirm you’re not a bot. Use --cookies", "not a bot"),
        ("ERROR: [youtube] x: Private video. Sign in if you've been granted access", "private"),
        ("ERROR: [youtube] x: Sign in to confirm your age. This video may be inappropriate", "age-restricted"),
        ("ERROR: unable to download video data: HTTP Error 403: Forbidden", "403"),
        ("ERROR: [youtube] x: Video unavailable", "unavailable"),
        ("ERROR: Unsupported URL: https://x", "isn't supported"),
        ("ERROR: [youtube] x: This video is DRM protected", "drm"),
    ],
)
def test_error_messages(client, fake_ydl, message, fragment):
    fake_ydl.error = media_import.DownloadError(message)
    t = wait(client, client.post("/api/imports", json={"url": "https://youtu.be/jNQXAC9IVRw"}).json()["id"])
    assert t["status"] == "failed"
    assert fragment in t["error"].lower()


def test_cancel_import(client, fake_ydl):
    t = client.post("/api/imports", json={"url": "https://youtu.be/jNQXAC9IVRw"}).json()
    client.post(f"/api/imports/{t['id']}/cancel")
    assert wait(client, t["id"])["status"] in ("cancelled", "completed")


def test_imports_are_session_scoped(client, fake_ydl):
    t = client.post("/api/imports", json={"url": "https://youtu.be/jNQXAC9IVRw"}).json()
    with TestClient(app) as other:
        assert other.get(f"/api/imports/{t['id']}").status_code == 404
    wait(client, t["id"])


def test_direct_url_via_background_import(client, monkeypatch, tmp_path, webm):
    def fake_download(url, dest, on_progress=None, cancel=None):
        p = dest / "source.webm"
        shutil.copy(webm, p)
        on_progress and on_progress(p.stat().st_size, p.stat().st_size, None, None)
        return p, "clip.webm", p.stat().st_size

    monkeypatch.setattr(url_import, "download", fake_download)
    t = wait(client, client.post("/api/imports", json={"url": "https://cdn.example.com/clip.webm"}).json()["id"])
    assert t["status"] == "completed" and t["kind"] == "direct" and t["progress"] == 1.0


def test_config_reports_platform_support(client):
    c = client.get("/api/config").json()
    assert c["platform_import"]["enabled"] is True and c["platform_import"]["yt_dlp"]
    assert "WEBM" in c["input_formats"]
