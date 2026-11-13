"""End-to-end API tests: upload/URL import -> process -> poll -> download."""

from __future__ import annotations

import hashlib
import http.server
import socketserver
import threading
import time
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import url_import
from app.config import settings
from app.main import app
from app.store import store
from tests.signals import SR, decode, dominant_frequency, probe, steady, stereo_test_signal, write_audio


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    old = settings.data_dir
    settings.data_dir = d
    yield d
    settings.data_dir = old


@pytest.fixture(scope="module")
def client(data_dir):
    # One client (= one event loop and one browser session) for the module.
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def signals(tmp_path_factory) -> dict[str, Path]:
    d = tmp_path_factory.mktemp("in")
    base = write_audio(d / "song.wav", stereo_test_signal(20.0))
    files = {"wav": base}
    for ext, args in {
        "mp3": ["-c:a", "libmp3lame", "-b:a", "192k"],
        "ogg": ["-c:a", "libvorbis", "-q:a", "5"],
        "flac": ["-c:a", "flac"],
        "m4a": ["-c:a", "aac", "-b:a", "192k"],
        "aac": ["-c:a", "aac", "-b:a", "192k", "-f", "adts"],
    }.items():
        import subprocess

        out = d / f"song.{ext}"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(base), *args, str(out)], check=True)
        files[ext] = out
    return files


def upload(client, path: Path, name: str | None = None):
    with open(path, "rb") as f:
        return client.post("/api/sources/upload", files={"file": (name or path.name, f, "application/octet-stream")})


def wait_for(client, job_id: str, timeout: float = 120) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] not in ("queued", "processing", "finalizing"):
            return job
        time.sleep(0.2)
    raise AssertionError("job did not finish")


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] and body["rubberband"] and body["rubberband_engine"] == "R3 (finer)"


@pytest.mark.parametrize("ext,label", [("wav", "WAV"), ("mp3", "MP3"), ("ogg", "OGG"), ("flac", "FLAC"), ("m4a", "M4A"), ("aac", "AAC")])
def test_upload_every_supported_format(client, signals, ext, label):
    r = upload(client, signals[ext])
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["format"] == label
    assert body["channels"] == 2
    assert body["duration"] == pytest.approx(20.0, abs=0.1)
    assert body["filename"] == f"song.{ext}"
    # Preview of the original is served, with seeking (Range) support.
    prev = client.get(body["preview_url"], headers={"Range": "bytes=0-99"})
    assert prev.status_code == 206 and prev.headers["content-type"].startswith("audio/")


def test_full_conversion_flow(client, signals, tmp_path):
    src = upload(client, signals["flac"], "My Track.flac").json()
    original_hash = hashlib.sha256(store.sources[src["id"]].path.read_bytes()).hexdigest()

    r = client.post("/api/jobs", json={"source_id": src["id"], "formats": ["mp3", "ogg"]})
    assert r.status_code == 202
    job = r.json()
    assert job["settings"]["speed"] == 2.0 and job["settings"]["mp3_bitrate"] == 320
    assert not job["duplicate"]

    seen_progress = []
    deadline = time.time() + 60
    while time.time() < deadline:
        j = client.get(f"/api/jobs/{job['id']}").json()
        seen_progress.append(j["progress"])
        if j["status"] in ("completed", "failed"):
            break
        time.sleep(0.05)
    assert j["status"] == "completed", j["error"]
    assert seen_progress == sorted(seen_progress)
    assert j["original_duration"] == pytest.approx(20.0, abs=0.05)

    for fmt, mime, codec in (("mp3", "audio/mpeg", "mp3"), ("ogg", "audio/ogg", "vorbis")):
        out = j["outputs"][fmt]
        assert out["filename"] == f"My Track_2x.{fmt}"
        assert out["duration"] == pytest.approx(10.0, abs=0.1)
        dl = client.get(out["download_url"])
        assert dl.status_code == 200
        assert dl.headers["content-type"] == mime
        assert dl.headers["content-disposition"].startswith("attachment;")
        assert f"My%20Track_2x.{fmt}" in dl.headers["content-disposition"]
        p = tmp_path / out["filename"]
        p.write_bytes(dl.content)
        meta = probe(p)
        assert meta["codec"] == codec and meta["channels"] == 2
        x = steady(decode(p))
        assert dominant_frequency(x[:, 0]) == pytest.approx(440.0, rel=0.003)
        assert dominant_frequency(x[:, 1]) == pytest.approx(660.0, rel=0.003)
        inline = client.get(out["preview_url"])
        assert inline.headers["content-disposition"].startswith("inline;")
        wf = client.get(out["waveform_url"]).json()["peaks"]
        assert len(wf) > 100 and max(wf) == 1.0

    # The original upload is untouched and read-only.
    path = store.sources[src["id"]].path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original_hash
    assert not (path.stat().st_mode & 0o222)


