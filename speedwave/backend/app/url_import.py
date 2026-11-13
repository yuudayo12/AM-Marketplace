"""Download audio from a direct URL, safely.

Only plain, publicly reachable HTTP(S) files are fetched. No login, cookies, DRM
or streaming-platform extraction: those are rejected with a clear message.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

import httpx

from .config import settings


class UrlImportError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


# Pages on these sites are players/web apps, not audio files.
STREAMING_PLATFORMS = {
    "youtube.com": "YouTube", "youtu.be": "YouTube", "music.youtube.com": "YouTube Music",
    "spotify.com": "Spotify", "open.spotify.com": "Spotify",
    "soundcloud.com": "SoundCloud", "music.apple.com": "Apple Music", "podcasts.apple.com": "Apple Podcasts",
    "deezer.com": "Deezer", "tidal.com": "TIDAL", "music.amazon.com": "Amazon Music",
    "pandora.com": "Pandora", "bandcamp.com": "Bandcamp", "mixcloud.com": "Mixcloud",
    "audiomack.com": "Audiomack", "tiktok.com": "TikTok", "instagram.com": "Instagram",
    "facebook.com": "Facebook", "twitch.tv": "Twitch", "vimeo.com": "Vimeo",
}

CONTENT_TYPE_EXT = {
    "audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/wav": ".wav", "audio/x-wav": ".wav", "audio/wave": ".wav",
    "audio/vnd.wave": ".wav", "audio/ogg": ".ogg", "application/ogg": ".ogg", "audio/vorbis": ".ogg",
    "audio/flac": ".flac", "audio/x-flac": ".flac", "audio/mp4": ".m4a", "audio/x-m4a": ".m4a",
    "audio/m4a": ".m4a", "audio/aac": ".aac", "audio/x-aac": ".aac", "audio/aacp": ".aac",
}
BINARY_TYPES = {"application/octet-stream", "binary/octet-stream", "application/x-download", "application/download", "video/mp4"}


def _platform_for(host: str) -> str | None:
    host = host.lower().rstrip(".")
    for domain, name in STREAMING_PLATFORMS.items():
        if host == domain or host.endswith("." + domain):
            return name
    return None


def validate_url(url: str) -> str:
    """Syntactic + policy validation. Returns the normalised URL."""
    url = (url or "").strip()
    if not url:
        raise UrlImportError("Please enter a URL.")
    if len(url) > 2048:
        raise UrlImportError("That URL is too long.")
    parts = urlsplit(url)
    if parts.scheme.lower() not in {"http", "https"}:
        raise UrlImportError("Only http:// and https:// links are supported.")
    if not parts.hostname:
        raise UrlImportError("That doesn't look like a valid URL.")
    if parts.username or parts.password:
        raise UrlImportError("Links with embedded credentials are not supported. Use a publicly accessible direct link.")
    platform = _platform_for(parts.hostname)
    if platform:
        raise UrlImportError(
            f"This is a {platform} page, not a direct audio file. SpeedWave only imports direct download links "
            f"(e.g. https://example.com/song.mp3) and does not extract audio from streaming platforms. "
            f"Download the file through the platform's own permitted options, then upload it here.",
            status=422,
        )
    return url


def _check_host_is_public(host: str, port: int) -> None:
    if settings.allow_private_urls:
        return
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise UrlImportError(f"Could not resolve the host '{host}'.") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise UrlImportError("Links to private, local or internal network addresses are not allowed.", status=403)


def _filename_from(response: httpx.Response, url: str) -> str:
    cd = response.headers.get("content-disposition", "")
    m = re.search(r"filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]+)", cd) or re.search(r'filename\s*=\s*"?([^";]+)"?', cd)
    if m:
        name = unquote(m.group(1)).strip()
    else:
        name = unquote(Path(urlsplit(url).path).name)
    return name or "audio"


def download(url: str, dest_dir: Path) -> tuple[Path, str, int]:
    """Fetch the URL into dest_dir. Returns (path, original filename, size in bytes)."""
    url = validate_url(url)
    limit = settings.max_upload_bytes
    timeout = httpx.Timeout(settings.url_timeout_seconds, connect=10.0)
    headers = {"User-Agent": "SpeedWave/1.0 (audio speed converter)", "Accept": "audio/*, application/ogg, */*;q=0.5"}

    with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=settings.url_trust_env, headers=headers) as client:
        current = url
        for _ in range(settings.url_max_redirects + 1):
            parts = urlsplit(current)
            _check_host_is_public(parts.hostname or "", parts.port or (443 if parts.scheme == "https" else 80))
            try:
                with client.stream("GET", current) as resp:
                    if resp.is_redirect:
                        location = resp.headers.get("location")
                        if not location:
                            raise UrlImportError("The server sent a redirect without a destination.")
                        current = validate_url(urljoin(current, location))
                        continue
                    return _save(resp, current, dest_dir, limit)
            except httpx.TimeoutException as e:
                raise UrlImportError("The server took too long to respond.", status=504) from e
            except httpx.HTTPError as e:
                raise UrlImportError(f"Could not download the file: {type(e).__name__}.", status=502) from e
        raise UrlImportError("Too many redirects.")


def _save(resp: httpx.Response, url: str, dest_dir: Path, limit: int) -> tuple[Path, str, int]:
    code = resp.status_code
    if code in (401, 403):
        raise UrlImportError(
            "Access denied: this link requires a login or permission. Only publicly accessible direct links are supported.",
            status=422,
        )
    if code == 404:
        raise UrlImportError("The file was not found at that URL (404).", status=422)
    if code == 451:
        raise UrlImportError("This file is unavailable for legal reasons (451).", status=422)
    if code >= 400:
        raise UrlImportError(f"The server returned an error ({code}).", status=502)

    ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    if ctype.startswith("text/") or ctype in {"application/json", "application/xml", "application/xhtml+xml"}:
        raise UrlImportError(
            "That URL points to a web page, not an audio file. Use a direct link to the file itself "
            "(right-click the download link and copy its address).",
            status=422,
        )
    if ctype and not (ctype.startswith("audio/") or ctype in CONTENT_TYPE_EXT or ctype in BINARY_TYPES):
        raise UrlImportError(f"The URL does not point to an audio file (content type: {ctype}).", status=422)

    length = resp.headers.get("content-length")
    if length and length.isdigit() and int(length) > limit:
        raise UrlImportError(f"The file is larger than the {settings.max_upload_mb} MB limit.", status=413)

    name = _filename_from(resp, url)
    ext = Path(name).suffix.lower()
    if not ext and ctype in CONTENT_TYPE_EXT:
        ext = CONTENT_TYPE_EXT[ctype]
        name += ext
    dest = dest_dir / f"source{ext or '.bin'}"
    size = 0
    with open(dest, "wb") as f:
        for chunk in resp.iter_bytes(1024 * 256):
            size += len(chunk)
            if size > limit:
                f.close()
                dest.unlink(missing_ok=True)
                raise UrlImportError(f"The file is larger than the {settings.max_upload_mb} MB limit.", status=413)
            f.write(chunk)
    if size == 0:
        dest.unlink(missing_ok=True)
        raise UrlImportError("The server returned an empty file.", status=422)
    return dest, name, size
