"""Audio-quality verification of the conversion engine using known test signals."""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pytest

from app import audio
from tests.signals import (
    SR, decode, dominant_frequency, probe, rms_db, steady, stereo_test_signal, tone, tone_snr_db, write_audio,
)


def run(src: Path, out_dir: Path, speed=2.0, formats=("mp3", "ogg"), quality="studio", clip=True, bitrate=320):
    info = audio.probe(src)
    specs = [audio.OutputSpec(fmt=f, path=out_dir / f"out_{speed}_{quality}.{f}", mp3_bitrate=bitrate) for f in formats]
    progress = []
    audio.convert(src, info, specs, speed, quality, clip, on_progress=lambda p, t: progress.append(p))
    return {s.fmt: s.path for s in specs}, progress


@pytest.fixture(scope="module")
def minute_stereo(tmp_path_factory) -> Path:
    d = tmp_path_factory.mktemp("signals")
    return write_audio(d / "stereo_60s.wav", stereo_test_signal(60.0))


@pytest.fixture(scope="module")
def converted(minute_stereo, tmp_path_factory):
    outs, progress = run(minute_stereo, tmp_path_factory.mktemp("out"))
    return outs, progress


# 1. A 1-minute file becomes ~30 seconds at 2x --------------------------------------


@pytest.mark.parametrize("fmt", ["mp3", "ogg"])
def test_one_minute_becomes_thirty_seconds(converted, fmt):
    outs, _ = converted
    meta = probe(outs[fmt])
    assert meta["duration"] == pytest.approx(30.0, abs=0.15)
    # Decoded sample count agrees with the container duration.
    assert len(decode(outs[fmt])) / SR == pytest.approx(30.0, abs=0.15)


@pytest.mark.parametrize("speed", [1.5, 2.5, 3.0])
def test_other_speeds_scale_duration(tmp_path, speed):
    src = write_audio(tmp_path / "s.wav", stereo_test_signal(12.0))
    outs, _ = run(src, tmp_path, speed=speed, formats=("ogg",))
    assert probe(outs["ogg"])["duration"] == pytest.approx(12.0 / speed, abs=0.12)


def test_progress_is_real_and_monotonic(converted):
    _, progress = converted
    assert len(progress) >= 2
    assert progress == sorted(progress)
    assert progress[-1] == pytest.approx(1.0, abs=0.02)


# 2. Pitch is unchanged ------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["mp3", "ogg"])
def test_pitch_preserved(converted, fmt):
    x = steady(decode(converted[0][fmt]))
    left, right = dominant_frequency(x[:, 0]), dominant_frequency(x[:, 1])
    # 0.3% is about 5 cents; a naive 2x resample would read 880 / 1320 Hz.
    assert left == pytest.approx(440.0, rel=0.003)
    assert right == pytest.approx(660.0, rel=0.003)


@pytest.mark.parametrize("quality", list(audio.QUALITY_MODES))
def test_pitch_preserved_every_quality_mode(tmp_path, quality):
    src = write_audio(tmp_path / "s.wav", stereo_test_signal(10.0))
    outs, _ = run(src, tmp_path, quality=quality, formats=("ogg",))
    x = steady(decode(outs["ogg"]))
    assert dominant_frequency(x[:, 0]) == pytest.approx(440.0, rel=0.01)
    assert dominant_frequency(x[:, 1]) == pytest.approx(660.0, rel=0.01)


def test_filter_is_pitch_preserving_time_stretch():
    for quality in audio.QUALITY_MODES:
        chain = audio.build_stretch_filter(2.0, quality, True, 30.0)
        assert chain.startswith("rubberband=tempo=2:pitch=1:")
        assert "asetrate" not in chain and "atempo" not in chain


def test_r3_engine_detected():
    """FFmpeg here links Rubber Band 3.x, so the high-quality R3 engine must be in use."""
    assert audio.r3_available()
    assert f"smoothing={audio.RB_OPTION_ENGINE_FINER}" in audio.build_stretch_filter(2.0, "studio", False)