def test_duplicate_requests_return_same_job(client, signals):
    src = upload(client, signals["wav"]).json()
    body = {"source_id": src["id"], "formats": ["ogg", "mp3"], "mp3_bitrate": 256}
    a = client.post("/api/jobs", json=body).json()
    b = client.post("/api/jobs", json={**body, "formats": ["mp3", "ogg"]}).json()
    assert b["id"] == a["id"] and b["duplicate"] is True
    wait_for(client, a["id"])
    # A different setting is a different job.
    c = client.post("/api/jobs", json={**body, "mp3_bitrate": 192}).json()
    assert c["id"] != a["id"] and not c["duplicate"]
    assert wait_for(client, c["id"])["status"] == "completed"


def test_speed_option_and_filename(client, signals):
    src = upload(client, signals["wav"]).json()
    j = client.post("/api/jobs", json={"source_id": src["id"], "speed": 1.5, "formats": ["ogg"]}).json()
    j = wait_for(client, j["id"])
    assert j["outputs"]["ogg"]["filename"] == "song_1.5x.ogg"
    assert j["outputs"]["ogg"]["duration"] == pytest.approx(20.0 / 1.5, abs=0.1)


def test_sessions_are_isolated(client, signals, data_dir):
    src = upload(client, signals["wav"]).json()
    j = client.post("/api/jobs", json={"source_id": src["id"], "formats": ["mp3"]}).json()
    wait_for(client, j["id"])
    with TestClient(app) as other:  # a different browser: new session cookie
        assert other.get(f"/api/sources/{src['id']}").status_code == 404
        assert other.get(f"/api/sources/{src['id']}/audio").status_code == 404
        assert other.get(f"/api/jobs/{j['id']}").status_code == 404
        assert other.get(f"/api/jobs/{j['id']}/download/mp3").status_code == 404
        assert other.post("/api/jobs", json={"source_id": src["id"]}).status_code == 404


def test_rejects_unsupported_extension(client, tmp_path):
    p = tmp_path / "notes.txt"
    p.write_text("hello")
    assert upload(client, p).status_code == 415


def test_rejects_corrupted_file(client, tmp_path):
    p = tmp_path / "broken.mp3"
    p.write_bytes(np.random.default_rng(1).bytes(200_000))
    r = upload(client, p)
    assert r.status_code == 422
    assert "corrupt" in r.json()["detail"].lower() or "could not be read" in r.json()["detail"].lower()


def test_rejects_truncated_flac(client, signals, tmp_path):
    data = signals["flac"].read_bytes()
    p = tmp_path / "trunc.flac"
    p.write_bytes(data[:60])  # header only
    assert upload(client, p).status_code == 422


def test_rejects_empty_and_oversized(client, tmp_path, signals, monkeypatch):
    empty = tmp_path / "empty.wav"
    empty.write_bytes(b"")
    assert upload(client, empty).status_code == 422
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    r = upload(client, signals["wav"])  # ~3.5 MB
    assert r.status_code == 413


def test_invalid_job_settings(client, signals):
    src = upload(client, signals["wav"]).json()
    assert client.post("/api/jobs", json={"source_id": src["id"], "speed": 9}).status_code == 422
    assert client.post("/api/jobs", json={"source_id": src["id"], "mp3_bitrate": 999}).status_code == 422
    assert client.post("/api/jobs", json={"source_id": src["id"], "formats": ["wma"]}).status_code == 422
    assert client.post("/api/jobs", json={"source_id": "nope-nope-nope-nope"}).status_code == 404


def test_cancel_job(client, tmp_path):
    long = write_audio(tmp_path / "long.wav", stereo_test_signal(240.0))
    src = upload(client, long).json()
    j = client.post("/api/jobs", json={"source_id": src["id"], "formats": ["mp3", "ogg"]}).json()
    time.sleep(0.5)
    client.post(f"/api/jobs/{j['id']}/cancel")
    j = wait_for(client, j["id"])
    assert j["status"] == "cancelled"
    assert j["outputs"] == {}
    assert client.get(f"/api/jobs/{j['id']}/download/mp3").status_code == 404


