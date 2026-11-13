"""Import audio from media platforms (YouTube, SoundCloud, Bandcamp, Vimeo, ...) via yt-dlp.

Policy:
  * Only publicly available media. No account login and no cookies, so private, members-only and
    age-restricted media cannot be imported.
  * No DRM circumvention. DRM-only services (Spotify, Apple Music, Deezer, TIDAL, ...) are refused
    up front, and yt-dlp refuses DRM-protected formats itself.
  * yt-dlp's default behaviour only. If a platform blocks the download, the user gets a clear
    explanation; SpeedWave does not try to work around it.
  * yt-dlp's "generic" extractor (scraping arbitrary web pages) is disabled, so only sites with a
    dedicated extractor are contacted.
"""

from __future__ import annotations

import re
import shutil
import sys
import threading
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlsplit

from .config import settings

try:  # yt-dlp is optional: without it, direct links still work.
    import yt_dlp
    from yt_dlp.utils import DownloadCancelled, DownloadError
except ImportError:  # pragma: no cover
    yt_dlp = None  # type: ignore


class MediaImportError(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


# Services whose catalogue is DRM-protected: nothing can be imported from them.
DRM_PLATFORMS = {
    "spotify.com": "Spotify", "music.apple.com": "Apple Music", "itunes.apple.com": "Apple Music",
    "deezer.com": "Deezer", "tidal.com": "TIDAL", "music.amazon.com": "Amazon Music",
    "music.amazon.co.uk": "Amazon Music", "pandora.com": "Pandora", "napster.com": "Napster",
    "qobuz.com": "Qobuz", "joox.com": "JOOX", "anghami.com": "Anghami",
}

ProgressCallback = Callable[[int, Optional[int], Optional[float], Optional[float]], None]
# (downloaded_bytes, total_bytes, speed_bytes_per_s, eta_seconds)


def _match_host(host: str, table: dict[str, str]) -> Optional[str]:
    host = host.lower().rstrip(".")
    for domain, name in table.items():
        if host == domain or host.endswith("." + domain):
            return name
    return None


def drm_platform(url: str) -> Optional[str]:
    return _match_host(urlsplit(url).hostname or "", DRM_PLATFORMS)


def available() -> bool:
    return yt_dlp is not None and settings.platform_import


def version() -> Optional[str]:
    return yt_dlp.version.__version__ if yt_dlp is not None else None


def js_runtime() -> Optional[str]:
    """Path of the deno binary yt-dlp uses for YouTube's JavaScript challenges, if installed."""
    found = shutil.which("deno")
    if found:
        return found
    local = Path(sys.executable).parent / "deno"
    return str(local) if local.exists() else None


_extractors = None


def platform_name(url: str) -> Optional[str]:
    """Name of the dedicated yt-dlp extractor for this URL, or None (offline regex check)."""
    global _extractors
    if not available():
        return None
    if _extractors is None:
        _extractors = [ie for ie in yt_dlp.extractor.gen_extractor_classes() if ie.IE_NAME != "generic" and ie._ENABLED]
    for ie in _extractors:
        try:
            if ie.suitable(url):
                return _pretty(ie.IE_NAME)
        except Exception:  # pragma: no cover - a broken extractor regex
            continue
    return None


def _pretty(ie_name: str) -> str:
    base = ie_name.split(":")[0]
    known = {"youtube": "YouTube", "soundcloud": "SoundCloud", "bandcamp": "Bandcamp", "vimeo": "Vimeo",
             "mixcloud": "Mixcloud", "twitch": "Twitch", "tiktok": "TikTok", "instagram": "Instagram",
             "facebook": "Facebook", "twitter": "X / Twitter", "dailymotion": "Dailymotion", "archiveorg": "Internet Archive",
             "audiomack": "Audiomack", "reddit": "Reddit"}
    return known.get(base.lower(), base[:1].upper() + base[1:])


def explain(platform: str, message: str) -> str:
    """Turn a yt-dlp error into a user-facing explanation."""
    m = re.sub(r"\x1b\[[0-9;]*m", "", message)
    low = m.lower()
    if "not a bot" in low or "sign in to confirm" in low and "age" not in low:
        return (f"{platform} is blocking downloads from this server's network (it asks to sign in to prove you're not a bot). "
                "This is common on cloud servers such as Google Colab. Run SpeedWave on your own computer, "
                "or save the audio yourself and upload the file.")
    if "drm" in low:
        return f"This {platform} media is DRM-protected and cannot be imported."
    if "private" in low or "members" in low or "join this channel" in low or "premium" in low:
        return f"This {platform} media is private, members-only or paid. SpeedWave doesn't log in to accounts, so it can't import it."
    if "age" in low and ("confirm" in low or "restricted" in low or "inappropriate" in low):
        return f"This {platform} media is age-restricted and needs a signed-in account. SpeedWave doesn't log in, so it can't import it."
    if "login" in low or "log in" in low or "sign in" in low or "cookies" in low or "authentication" in low:
        return f"{platform} requires you to log in to access this. SpeedWave only imports publicly available media."
    if "403" in low or "forbidden" in low:
        return (f"{platform} refused the download (HTTP 403). Platforms often block cloud servers. "
                "Try running SpeedWave on your own computer, or upload the file instead.")
    if "429" in low or "too many requests" in low or "rate" in low and "limit" in low:
        return f"{platform} is rate-limiting this server. Wait a few minutes and try again."
    if "not available in your country" in low or "geo" in low:
        return f"This {platform} media isn't available in the server's region."
    if "unavailable" in low or "removed" in low or "does not exist" in low or "404" in low:
        return f"This {platform} media is unavailable. It may have been removed or the link is wrong."
    if "unsupported url" in low:
        return "This link isn't supported. Use a link to a single track/video page or a direct audio file."
    if "requested format is not available" in low:
        return f"No downloadable audio was offered by {platform} for this link."
    tail = m.replace("ERROR:", "").strip().splitlines()[-1][:200] if m.strip() else "unknown error"
    return f"Could not import from {platform}: {tail}"


def download(
    url: str,
    dest_dir: Path,
    on_progress: Optional[ProgressCallback] = None,
    cancel: Optional[threading.Event] = None,
) -> tuple[Path, str, int]:
    """Download the best available audio for a single media page. Returns (path, display name, size)."""
    if not available():
        raise MediaImportError("Platform import isn't available on this server (yt-dlp is not installed).", status=501)
    platform = platform_name(url) or "this site"
    limit = settings.max_upload_bytes
    max_seconds = settings.max_duration_minutes * 60

    def hook(d: dict) -> None:
        if cancel is not None and cancel.is_set():
            raise DownloadCancelled("cancelled")
        if d.get("status") == "downloading" and on_progress:
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            on_progress(int(d.get("downloaded_bytes") or 0), int(total) if total else None, d.get("speed"), d.get("eta"))

    opts = {
        "format": "bestaudio/best",
        "outtmpl": {"default": str(dest_dir / "source.%(ext)s")},
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "allowed_extractors": ["default", "-generic"],
        "max_filesize": limit,
        "progress_hooks": [hook],
        "socket_timeout": settings.url_timeout_seconds,
        "retries": 3,
        "cachedir": False,
        "overwrites": True,
        "restrictfilenames": True,
        "logger": _QuietLogger(),
    }
    deno = js_runtime()
    if deno:
        opts["js_runtimes"] = {"deno": {"path": deno}}

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise MediaImportError(f"{platform} returned no media for this link.")
            if info.get("_type") in ("playlist", "multi_video") or info.get("entries") is not None:
                raise MediaImportError("Playlists, albums and channels aren't supported. Paste the link of a single track or video.")
            if info.get("is_live") or info.get("live_status") in ("is_live", "is_upcoming"):
                raise MediaImportError("Live streams and premieres can't be imported. Try again once the recording is available.")
            if info.get("_has_drm"):
                raise MediaImportError(f"This {platform} media is DRM-protected and cannot be imported.")
            duration = info.get("duration")
            if duration and duration > max_seconds:
                raise MediaImportError(f"This media is longer than the {settings.max_duration_minutes}-minute limit.", status=413)
            size = info.get("filesize") or info.get("filesize_approx")
            if size and size > limit:
                raise MediaImportError(f"The audio is larger than the {settings.max_upload_mb} MB limit.", status=413)
            ydl.process_ie_result(info, download=True)
    except MediaImportError:
        raise
    except DownloadCancelled:
        raise MediaImportError("Import cancelled.", status=499)
    except DownloadError as e:
        raise MediaImportError(explain(platform, str(e)), status=422) from e

    files = [p for p in dest_dir.glob("source.*") if not p.name.endswith((".part", ".ytdl"))]
    if not files:
        raise MediaImportError(f"{platform} didn't provide a downloadable audio file (it may exceed the {settings.max_upload_mb} MB limit).")
    path = max(files, key=lambda p: p.stat().st_size)
    title = (info.get("title") or "audio").strip().rstrip(".") or "audio"
    if info.get("uploader") and platform in ("SoundCloud", "Bandcamp") and info["uploader"] not in title:
        title = f"{info['uploader']} - {title}"
    return path, f"{title}{path.suffix}", path.stat().st_size


class _QuietLogger:
    """Swallow yt-dlp chatter; errors surface as DownloadError."""

    def debug(self, msg: str) -> None:
        pass

    info = warning = debug

    def error(self, msg: str) -> None:
        pass
