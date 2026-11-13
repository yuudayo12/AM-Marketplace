"""In-memory registry of uploaded sources and conversion jobs, with on-disk files.

Layout:  DATA_DIR/<session_id>/<source_id>/source.<ext>          (read-only original)
                                          /jobs/<job_id>/<name>_2x.mp3
Everything is scoped to the browser session that created it.
"""

from __future__ import annotations

import asyncio
import logging
import re
import secrets
import shutil
import stat
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from . import audio
from .config import settings

log = logging.getLogger("speedwave")

ID_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def new_id() -> str:
    return secrets.token_urlsafe(16)


def safe_stem(name: str) -> str:
    stem = Path(name.replace("\\", "/")).stem
    stem = unicodedata.normalize("NFC", stem)
    stem = re.sub(r"[\x00-\x1f\x7f/\\:*?\"<>|]+", "_", stem).strip(" ._")
    return (stem or "audio")[:120]


def speed_label(speed: float) -> str:
    return f"{speed:.2f}".rstrip("0").rstrip(".") + "x"


@dataclass
class Source:
    id: str
    session_id: str
    dir: Path
    path: Path
    original_name: str
    size: int
    info: audio.AudioInfo
    origin: str  # "upload" | "url"
    created_at: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)
    waveform: Optional[list[float]] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.original_name,
            "size": self.size,
            "origin": self.origin,
            **self.info.to_dict(),
            "preview_url": f"/api/sources/{self.id}/audio",
            "waveform_url": f"/api/sources/{self.id}/waveform",
        }


@dataclass
class JobSettings:
    speed: float
    formats: tuple[str, ...]
    mp3_bitrate: int
    ogg_quality: int
    quality: str
    clip_protection: bool


@dataclass
class Job:
    id: str
    session_id: str
    source: Source
    settings: JobSettings
    dir: Path
    status: str = "queued"  # queued | processing | finalizing | completed | failed | cancelled
    stage: str = "Waiting for a free processing slot"
    progress: float = 0.0
    eta_seconds: Optional[float] = None
    realtime_factor: Optional[float] = None
    error: Optional[str] = None
    outputs: dict[str, dict] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    task: Optional[asyncio.Task] = None

    @property
    def active(self) -> bool:
        return self.status in {"queued", "processing", "finalizing"}

    def to_dict(self) -> dict:
        s = self.settings
        elapsed = None
        if self.started_at:
            elapsed = (self.finished_at or time.time()) - self.started_at
        return {
            "id": self.id,
            "source_id": self.source.id,
            "status": self.status,
            "stage": self.stage,
            "progress": round(self.progress, 4),
            "eta_seconds": None if self.eta_seconds is None else round(self.eta_seconds, 1),
            "elapsed_seconds": None if elapsed is None else round(elapsed, 2),
            "realtime_factor": self.realtime_factor,
            "error": self.error,
            "settings": {
                "speed": s.speed,
                "formats": list(s.formats),
                "mp3_bitrate": s.mp3_bitrate,
                "ogg_quality": s.ogg_quality,
                "quality": s.quality,
                "engine": "R3 (finer)" if s.quality != "fast" and audio.r3_available() else "R2 (faster)",
                "clip_protection": s.clip_protection,
            },
            "original_duration": self.source.info.duration,
            "expected_duration": self.source.info.duration / s.speed,
            "outputs": {
                fmt: {
                    k: v for k, v in o.items() if k not in ("path", "waveform")
                }
                | {
                    "download_url": f"/api/jobs/{self.id}/download/{fmt}",
                    "preview_url": f"/api/jobs/{self.id}/download/{fmt}?inline=1",
                    "waveform_url": f"/api/jobs/{self.id}/waveform/{fmt}",
                }
                for fmt, o in self.outputs.items()
            },
        }


@dataclass
class ImportTask:
    """A URL / platform import running in the background, with real download progress."""

    id: str
    session_id: str
    url: str
    kind: str  # "direct" | "platform"
    platform: Optional[str]
    status: str = "downloading"  # downloading | analyzing | completed | failed | cancelled
    stage: str = "Connecting"
    downloaded: int = 0
    total: Optional[int] = None
    speed: Optional[float] = None
    eta: Optional[float] = None
    error: Optional[str] = None
    source: Optional[Source] = None
    created_at: float = field(default_factory=time.time)
    cancel_event: threading.Event = field(default_factory=threading.Event)

    @property
    def active(self) -> bool:
        return self.status in {"downloading", "analyzing"}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "kind": self.kind,
            "platform": self.platform,
            "status": self.status,
            "stage": self.stage,
            "downloaded_bytes": self.downloaded,
            "total_bytes": self.total,
            "progress": round(min(self.downloaded / self.total, 1.0), 4) if self.total else None,
            "speed_bps": None if self.speed is None else round(self.speed),
            "eta_seconds": None if self.eta is None else round(self.eta, 1),
            "error": self.error,
            "source": self.source.to_dict() if self.source else None,
        }