def test_delete_source_removes_files(client, signals):
    src = upload(client, signals["wav"]).json()
    d = store.sources[src["id"]].dir
    assert d.exists()
    assert client.delete(f"/api/sources/{src['id']}").status_code == 204
    assert not d.exists()
    assert client.get(f"/api/sources/{src['id']}").status_code == 404


def test_expired_files_cleaned_up(client, signals, monkeypatch):
    src = upload(client, signals["wav"]).json()
    s = store.sources[src["id"]]
    s.last_access = time.time() - 10 * 3600
    store.cleanup_expired()
    assert src["id"] not in store.sources and not s.dir.exists()


# ------------------------------------------------------------------------------ URL import


class _Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/page":
            body = b"<html>not audio</html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/private.mp3":
            self.send_response(401)
            self.end_headers()
        elif self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/files/song.mp3")
            self.end_headers()
        elif self.path == "/download?id=7":
            body = Path(self.directory, "files", "song.ogg").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", 'attachment; filename="Night Drive.ogg"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()


@pytest.fixture(scope="module")
def http_server(signals, tmp_path_factory):
    root = tmp_path_factory.mktemp("www")
    (root / "files").mkdir()
    for ext in ("mp3", "ogg"):
        (root / "files" / f"song.{ext}").write_bytes(signals[ext].read_bytes())
    (root / "files" / "fake.mp3").write_bytes(b"this is not audio at all" * 100)
    handler = lambda *a, **k: _Handler(*a, directory=str(root), **k)  # noqa: E731
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture
def allow_local(monkeypatch):
    monkeypatch.setattr(settings, "allow_private_urls", True)
    monkeypatch.setattr(settings, "url_trust_env", False)


def test_url_import_and_convert(client, http_server, allow_local):
    r = client.post("/api/sources/url", json={"url": f"{http_server}/files/song.mp3"})
    assert r.status_code == 201, r.text
    src = r.json()
    assert src["format"] == "MP3" and src["origin"] == "url" and src["filename"] == "song.mp3"
    j = client.post("/api/jobs", json={"source_id": src["id"], "formats": ["mp3"]}).json()
    j = wait_for(client, j["id"])
    assert j["status"] == "completed"
    assert j["outputs"]["mp3"]["duration"] == pytest.approx(10.0, abs=0.1)


def test_url_import_follows_redirect_and_content_disposition(client, http_server, allow_local):
    assert client.post("/api/sources/url", json={"url": f"{http_server}/redirect"}).status_code == 201
    r = client.post("/api/sources/url", json={"url": f"{http_server}/download?id=7"})
    assert r.status_code == 201 and r.json()["filename"] == "Night Drive.ogg" and r.json()["format"] == "OGG"


@pytest.mark.parametrize(
    "path,status,fragment",
    [
        ("/page", 422, "web page"),
        ("/private.mp3", 422, "login"),
        ("/files/missing.mp3", 422, "not found"),
        ("/files/fake.mp3", 422, ""),
    ],
)
def test_url_import_errors(client, http_server, allow_local, path, status, fragment):
    r = client.post("/api/sources/url", json={"url": http_server + path})
    assert r.status_code == status
    assert fragment in r.json()["detail"].lower()


def test_url_import_size_limit(client, http_server, allow_local, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 0)
    r = client.post("/api/sources/url", json={"url": f"{http_server}/files/song.mp3"})
    assert r.status_code == 413


def test_url_private_addresses_blocked_by_default(client, http_server, monkeypatch):
    monkeypatch.setattr(settings, "allow_private_urls", False)
    monkeypatch.setattr(settings, "url_trust_env", False)
    for url in (f"{http_server}/files/song.mp3", "http://localhost/x.mp3", "http://10.0.0.5/a.mp3", "http://[::1]/a.mp3",
                "http://169.254.169.254/latest/meta-data"):
        r = client.post("/api/sources/url", json={"url": url})
        assert r.status_code == 403, url


