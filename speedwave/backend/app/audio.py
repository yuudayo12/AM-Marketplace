"""FFmpeg / Rubber Band audio engine.

All audio work goes through FFmpeg. Time-stretching uses FFmpeg's ``rubberband``
filter (Rubber Band Library), a phase-vocoder time-stretcher that changes tempo
while keeping pitch and key unchanged. No resampling trick is used for the speed
change, so the pitch is never shifted.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from .config import settings


class AudioError(Exception):
    """A user-facing audio problem (unsupported, corrupt, protected...)."""


class CancelledError(Exception):
    pass


# --------------------------------------------------------------------------- formats

# Input formats accepted, keyed by the label shown to the user.
# Values are the ffprobe demuxer names that identify that container.
INPUT_FORMATS: dict[str, set[str]] = {
    "MP3": {"mp3"},
    "WAV": {"wav", "w64"},
    "OGG": {"ogg"},
    "FLAC": {"flac"},
    "M4A": {"mov", "mp4", "m4a", "3gp", "3g2", "mj2", "ipod"},
    "AAC": {"aac"},
    # WebM/Opus is what YouTube and many platforms deliver as their best audio.
    "WEBM": {"matroska", "webm"},
}
INPUT_EXTENSIONS = {".mp3", ".wav", ".ogg", ".oga", ".opus", ".flac", ".m4a", ".mp4", ".aac", ".webm"}
INPUT_MIME = {"MP3": "audio/mpeg", "WAV": "audio/wav", "OGG": "audio/ogg", "FLAC": "audio/flac",
              "M4A": "audio/mp4", "AAC": "audio/aac", "WEBM": "audio/webm"}

OUTPUT_FORMATS = {
    "mp3": {"ext": "mp3", "mime": "audio/mpeg", "codec": "mp3"},
    "ogg": {"ext": "ogg", "mime": "audio/ogg", "codec": "vorbis"},
}
MP3_BITRATES = [128, 192, 256, 320]
MP3_SAMPLE_RATES = [8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000]

# Rubber Band engines.
#  R3 ("finer", Rubber Band >= 3.0) is the high-quality engine. In measurements on pure
#  tones from 110 Hz to 5 kHz it kept level within 0.01 dB and pitch within 0.001%.
#  R2 ("faster") is the classic phase vocoder FFmpeg uses by default. It is about twice
#  as fast, but on sustained tones it showed up to 3.5 dB level loss and audible warble.
#  FFmpeg 6.x/7.x has no named option for the engine. Its rubberband filter ORs every
#  option value into the library's option bitmask, so RubberBandOptionEngineFiner
#  (0x20000000) can be passed through the otherwise-unused "smoothing" option (R3 ignores
#  smoothing).
RB_OPTION_ENGINE_FINER = 0x20000000

QUALITY_MODES: dict[str, dict] = {
    "studio": {
        "label": "Studio (Rubber Band R3)",
        "description": "Highest fidelity: the R3 'finer' engine keeps tone, level and stereo image intact. Recommended.",
    },
    "fast": {
        "label": "Fast (Rubber Band R2)",
        "description": "Classic engine, roughly 2x quicker. Good for speech; can add slight warble on sustained notes.",
    },
}
DEFAULT_QUALITY = "studio"

MIN_SPEED, MAX_SPEED = 0.5, 4.0
# Ceiling for the optional clip protection limiter: -1 dBFS, the usual safe
# headroom for lossy encoders (MP3/Vorbis decoders can overshoot a little).
CLIP_CEILING_DB = -1.0


# --------------------------------------------------------------------------- probing


@dataclass
class AudioInfo:
    format_name: str  # ffprobe demuxer name, e.g. "mp3"
    format_label: str  # user-facing label, e.g. "MP3"
    codec: str
    duration: float
    sample_rate: int
    channels: int
    channel_layout: Optional[str]
    bit_rate: Optional[int]

    def to_dict(self) -> dict:
        return {
            "format": self.format_label,
            "codec": self.codec,
            "duration": self.duration,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "channel_layout": self.channel_layout,
            "bit_rate": self.bit_rate,
        }


def _run(cmd: list[str], timeout: float = 120) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout)
    except FileNotFoundError as e:
        raise AudioError(f"'{cmd[0]}' was not found. Is FFmpeg installed and on PATH?") from e
    except subprocess.TimeoutExpired as e:
        raise AudioError("Audio analysis timed out.") from e


def format_label_for(format_name: str) -> Optional[str]:
    names = set(format_name.split(","))
    for label, demuxers in INPUT_FORMATS.items():
        if names & demuxers:
            return label
    return None


def probe(path: Path) -> AudioInfo:
    """Inspect a file with ffprobe and make sure it is decodable, supported audio."""
    proc = _run(
        [settings.ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        timeout=60,
    )
    if proc.returncode != 0:
        raise AudioError("This file could not be read as audio. It may be corrupted or not an audio file.")
    try:
        data = json.loads(proc.stdout or b"{}")
    except json.JSONDecodeError as e:
        raise AudioError("Could not read the audio metadata.") from e

    fmt = data.get("format") or {}
    format_name = fmt.get("format_name", "")
    label = format_label_for(format_name)
    if label is None:
        raise AudioError(
            f"Unsupported format ({format_name or 'unknown'}). Supported formats: MP3, WAV, OGG, FLAC, M4A, AAC, WEBM."
        )

    streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    if not streams:
        raise AudioError("No audio stream was found in this file.")
    stream = streams[0]
    codec = stream.get("codec_name") or ""
    tag = (stream.get("codec_tag_string") or "").lower()
    if not codec or codec == "none" or tag in {"drms", "enca"}:
        raise AudioError("This audio is DRM-protected or uses an unsupported codec and cannot be processed.")

    sample_rate = int(stream.get("sample_rate") or 0)
    channels = int(stream.get("channels") or 0)
    if sample_rate <= 0 or channels <= 0:
        raise AudioError("The audio stream has no valid sample rate or channel count.")

    # Make sure the start of the file actually decodes (catches truncated/corrupt files).
    check = _run([settings.ffmpeg, "-v", "error", "-xerror", "-t", "10", "-i", str(path), "-map", "0:a:0", "-f", "null", "-"])
    if check.returncode != 0:
        msg = check.stderr.decode(errors="replace").strip().splitlines()
        hint = f" ({msg[-1][:160]})" if msg else ""
        raise AudioError(f"The audio data could not be decoded; the file appears to be corrupted{hint}.")

    duration = _float(stream.get("duration")) or _float(fmt.get("duration"))
    if not duration or duration <= 0 or label in ("AAC", "MP3"):
        # MP3 and raw ADTS AAC headers often carry only a bitrate-based estimate (VBR files
        # without a Xing header), so measure the exact duration by decoding.
        duration = measure_duration(path)
    if duration <= 0:
        raise AudioError("No playable audio was found. The file appears to be corrupted or empty.")

    bit_rate = _int(stream.get("bit_rate")) or _int(fmt.get("bit_rate"))
    return AudioInfo(
        format_name=format_name,
        format_label=label,
        codec=codec,
        duration=duration,
        sample_rate=sample_rate,
        channels=channels,
        channel_layout=stream.get("channel_layout"),
        bit_rate=bit_rate,
    )


def measure_duration(path: Path) -> float:
    """Exact duration by fully decoding the first audio stream."""
    proc = _run(
        [settings.ffmpeg, "-v", "error", "-nostats", "-progress", "pipe:1", "-i", str(path), "-map", "0:a:0", "-f", "null", "-"],
        timeout=600,
    )
    times = re.findall(rb"out_time_us=(\d+)", proc.stdout)
    return int(times[-1]) / 1e6 if times else 0.0


def _float(v) -> Optional[float]:
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _int(v) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def waveform(path: Path, points: int = 600) -> list[float]:
    """Peak envelope (0..1) of the audio, for display."""
    proc = _run(
        [settings.ffmpeg, "-v", "error", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", "4000", "-f", "f32le", "-"],
        timeout=600,
    )
    if proc.returncode != 0:
        return []
    samples = np.abs(np.frombuffer(proc.stdout, dtype=np.float32))
    if samples.size == 0:
        return []
    points = max(1, min(points, samples.size))
    usable = samples[: samples.size - samples.size % points]
    peaks = usable.reshape(points, -1).max(axis=1)
    top = float(peaks.max()) or 1.0
    return [round(float(p) / top, 4) for p in peaks]


# --------------------------------------------------------------------------- conversion


@dataclass
class OutputSpec:
    fmt: str  # "mp3" | "ogg"
    path: Path
    mp3_bitrate: int = 320
    ogg_quality: int = 8  # libvorbis -q:a scale 0..10 (8 = ~256 kbps stereo)


_engine_cache: Optional[bool] = None


def r3_available() -> bool:
    """Functional check: does this FFmpeg's librubberband actually run the R3 engine?

    R3 flushes a longer tail than R2 (about +95 ms on a short clip; R2's output length is
    exact), so a 1-second test tone tells the two engines apart with no version guessing.
    Override with SPEEDWAVE_RUBBERBAND_ENGINE=finer|faster.
    """
    global _engine_cache
    forced = settings.rubberband_engine
    if forced in ("finer", "faster"):
        return forced == "finer"
    if _engine_cache is None:
        proc = _run(
            [settings.ffmpeg, "-v", "error", "-f", "lavfi", "-i", "sine=f=440:d=1:r=44100",
             "-af", f"rubberband=tempo=2:smoothing={RB_OPTION_ENGINE_FINER}", "-f", "f32le", "-"],
            timeout=30,
        )
        seconds = len(proc.stdout) / 4 / 44100 if proc.returncode == 0 else 0.0
        _engine_cache = seconds > 0.53
    return _engine_cache


def build_stretch_filter(speed: float, quality: str, clip_protection: bool, target_duration: Optional[float] = None) -> str:
    """The pitch-preserving time-stretch chain (applied once, shared by all outputs)."""
    use_r3 = quality != "fast" and r3_available()
    if use_r3:
        # channels=together: R3 analyses the channels jointly, which keeps the stereo image
        # coherent; level and pitch stay exact in tests.
        chain = f"rubberband=tempo={speed:.6g}:pitch=1:smoothing={RB_OPTION_ENGINE_FINER}:channels=together"
    else:
        # R2: transients=mixed was the best all-round setting in measurements. The default,
        # crisp, added warble on held notes. channels=together distorted wide stereo in R2.
        chain = f"rubberband=tempo={speed:.6g}:pitch=1:transients=mixed:detector=compound:phase=laminar:window=standard:channels=apart"
    if target_duration:
        # Drop the engine's flushed tail so the result is exactly duration / speed.
        chain += f",atrim=duration={target_duration:.6f}"
    if clip_protection:
        limit = 10 ** (CLIP_CEILING_DB / 20)
        # Lookahead peak limiter with auto-gain disabled: samples below the ceiling pass
        # through unchanged, and delay compensation keeps the timing exact.
        chain += f",alimiter=limit={limit:.4f}:attack=5:release=50:level=false:latency=true"
    return chain


def mp3_sample_rate(sr: int) -> int:
    """LAME only supports a fixed set of rates; pick the nearest one at or above `sr`."""
    if sr in MP3_SAMPLE_RATES:
        return sr
    if sr > 48000:
        return 48000
    return min(r for r in MP3_SAMPLE_RATES if r >= sr)


def build_command(src: Path, info: AudioInfo, outputs: list[OutputSpec], speed: float, quality: str, clip_protection: bool) -> list[str]:
    stretch = build_stretch_filter(speed, quality, clip_protection, info.duration / speed)
    n = len(outputs)
    labels = [f"o{i}" for i in range(n)]
    graph = f"[0:a:0]{stretch}"
    if n > 1:
        graph += f",asplit={n}" + "".join(f"[s{i}]" for i in range(n))
    else:
        graph += "[s0]"
    for i, out in enumerate(outputs):
        post = []
        if out.fmt == "mp3":
            sr = mp3_sample_rate(info.sample_rate)
            if sr != info.sample_rate:
                post.append(f"aresample={sr}:resampler=soxr:precision=28")
            if info.channels > 2:
                post.append("pan=stereo|FL<FL+0.707*FC+0.707*BL+0.707*SL|FR<FR+0.707*FC+0.707*BR+0.707*SR")
        graph += f";[s{i}]{','.join(post) or 'anull'}[{labels[i]}]"

    cmd = [settings.ffmpeg, "-hide_banner", "-nostdin", "-y", "-v", "error", "-i", str(src), "-filter_complex", graph]
    for i, out in enumerate(outputs):
        # Keep title/artist/album tags, but drop tags that describe the original timing.
        cmd += ["-map", f"[{labels[i]}]", "-map_metadata", "0", "-map_chapters", "-1"]
        cmd += ["-metadata", "TLEN=", "-metadata", "iTunSMPB=", "-metadata", "LENGTH="]
        if out.fmt == "mp3":
            cmd += ["-c:a", "libmp3lame", "-b:a", f"{out.mp3_bitrate}k", "-compression_level", "0", "-id3v2_version", "3"]
        else:
            cmd += ["-c:a", "libvorbis", "-q:a", str(out.ogg_quality)]
        cmd += [str(out.path)]
    cmd += ["-progress", "pipe:1", "-nostats"]
    return cmd


ProgressCallback = Callable[[float, float], None]  # (fraction 0..1, processed_output_seconds)


def convert(
    src: Path,
    info: AudioInfo,
    outputs: list[OutputSpec],
    speed: float,
    quality: str = DEFAULT_QUALITY,
    clip_protection: bool = True,
    on_progress: Optional[ProgressCallback] = None,
    cancel: Optional[threading.Event] = None,
) -> None:
    """Run the conversion, reporting real progress parsed from ffmpeg's -progress output."""
    if not (MIN_SPEED <= speed <= MAX_SPEED):
        raise AudioError(f"Speed must be between {MIN_SPEED}x and {MAX_SPEED}x.")
    cmd = build_command(src, info, outputs, speed, quality, clip_protection)
    expected = info.duration / speed
    stderr_path = outputs[0].path.parent / "ffmpeg.log"

    with open(stderr_path, "wb") as errf:
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errf, stdin=subprocess.DEVNULL)
        except FileNotFoundError as e:
            raise AudioError("FFmpeg was not found. Is it installed and on PATH?") from e

        killer_done = threading.Event()

        def watch_cancel():
            while not killer_done.is_set():
                if cancel is not None and cancel.wait(0.2):
                    proc.kill()
                    return

        watcher = threading.Thread(target=watch_cancel, daemon=True)
        watcher.start()
        try:
            assert proc.stdout is not None
            for raw in proc.stdout:
                line = raw.decode(errors="replace").strip()
                if line.startswith("out_time_us=") and on_progress:
                    try:
                        t = int(line.split("=", 1)[1]) / 1e6
                    except ValueError:
                        continue
                    on_progress(min(max(t / expected, 0.0), 1.0) if expected > 0 else 0.0, t)
            proc.wait()
        finally:
            killer_done.set()
            if proc.poll() is None:
                proc.kill()
                proc.wait()

    if cancel is not None and cancel.is_set():
        raise CancelledError()
    if proc.returncode != 0:
        log = stderr_path.read_text(errors="replace").strip().splitlines()
        detail = log[-1][:300] if log else f"exit code {proc.returncode}"
        raise AudioError(f"FFmpeg failed while processing the audio: {detail}")
    for out in outputs:
        if not out.path.exists() or out.path.stat().st_size == 0:
            raise AudioError(f"FFmpeg produced no {out.fmt.upper()} output.")