def test_pitch_and_level_exact_across_spectrum(tmp_path):
    """One pure tone per channel, 110 Hz to 5 kHz: pitch and level must be untouched."""
    freqs = [110.0, 220.0, 440.0, 660.0, 1000.0, 1760.0, 3000.0, 5000.0]
    sig = np.stack([tone([f], 8.0, 0.4) for f in freqs], axis=1)
    src = write_audio(tmp_path / "multi.wav", sig, codec_args=["-c:a", "pcm_f32le"])
    out = tmp_path / "multi_out.wav"
    chain = audio.build_stretch_filter(2.0, "studio", True, 4.0)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", chain, "-c:a", "pcm_f32le", str(out)], check=True)
    x = steady(decode(out))
    assert len(decode(out)) / SR == pytest.approx(4.0, abs=0.001)
    for i, f in enumerate(freqs):
        assert dominant_frequency(x[:, i]) == pytest.approx(f, rel=0.0005), f"{f} Hz pitch moved"
        assert rms_db(x[:, i]) == pytest.approx(rms_db(sig[:, i]), abs=0.1), f"{f} Hz level changed"
        assert tone_snr_db(x[:, i], [f]) > 25, f"{f} Hz has artifacts"


# 3. Stereo stays stereo -----------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["mp3", "ogg"])
def test_stereo_preserved_and_channels_not_mixed(converted, fmt):
    outs, _ = converted
    assert probe(outs[fmt])["channels"] == 2
    x = steady(decode(outs[fmt]))
    # Left must still be the 440 Hz channel, right the 660 Hz one, with strong separation.
    assert tone_snr_db(x[:, 0], [440.0]) > 15
    assert tone_snr_db(x[:, 0], [660.0]) < -25
    assert tone_snr_db(x[:, 1], [660.0]) > 15
    assert tone_snr_db(x[:, 1], [440.0]) < -25


def test_mono_stays_mono(tmp_path):
    src = write_audio(tmp_path / "mono.wav", tone([440.0], 6.0))
    outs, _ = run(src, tmp_path)
    assert probe(outs["mp3"])["channels"] == 1
    assert probe(outs["ogg"])["channels"] == 1


# 4. Output plays successfully -------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["mp3", "ogg"])
def test_output_decodes_without_errors(converted, fmt):
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-xerror", "-i", str(converted[0][fmt]), "-f", "null", "-"], capture_output=True
    )
    assert proc.returncode == 0 and proc.stderr == b""


# 5. MP3 and OGG are valid ------------------------------------------------------------------


def test_mp3_is_valid_320k(converted):
    meta = probe(converted[0]["mp3"])
    assert meta["codec"] == "mp3" and meta["format"] == "mp3"
    assert meta["sample_rate"] == 44100
    assert meta["bit_rate"] == pytest.approx(320_000, rel=0.02)
    assert converted[0]["mp3"].read_bytes()[:3] == b"ID3"


@pytest.mark.parametrize("bitrate", [128, 192, 256])
def test_mp3_bitrate_is_configurable(tmp_path, bitrate):
    src = write_audio(tmp_path / "s.wav", stereo_test_signal(8.0))
    outs, _ = run(src, tmp_path, formats=("mp3",), bitrate=bitrate)
    assert probe(outs["mp3"])["bit_rate"] == pytest.approx(bitrate * 1000, rel=0.03)


def test_ogg_is_valid_vorbis(converted):
    meta = probe(converted[0]["ogg"])
    assert meta["codec"] == "vorbis" and meta["format"] == "ogg"
    assert converted[0]["ogg"].read_bytes()[:4] == b"OggS"