@pytest.mark.parametrize(
    "url,fragment",
    [
        ("ftp://example.com/a.mp3", "http"),
        ("file:///etc/passwd", "http"),
        ("not a url", "http"),
        ("", "enter a url"),
        ("https://user:pw@example.com/a.mp3", "credentials"),
        ("https://open.spotify.com/track/123", "drm"),
        ("https://music.apple.com/us/album/x/1", "drm"),
    ],
)
def test_url_validation(client, url, fragment):
    r = client.post("/api/sources/url", json={"url": url})
    assert r.status_code in (400, 422)
    assert fragment in r.json()["detail"].lower()


def test_validate_url_unit():
    assert url_import.validate_url("  https://cdn.example.com/a.mp3 ") == "https://cdn.example.com/a.mp3"
    with pytest.raises(url_import.UrlImportError):
        url_import.validate_url("https://open.spotify.com/track/x")


# ------------------------------------------------------------------------------ Google Drive / Dropbox

DRIVE_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz012345"
DIRECT = f"https://drive.usercontent.google.com/download?id={DRIVE_ID}&export=download&confirm=t"


@pytest.mark.parametrize(
    "link",
    [
        f"https://drive.google.com/file/d/{DRIVE_ID}/view?usp=sharing",
        f"https://drive.google.com/file/d/{DRIVE_ID}/view?usp=drive_link",
        f"https://drive.google.com/open?id={DRIVE_ID}",
        f"https://drive.google.com/uc?export=download&id={DRIVE_ID}",
        f"https://docs.google.com/uc?id={DRIVE_ID}",
        f"https://drive.google.com/file/u/0/d/{DRIVE_ID}/view".replace("/u/0/d/", "/d/"),
    ],
)
def test_google_drive_share_links_resolve_to_direct_download(link):
    assert url_import.resolve_share_link(link) == (DIRECT, "gdrive")


@pytest.mark.parametrize(
    "link,fragment",
    [
        ("https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOp", "folder"),
        ("https://docs.google.com/document/d/1AbCdEfGhIjKlMnOp/edit", "docs"),
        ("https://drive.google.com/file/view", "file id"),
    ],
)
def test_google_drive_unsupported_links(link, fragment):
    with pytest.raises(url_import.UrlImportError) as e:
        url_import.resolve_share_link(link)
    assert fragment in str(e.value).lower()


def test_dropbox_share_link_forces_download():
    url, provider = url_import.resolve_share_link("https://www.dropbox.com/scl/fi/abc/song.mp3?rlkey=xyz&dl=0")
    assert provider == "dropbox" and url == "https://www.dropbox.com/scl/fi/abc/song.mp3?rlkey=xyz&dl=1"


def test_other_links_unchanged():
    assert url_import.resolve_share_link("https://cdn.example.com/a.mp3") == ("https://cdn.example.com/a.mp3", None)


def _fake(status: int, ctype: str, body: bytes = b"", cd: str | None = None):
    import httpx

    headers = {"content-type": ctype}
    if cd:
        headers["content-disposition"] = cd
    return httpx.Response(status, headers=headers, content=body)


def test_private_drive_file_gives_sharing_instructions(tmp_path):
    for resp in (_fake(200, "text/html; charset=utf-8", b"<html>Sign in</html>"), _fake(403, "text/html")):
        with pytest.raises(url_import.UrlImportError) as e:
            url_import._save(resp, DIRECT, tmp_path, 10**8, "gdrive")
        assert "anyone with the link" in str(e.value).lower()


def test_public_drive_file_saved_with_its_name(tmp_path, signals):
    resp = _fake(200, "audio/mpeg", signals["mp3"].read_bytes(), "attachment; filename=\"Lagu Saya.mp3\"")
    path, name, size = url_import._save(resp, DIRECT, tmp_path, 10**8, "gdrive")
    assert name == "Lagu Saya.mp3" and path.suffix == ".mp3" and size == signals["mp3"].stat().st_size


def test_embedded_mode_uses_partitioned_cookie(monkeypatch, data_dir):
    monkeypatch.setattr(settings, "embedded", True)
    with TestClient(app, base_url="https://testserver") as c:
        r = c.get("/api/config")
        cookie = r.headers["set-cookie"]
        assert "SameSite=None" in cookie and "Secure" in cookie and "Partitioned" in cookie
        sid = r.cookies.get("sw_session")
        assert sid and c.get("/api/config", cookies={"sw_session": sid}).headers.get("set-cookie") is None
