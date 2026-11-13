"""Test-signal generation and analysis helpers (numpy + ffmpeg)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

SR = 44100


def write_audio(path: Path, data: np.ndarray, sr: int = SR, codec_args: list[str] | None = None) -> Path:
    """Write float samples (frames x channels) via ffmpeg into any format implied by `path`."""
    data = np.atleast_2d(data.T).T if data.ndim == 1 else data
    channels = data.shape[1]
    args = codec_args if codec_args is not None else (["-c:a", "pcm_s16le"] if path.suffix == ".wav" else [])
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", str(channels), "-i", "-", *args, str(path)],
        input=data.astype(np.float32).tobytes(),
        check=True,
    )
    return path


def tone(freqs: list[float], seconds: float, amp: float = 0.25, sr: int = SR) -> np.ndarray:
    t = np.arange(int(seconds * sr)) / sr
    return sum(amp * np.sin(2 * np.pi * f * t) for f in freqs)


def stereo_test_signal(seconds: float = 60.0, sr: int = SR) -> np.ndarray:
    """Left: 440 Hz (A4). Right: 660 Hz (E5). Distinct per-channel pitches."""
    return np.stack([tone([440.0], seconds, 0.4, sr), tone([660.0], seconds, 0.4, sr)], axis=1)


def decode(path: Path, sr: int = SR, channels: int | None = None) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-f", "f32le", "-ar", str(sr)]
    if channels:
        cmd += ["-ac", str(channels)]
    proc = subprocess.run(cmd + ["-"], capture_output=True, check=True)
    ch = channels or probe(path)["channels"]
    return np.frombuffer(proc.stdout, dtype=np.float32).reshape(-1, ch).astype(np.float64)


def probe(path: Path) -> dict:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True, check=True,
    )
    d = json.loads(proc.stdout)
    s = [x for x in d["streams"] if x["codec_type"] == "audio"][0]
    return {
        "codec": s["codec_name"],
        "channels": int(s["channels"]),
        "sample_rate": int(s["sample_rate"]),
        "duration": float(d["format"]["duration"]),
        "bit_rate": int(d["format"].get("bit_rate", 0)),
        "format": d["format"]["format_name"],
    }


def spectrum(x: np.ndarray, sr: int = SR) -> tuple[np.ndarray, np.ndarray]:
    w = np.blackman(len(x))
    return np.fft.rfftfreq(len(x), 1 / sr), np.abs(np.fft.rfft(x * w)) ** 2


def dominant_frequency(x: np.ndarray, sr: int = SR) -> float:
    """Peak frequency with parabolic interpolation (sub-bin accuracy)."""
    freqs, p = spectrum(x, sr)
    mag = np.sqrt(p)
    k = int(np.argmax(mag[1:-1])) + 1
    a, b, c = np.log(mag[k - 1] + 1e-20), np.log(mag[k] + 1e-20), np.log(mag[k + 1] + 1e-20)
    offset = 0.5 * (a - c) / (a - 2 * b + c)
    return float((k + offset) * sr / len(x))


def tone_snr_db(x: np.ndarray, freqs: list[float], sr: int = SR, width_hz: float = 6.0) -> float:
    """Energy at the expected tones vs. everything else (artifacts, noise, distortion)."""
    f, p = spectrum(x, sr)
    mask = np.zeros_like(p, dtype=bool)
    for t in freqs:
        mask |= np.abs(f - t) < width_hz
    return float(10 * np.log10(p[mask].sum() / max(p[~mask].sum(), 1e-30)))


def rms_db(x: np.ndarray) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(x**2)) + 1e-20))


def steady(x: np.ndarray, sr: int = SR, trim: float = 1.0) -> np.ndarray:
    """Drop the first/last `trim` seconds (filter warm-up and encoder padding)."""
    n = int(trim * sr)
    return x[n:-n] if len(x) > 2 * n else x