def test_high_sample_rate_input_resampled_for_mp3(tmp_path):
    src = write_audio(tmp_path / "hi.wav", stereo_test_signal(5.0, sr=96000), sr=96000)
    outs, _ = run(src, tmp_path)
    assert probe(outs["mp3"])["sample_rate"] == 48000  # LAME maximum
    assert probe(outs["ogg"])["sample_rate"] == 96000  # Vorbis keeps the original rate
    x = steady(decode(outs["mp3"], sr=48000), sr=48000)
    assert dominant_frequency(x[:, 0], sr=48000) == pytest.approx(440.0, rel=0.003)


# 6. No clipping / excessive distortion / unexpected volume change ------------------------


def test_level_unchanged_and_low_distortion(converted, minute_stereo):
    src = steady(decode(minute_stereo))
    for fmt in ("mp3", "ogg"):
        x = steady(decode(converted[0][fmt]))
        for c in range(2):
            # No unexpected volume change: within 0.5 dB RMS of the original.
            assert rms_db(x[:, c]) == pytest.approx(rms_db(src[:, c]), abs=0.5)
        # Peak stays well below full scale for a -8 dBFS input.
        assert np.abs(x).max() < 0.6
        # Pure-tone purity: artifacts at least 20 dB below the tone.
        assert tone_snr_db(x[:, 0], [440.0]) > 20
        assert tone_snr_db(x[:, 1], [660.0]) > 18


def test_studio_quality_is_very_clean_on_chords(tmp_path):
    left = tone([261.63, 329.63, 392.0], 12.0, 0.2)
    right = tone([261.63, 523.25], 12.0, 0.2)
    src = write_audio(tmp_path / "chord.wav", np.stack([left, right], axis=1), codec_args=["-c:a", "pcm_f32le"])
    outs, _ = run(src, tmp_path, formats=("ogg",))
    x = steady(decode(outs["ogg"]))
    assert tone_snr_db(x[:, 0], [261.63, 329.63, 392.0]) > 40
    assert tone_snr_db(x[:, 1], [261.63, 523.25]) > 40


def _hot_master(seconds: float = 12.0) -> np.ndarray:
    """A loud, full-scale signal: chord + noise bursts normalised to -0.1 dBFS."""
    rng = np.random.default_rng(7)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    chord = sum(np.sin(2 * np.pi * f * t) for f in (110.0, 220.0, 277.18, 329.63))
    bursts = rng.standard_normal(n) * (np.sin(2 * np.pi * 2 * t) > 0.95)
    sig = chord + 1.5 * bursts
    sig = np.stack([sig, np.roll(sig, 300)], axis=1)
    return sig / np.abs(sig).max() * 10 ** (-0.1 / 20)


def test_no_clipping_on_full_scale_input(tmp_path):
    src = write_audio(tmp_path / "hot.wav", _hot_master(), codec_args=["-c:a", "pcm_f32le"])
    outs, _ = run(src, tmp_path, clip=True)
    for fmt in ("mp3", "ogg"):
        x = decode(outs[fmt])
        assert np.abs(x).max() < 1.0, f"{fmt} output clips"
        assert np.mean(np.abs(x) > 0.999) == 0.0


def test_clip_protection_is_transparent_below_ceiling(tmp_path):
    """The limiter must not alter audio that never reaches the -1 dBFS ceiling."""
    src = write_audio(tmp_path / "quiet.wav", stereo_test_signal(8.0) * 0.5, codec_args=["-c:a", "pcm_f32le"])
    info = audio.probe(src)
    on, off = tmp_path / "on.wav", tmp_path / "off.wav"
    for path, clip in ((on, True), (off, False)):
        chain = audio.build_stretch_filter(2.0, "studio", clip, 4.0)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", chain, "-c:a", "pcm_f32le", str(path)], check=True)
    a, b = decode(on), decode(off)
    n = min(len(a), len(b))
    assert abs(len(a) - len(b)) < SR * 0.01  # latency compensated: same length / timing
    assert np.max(np.abs(a[:n] - b[:n])) < 1e-4
    assert info.duration == pytest.approx(8.0, abs=0.01)
