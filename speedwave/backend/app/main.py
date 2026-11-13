"""SpeedWave API server."""

from __future__ import annotations

import asyncio
import logging
import secrets
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import audio, media_import, url_import
from .config import settings
from .store import ID_RE, JobSettings, Source, register_source, store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("speedwave")

SESSION_COOKIE = "sw_session"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    status = audio.engine_status()
    if not status["ok"]:
        log.error("Audio engine incomplete: %s", status)
    else:
        log.info("Audio engine: %s (rubberband, libmp3lame, libvorbis available)", status["ffmpeg"])
    cleaner = asyncio.create_task(store.cleanup_loop())
    yield
    cleaner.cancel()


app = FastAPI(title="SpeedWave", version="1.0.0", lifespan=lifespan)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def session_middleware(request: Request, call_next):
    """Every browser gets an anonymous random session; files are only visible to it."""
    sid = request.cookies.get(SESSION_COOKIE)
    new = not (sid and ID_RE.match(sid))
    if new:
        sid = secrets.token_urlsafe(24)
    request.state.session_id = sid
    response = await call_next(request)
    if new:
        if settings.embedded:
            # Inside an iframe on another site (e.g. Colab's notebook output) a Lax cookie is a
            # third-party cookie and is dropped. SameSite=None + Partitioned (CHIPS) is accepted
            # by browsers that block third-party cookies.
            response.headers.append(
                "set-cookie",
                f"{SESSION_COOKIE}={sid}; Max-Age=86400; Path=/; HttpOnly; Secure; SameSite=None; Partitioned",
            )
        else:
            response.set_cookie(
                SESSION_COOKIE, sid, httponly=True, samesite="lax", secure=settings.cookie_secure, max_age=60 * 60 * 24
            )
    return response


def _session(request: Request) -> str:
    return request.state.session_id


# --------------------------------------------------------------------------- models


class UrlImportRequest(BaseModel):
    url: str = Field(..., max_length=2048)


class JobRequest(BaseModel):
    source_id: str
    speed: float = Field(2.0, ge=audio.MIN_SPEED, le=audio.MAX_SPEED)
    formats: list[Literal["mp3", "ogg"]] = Field(default_factory=lambda: ["mp3"], min_length=1, max_length=2)
    mp3_bitrate: int = 320
    ogg_quality: int = Field(8, ge=3, le=10)
    quality: Literal["studio", "fast"] = audio.DEFAULT_QUALITY
    clip_protection: bool = True

    @field_validator("mp3_bitrate")
    @classmethod
    def _bitrate(cls, v: int) -> int:
        if v not in audio.MP3_BITRATES:
            raise ValueError(f"mp3_bitrate must be one of {audio.MP3_BITRATES}")
        return v


# --------------------------------------------------------------------------- info


@app.get("/api/health")
def health():
    status = audio.engine_status()
    return JSONResponse(status, status_code=200 if status["ok"] else 503)


@app.get("/api/config")
def config():
    return {
        "max_upload_mb": settings.max_upload_mb,
        "max_duration_minutes": settings.max_duration_minutes,
        "file_ttl_minutes": settings.file_ttl_minutes,
        "input_formats": list(audio.INPUT_FORMATS),
        "input_extensions": sorted(audio.INPUT_EXTENSIONS),
        "output_formats": list(audio.OUTPUT_FORMATS),
        "mp3_bitrates": audio.MP3_BITRATES,
        "speed": {"default": 2.0, "min": audio.MIN_SPEED, "max": audio.MAX_SPEED},
        "quality_modes": [{"id": k, "label": v["label"], "description": v["description"]} for k, v in audio.QUALITY_MODES.items()],
        "default_quality": audio.DEFAULT_QUALITY,
        "r3_available": audio.r3_available(),
        "platform_import": {
            "enabled": media_import.available(),
            "yt_dlp": media_import.version(),
            "js_runtime": bool(media_import.js_runtime()),
        },
    }


# --------------------------------------------------------------------------- sources


async def _register(session_id: str, source_id: str, d: Path, path: Path, name: str, size: int, origin: str) -> Source:
    try:
        return await asyncio.to_thread(register_source, session_id, source_id, d, path, name, size, origin)
    except audio.AudioError as e:
        raise HTTPException(422, str(e))