def verify_output(path: Path, fmt: str) -> dict:
    """Probe a produced file and return its properties."""
    proc = _run([settings.ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    if proc.returncode != 0:
        raise AudioError(f"The produced {fmt.upper()} file is not readable.")
    data = json.loads(proc.stdout)
    streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    if not streams or streams[0].get("codec_name") != OUTPUT_FORMATS[fmt]["codec"]:
        raise AudioError(f"The produced {fmt.upper()} file has an unexpected codec.")
    s, f = streams[0], data.get("format", {})
    duration = _float(f.get("duration")) or _float(s.get("duration")) or 0.0
    return {
        "duration": duration,
        "sample_rate": int(s.get("sample_rate") or 0),
        "channels": int(s.get("channels") or 0),
        "bit_rate": _int(f.get("bit_rate")),
        "size": path.stat().st_size,
    }


# --------------------------------------------------------------------------- environment


def engine_status() -> dict:
    """Report whether FFmpeg, Rubber Band and the encoders are usable."""
    status = {"ffmpeg": None, "rubberband": False, "libmp3lame": False, "libvorbis": False, "soxr": False}
    try:
        v = subprocess.run([settings.ffmpeg, "-hide_banner", "-version"], capture_output=True, timeout=10)
        first = v.stdout.decode(errors="replace").splitlines()
        status["ffmpeg"] = first[0] if first else "unknown"
        filters = subprocess.run([settings.ffmpeg, "-hide_banner", "-filters"], capture_output=True, timeout=10).stdout.decode()
        encoders = subprocess.run([settings.ffmpeg, "-hide_banner", "-encoders"], capture_output=True, timeout=10).stdout.decode()
        status["rubberband"] = bool(re.search(r"\srubberband\s", filters))
        status["libmp3lame"] = "libmp3lame" in encoders
        status["libvorbis"] = "libvorbis" in encoders
        status["soxr"] = "--enable-libsoxr" in v.stdout.decode(errors="replace")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    status["rubberband_engine"] = ("R3 (finer)" if r3_available() else "R2 (faster)") if status["rubberband"] else None
    status["ok"] = bool(status["ffmpeg"] and status["rubberband"] and status["libmp3lame"] and status["libvorbis"])
    return status


def now() -> float:
    return time.time()
