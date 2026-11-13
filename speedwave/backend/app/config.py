"""Runtime configuration, read from environment variables (prefix SPEEDWAVE_)."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(f"SPEEDWAVE_{name}", default)


def _env_bool(name: str, default: bool) -> bool:
    return _env(name, "1" if default else "0").strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    # Where uploaded sources and processed outputs are stored (per-session subfolders).
    data_dir: Path = field(
        default_factory=lambda: Path(_env("DATA_DIR", str(Path(tempfile.gettempdir()) / "speedwave")))
    )
    ffmpeg: str = field(default_factory=lambda: _env("FFMPEG", "ffmpeg"))
    ffprobe: str = field(default_factory=lambda: _env("FFPROBE", "ffprobe"))

    # Rubber Band engine: "auto" (R3 if available), "finer" (force R3), "faster" (force R2).
    rubberband_engine: str = field(default_factory=lambda: _env("RUBBERBAND_ENGINE", "auto").lower())

    # Limits
    max_upload_mb: int = field(default_factory=lambda: int(_env("MAX_UPLOAD_MB", "500")))
    max_duration_minutes: int = field(default_factory=lambda: int(_env("MAX_DURATION_MINUTES", "240")))
    max_concurrent_jobs: int = field(default_factory=lambda: int(_env("MAX_CONCURRENT_JOBS", "2")))
    # Files (sources + outputs) are deleted this long after their last access.
    file_ttl_minutes: int = field(default_factory=lambda: int(_env("FILE_TTL_MINUTES", "60")))
    cleanup_interval_seconds: int = field(default_factory=lambda: int(_env("CLEANUP_INTERVAL_SECONDS", "120")))

    # URL import
    url_timeout_seconds: float = field(default_factory=lambda: float(_env("URL_TIMEOUT_SECONDS", "30")))
    url_max_redirects: int = field(default_factory=lambda: int(_env("URL_MAX_REDIRECTS", "5")))
    # Allow URLs that resolve to private / loopback addresses. Off by default (SSRF protection).
    allow_private_urls: bool = field(default_factory=lambda: _env_bool("ALLOW_PRIVATE_URLS", False))
    # Let the HTTP client honour HTTP(S)_PROXY / SSL_CERT_FILE environment variables.
    url_trust_env: bool = field(default_factory=lambda: _env_bool("URL_TRUST_ENV", True))

    # Serve the built frontend (frontend/dist) from the API server when present.
    frontend_dist: Path = field(
        default_factory=lambda: Path(
            _env("FRONTEND_DIST", str(Path(__file__).resolve().parents[2] / "frontend" / "dist"))
        )
    )
    # Comma-separated list of allowed CORS origins (only needed if the frontend runs on another origin).
    cors_origins: str = field(default_factory=lambda: _env("CORS_ORIGINS", ""))
    cookie_secure: bool = field(default_factory=lambda: _env_bool("COOKIE_SECURE", False))

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