@app.post("/api/sources/upload", status_code=201)
async def upload(request: Request, file: UploadFile = File(...)):
    session_id = _session(request)
    name = Path((file.filename or "audio").replace("\\", "/")).name[:255] or "audio"
    ext = Path(name).suffix.lower()
    if ext not in audio.INPUT_EXTENSIONS:
        raise HTTPException(415, "Unsupported file type. Supported formats: MP3, WAV, OGG, FLAC, M4A, AAC, WEBM.")

    source_id, d = store.new_source_dir(session_id)
    dest = d / f"source{ext}"
    size = 0
    try:
        with open(dest, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(413, f"The file is larger than the {settings.max_upload_mb} MB limit.")
                out.write(chunk)
    except BaseException:
        shutil.rmtree(d, ignore_errors=True)
        raise
    finally:
        await file.close()
    if size == 0:
        shutil.rmtree(d, ignore_errors=True)
        raise HTTPException(422, "The uploaded file is empty.")
    src = await _register(session_id, source_id, d, dest, name, size, "upload")
    return src.to_dict()


@app.post("/api/sources/url", status_code=201)
async def import_url(request: Request, body: UrlImportRequest):
    session_id = _session(request)
    try:
        url_import.validate_url(body.url)
    except url_import.UrlImportError as e:
        raise HTTPException(e.status, str(e))
    source_id, d = store.new_source_dir(session_id)
    try:
        path, name, size = await asyncio.to_thread(url_import.download, body.url, d)
    except url_import.UrlImportError as e:
        shutil.rmtree(d, ignore_errors=True)
        raise HTTPException(e.status, str(e))
    except BaseException:
        shutil.rmtree(d, ignore_errors=True)
        raise
    src = await _register(session_id, source_id, d, path, name, size, "url")
    return src.to_dict()


@app.post("/api/imports", status_code=202)
async def start_import(request: Request, body: UrlImportRequest):
    """Start a URL / platform import in the background; poll GET /api/imports/{id}."""
    try:
        url = url_import.validate_url(body.url)
        kind, platform = url_import.source_kind(url)
    except url_import.UrlImportError as e:
        raise HTTPException(e.status, str(e))
    return store.start_import(_session(request), url, kind, platform).to_dict()


def _import_or_404(request: Request, import_id: str):
    task = store.get_import(import_id, _session(request))
    if task is None:
        raise HTTPException(404, "Import not found.")
    return task


@app.get("/api/imports/{import_id}")
def get_import(request: Request, import_id: str):
    return _import_or_404(request, import_id).to_dict()


@app.post("/api/imports/{import_id}/cancel")
def cancel_import(request: Request, import_id: str):
    task = _import_or_404(request, import_id)
    task.cancel_event.set()
    return task.to_dict()


def _source_or_404(request: Request, source_id: str) -> Source:
    src = store.get_source(source_id, _session(request))
    if src is None:
        raise HTTPException(404, "Audio not found. It may have expired; please upload it again.")
    return src


@app.get("/api/sources/{source_id}")
def get_source(request: Request, source_id: str):
    return _source_or_404(request, source_id).to_dict()


@app.get("/api/sources/{source_id}/audio")
def source_audio(request: Request, source_id: str):
    src = _source_or_404(request, source_id)
    mime = audio.INPUT_MIME.get(src.info.format_label, "application/octet-stream")
    return FileResponse(src.path, media_type=mime, headers={"Cache-Control": "private, max-age=3600"})


@app.get("/api/sources/{source_id}/waveform")
async def source_waveform(request: Request, source_id: str):
    src = _source_or_404(request, source_id)
    if src.waveform is None:
        src.waveform = await asyncio.to_thread(audio.waveform, src.path)
    return {"peaks": src.waveform}


@app.delete("/api/sources/{source_id}", status_code=204)
def delete_source(request: Request, source_id: str):
    store.remove_source(_source_or_404(request, source_id))


# --------------------------------------------------------------------------- jobs


@app.post("/api/jobs", status_code=202)
async def create_job(request: Request, body: JobRequest):
    src = _source_or_404(request, body.source_id)
    js = JobSettings(
        speed=round(body.speed, 3),
        formats=tuple(sorted(set(body.formats))),
        mp3_bitrate=body.mp3_bitrate,
        ogg_quality=body.ogg_quality,
        quality=body.quality,
        clip_protection=body.clip_protection,
    )
    job, duplicate = await store.submit(src, js)
    return {**job.to_dict(), "duplicate": duplicate}


def _job_or_404(request: Request, job_id: str):
    job = store.get_job(job_id, _session(request))
    if job is None:
        raise HTTPException(404, "Job not found. It may have expired.")
    return job


@app.get("/api/jobs/{job_id}")
def get_job(request: Request, job_id: str):
    return _job_or_404(request, job_id).to_dict()


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(request: Request, job_id: str):
    job = _job_or_404(request, job_id)
    store.cancel(job)
    return job.to_dict()


def _output_or_404(request: Request, job_id: str, fmt: str) -> dict:
    job = _job_or_404(request, job_id)
    if job.status != "completed" or fmt not in job.outputs:
        raise HTTPException(404, "This output is not available.")
    return job.outputs[fmt]


@app.get("/api/jobs/{job_id}/download/{fmt}")
def download(request: Request, job_id: str, fmt: str, inline: bool = False):
    out = _output_or_404(request, job_id, fmt)
    return FileResponse(
        out["path"],
        media_type=out["mime"],
        filename=out["filename"],
        content_disposition_type="inline" if inline else "attachment",
        headers={"Cache-Control": "private, no-transform"},
    )


@app.get("/api/jobs/{job_id}/waveform/{fmt}")
async def output_waveform(request: Request, job_id: str, fmt: str):
    out = _output_or_404(request, job_id, fmt)
    if "waveform" not in out:
        out["waveform"] = await asyncio.to_thread(audio.waveform, out["path"])
    return {"peaks": out["waveform"]}


# --------------------------------------------------------------------------- frontend


if settings.frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=settings.frontend_dist, html=True), name="frontend")