def register_source(session_id: str, source_id: str, d: Path, path: Path, name: str, size: int, origin: str) -> Source:
    """Probe a stored file and register it. Raises audio.AudioError (and removes the folder) if unusable."""
    try:
        info = audio.probe(path)
        if info.duration > settings.max_duration_minutes * 60:
            raise audio.AudioError(f"The audio is longer than the {settings.max_duration_minutes}-minute limit.")
    except audio.AudioError:
        shutil.rmtree(d, ignore_errors=True)
        raise
    src = Source(id=source_id, session_id=session_id, dir=d, path=path, original_name=name, size=size, info=info, origin=origin)
    store.add_source(src)
    log.info("Source %s: %s (%s, %.1fs, %d ch)", source_id, name, info.format_label, info.duration, info.channels)
    return src


class Store:
    def __init__(self) -> None:
        self.sources: dict[str, Source] = {}
        self.jobs: dict[str, Job] = {}
        self.imports: dict[str, ImportTask] = {}
        self._import_sem: Optional[asyncio.Semaphore] = None
        self._lock = asyncio.Lock()
        self._sem: Optional[asyncio.Semaphore] = None

    @property
    def semaphore(self) -> asyncio.Semaphore:
        if self._sem is None:
            self._sem = asyncio.Semaphore(max(1, settings.max_concurrent_jobs))
        return self._sem

    # ---------------------------------------------------------------- sources

    def new_source_dir(self, session_id: str) -> tuple[str, Path]:
        sid = new_id()
        d = settings.data_dir / session_id / sid
        d.mkdir(parents=True, exist_ok=False)
        return sid, d

    def add_source(self, src: Source) -> None:
        # The original is made read-only: nothing in SpeedWave ever writes to it again.
        src.path.chmod(stat.S_IRUSR | stat.S_IRGRP)
        self.sources[src.id] = src

    def get_source(self, source_id: str, session_id: str) -> Optional[Source]:
        src = self.sources.get(source_id)
        if src is None or src.session_id != session_id:
            return None
        src.last_access = time.time()
        return src

    def remove_source(self, src: Source) -> None:
        for job in [j for j in self.jobs.values() if j.source.id == src.id]:
            job.cancel_event.set()
            self.jobs.pop(job.id, None)
        self.sources.pop(src.id, None)
        try:
            src.path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # read-only files block rmtree on Windows
        except OSError:
            pass
        shutil.rmtree(src.dir, ignore_errors=True)

    # ---------------------------------------------------------------- imports

    def get_import(self, import_id: str, session_id: str) -> Optional[ImportTask]:
        task = self.imports.get(import_id)
        return task if task is not None and task.session_id == session_id else None

    def start_import(self, session_id: str, url: str, kind: str, platform: Optional[str]) -> ImportTask:
        task = ImportTask(id=new_id(), session_id=session_id, url=url, kind=kind, platform=platform)
        self.imports[task.id] = task
        asyncio.create_task(self._run_import(task))
        return task

    async def _run_import(self, task: ImportTask) -> None:
        from . import url_import  # local import: url_import -> media_import -> config only

        if self._import_sem is None:
            self._import_sem = asyncio.Semaphore(3)
        source_id, d = self.new_source_dir(task.session_id)

        def on_progress(done: int, total: Optional[int], speed: Optional[float], eta: Optional[float]) -> None:
            task.stage = f"Downloading from {task.platform}" if task.platform else "Downloading"
            task.downloaded, task.total, task.speed, task.eta = done, total, speed, eta

        try:
            async with self._import_sem:
                task.stage = f"Fetching from {task.platform}" if task.platform else "Connecting"
                path, name, size = await asyncio.to_thread(url_import.download, task.url, d, on_progress, task.cancel_event)
                task.status, task.stage, task.eta = "analyzing", "Analyzing audio", None
                task.downloaded = size
                task.source = await asyncio.to_thread(
                    register_source, task.session_id, source_id, d, path, name, size, "platform" if task.kind == "platform" else "url"
                )
            task.status, task.stage = "completed", "Done"
        except url_import.UrlImportError as e:
            shutil.rmtree(d, ignore_errors=True)
            cancelled = task.cancel_event.is_set() or e.status == 499
            task.status = "cancelled" if cancelled else "failed"
            task.stage, task.error = ("Cancelled", None) if cancelled else ("Failed", str(e))
        except audio.AudioError as e:
            task.status, task.stage, task.error = "failed", "Failed", str(e)
        except Exception as e:  # pragma: no cover
            log.exception("Import %s crashed", task.id)
            shutil.rmtree(d, ignore_errors=True)
            task.status, task.stage = "failed", "Failed"
            task.error = f"Unexpected import error ({type(e).__name__}). Check the server log."
        finally:
            task.speed = task.eta = None

    # ---------------------------------------------------------------- jobs

    def get_job(self, job_id: str, session_id: str) -> Optional[Job]:
        job = self.jobs.get(job_id)
        if job is None or job.session_id != session_id:
            return None
        job.source.last_access = time.time()
        return job

    async def submit(self, src: Source, js: JobSettings) -> tuple[Job, bool]:
        """Create a job, or return the existing identical one (duplicate protection)."""
        async with self._lock:
            for job in self.jobs.values():
                if job.source.id == src.id and job.settings == js and (job.active or job.status == "completed"):
                    return job, True
            job_id = new_id()
            d = src.dir / "jobs" / job_id
            d.mkdir(parents=True)
            job = Job(id=job_id, session_id=src.session_id, source=src, settings=js, dir=d)
            self.jobs[job_id] = job
            job.task = asyncio.create_task(self._run(job))
            return job, False

    async def _run(self, job: Job) -> None:
        try:
            async with self.semaphore:
                if job.cancel_event.is_set():
                    raise audio.CancelledError()
                await self._process(job)
        except audio.CancelledError:
            job.status, job.stage, job.eta_seconds = "cancelled", "Cancelled", None
            self._discard_outputs(job)
        except audio.AudioError as e:
            job.status, job.stage, job.error, job.eta_seconds = "failed", "Failed", str(e), None
            self._discard_outputs(job)
        except Exception as e:  # pragma: no cover - unexpected bug
            log.exception("Job %s crashed", job.id)
            job.status, job.stage, job.eta_seconds = "failed", "Failed", None
            job.error = f"Unexpected processing error ({type(e).__name__}). Check the server log."
            self._discard_outputs(job)
        finally:
            job.finished_at = time.time()

    async def _process(self, job: Job) -> None:
        s, src = job.settings, job.source
        job.status, job.stage, job.started_at = "processing", "Time-stretching & encoding", time.time()
        stem = f"{safe_stem(src.original_name)}_{speed_label(s.speed)}"
        specs = [
            audio.OutputSpec(fmt=f, path=job.dir / f"{stem}.{audio.OUTPUT_FORMATS[f]['ext']}",
                             mp3_bitrate=s.mp3_bitrate, ogg_quality=s.ogg_quality)
            for f in s.formats
        ]

        def on_progress(fraction: float, out_seconds: float) -> None:
            # Progress is the position ffmpeg has written in the output timeline.
            job.progress = min(fraction, 0.99)
            elapsed = time.time() - (job.started_at or time.time())
            if out_seconds > 0 and elapsed > 0.5:
                job.realtime_factor = round(out_seconds * s.speed / elapsed, 1)  # input seconds per second
            if fraction > 0.02 and elapsed > 1.0:
                job.eta_seconds = max(elapsed * (1 - fraction) / fraction, 0.0)

        await asyncio.to_thread(
            audio.convert, src.path, src.info, specs, s.speed, s.quality, s.clip_protection, on_progress, job.cancel_event
        )

        job.status, job.stage, job.eta_seconds = "finalizing", "Verifying output files", None
        expected = src.info.duration / s.speed
        for spec in specs:
            meta = await asyncio.to_thread(audio.verify_output, spec.path, spec.fmt)
            if abs(meta["duration"] - expected) > max(0.5, expected * 0.02):
                raise audio.AudioError(
                    f"{spec.fmt.upper()} output duration {meta['duration']:.2f}s does not match the expected {expected:.2f}s."
                )
            job.outputs[spec.fmt] = {
                "filename": spec.path.name,
                "mime": audio.OUTPUT_FORMATS[spec.fmt]["mime"],
                "path": spec.path,
                **meta,
            }
        (job.dir / "ffmpeg.log").unlink(missing_ok=True)
        job.progress, job.status, job.stage = 1.0, "completed", "Done"

    def _discard_outputs(self, job: Job) -> None:
        job.outputs = {}
        for p in job.dir.glob("*"):
            if p.name != "ffmpeg.log":
                p.unlink(missing_ok=True)

    def cancel(self, job: Job) -> None:
        if job.active:
            job.cancel_event.set()

    # ---------------------------------------------------------------- cleanup

    def cleanup_expired(self) -> int:
        cutoff = time.time() - settings.file_ttl_minutes * 60
        removed = 0
        for src in list(self.sources.values()):
            busy = any(j.active for j in self.jobs.values() if j.source.id == src.id)
            if src.last_access < cutoff and not busy:
                self.remove_source(src)
                removed += 1
        for t in list(self.imports.values()):
            if not t.active and t.created_at < cutoff:
                self.imports.pop(t.id, None)
        # Orphaned directories (e.g. left over from a previous server run).
        root = settings.data_dir
        if root.exists():
            known = {str(s.dir) for s in self.sources.values()}
            for session_dir in root.iterdir():
                if not session_dir.is_dir():
                    continue
                for d in session_dir.iterdir():
                    if str(d) not in known and d.stat().st_mtime < cutoff:
                        shutil.rmtree(d, ignore_errors=True)
                if not any(session_dir.iterdir()):
                    session_dir.rmdir()
        return removed

    async def cleanup_loop(self) -> None:
        while True:
            try:
                n = await asyncio.to_thread(self.cleanup_expired)
                if n:
                    log.info("Cleaned up %d expired source(s)", n)
            except Exception:  # pragma: no cover
                log.exception("Cleanup failed")
            await asyncio.sleep(settings.cleanup_interval_seconds)


store = Store()
