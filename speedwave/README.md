# SPEEDWAVE — Professional Audio Speed Converter

SpeedWave is a web app that speeds audio up (2× by default) **without changing pitch or key**. Upload a file
or paste a direct audio link, convert it with FFmpeg + the Rubber Band Library, preview the result, and
download it as MP3 and/or OGG.

No AI and no generated audio. SpeedWave time-stretches your original audio and nothing else.

```
speedwave/
├── backend/          FastAPI + FFmpeg/Rubber Band engine + test suite
│   ├── app/
│   │   ├── main.py        HTTP API, session cookies, static frontend
│   │   ├── audio.py       probing, time-stretch filter, encoding, verification
│   │   ├── store.py       sources/jobs, async queue, dedup, cleanup
│   │   ├── url_import.py  safe direct-URL downloader
│   │   └── config.py      environment configuration
│   └── tests/             audio-quality + API tests (pytest)
├── frontend/         React + TypeScript + Tailwind (Vite)
├── run.sh            one-command local start
└── Dockerfile
```

---

## 1. Requirements

| Dependency | Version | Notes |
|---|---|---|
| **FFmpeg** | 5.1+ | Must be built with `--enable-librubberband`, `libmp3lame` and `libvorbis` (`libsoxr` is recommended). Ubuntu/Debian/Homebrew packages include all of these. |
| **Rubber Band Library** | 3.x recommended | Linked into FFmpeg. 3.x provides the high-quality **R3** engine. With 2.x, SpeedWave falls back to R2 automatically. |
| Python | 3.10+ | Backend |
| Node.js | 18+ | Building the frontend |

Check your FFmpeg:

```bash
ffmpeg -hide_banner -filters | grep rubberband      # should print the rubberband filter
ffmpeg -hide_banner -encoders | grep -E "libmp3lame|libvorbis"
```

Install FFmpeg:

* **Ubuntu / Debian:** `sudo apt install ffmpeg`
* **macOS:** `brew install ffmpeg` (includes rubberband)
* **Windows:** use a "full" build from gyan.dev (includes librubberband), or run SpeedWave with Docker.

## 2. Installation

```bash
cd speedwave

# backend
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements-dev.txt

# frontend
cd frontend && npm install && npm run build && cd ..
```

## 3. Running locally

**Production-style (single server):**

```bash
./run.sh                    # builds the frontend if needed, serves on http://localhost:8000
```

**Development (hot reload):**

```bash
# terminal 1 — API on :8000
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000
# terminal 2 — UI on :5173 (proxies /api to :8000)
cd frontend && npm run dev
```

Open http://localhost:5173 in dev mode, or http://localhost:8000 when using `run.sh`.

**Docker:**

```bash
docker build -t speedwave . && docker run -p 8000:8000 speedwave
```

**Tests:**

```bash
cd backend && .venv/bin/pytest          # 64 tests, about 1 minute
```

### Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `SPEEDWAVE_MAX_UPLOAD_MB` | `500` | Max upload / URL download size |
| `SPEEDWAVE_MAX_DURATION_MINUTES` | `240` | Max audio length |
| `SPEEDWAVE_MAX_CONCURRENT_JOBS` | `2` | Parallel conversions. Extra jobs wait in a queue |
| `SPEEDWAVE_FILE_TTL_MINUTES` | `60` | Files are deleted this long after last access |
| `SPEEDWAVE_DATA_DIR` | `$TMP/speedwave` | Working storage |
| `SPEEDWAVE_RUBBERBAND_ENGINE` | `auto` | `auto`, `finer` (force R3) or `faster` (force R2) |
| `SPEEDWAVE_FFMPEG` / `SPEEDWAVE_FFPROBE` | `ffmpeg` / `ffprobe` | Binary paths |
| `SPEEDWAVE_ALLOW_PRIVATE_URLS` | `0` | Allow URL import from LAN/localhost (keep off on servers) |
| `SPEEDWAVE_URL_TIMEOUT_SECONDS` | `30` | URL download timeout |
| `SPEEDWAVE_CORS_ORIGINS` | – | Only needed if the UI is hosted on a different origin |
| `SPEEDWAVE_COOKIE_SECURE` | `0` | Set `1` when serving over HTTPS |

## 4. How to use

1. **Input:** drag an MP3/WAV/OGG/FLAC/M4A/AAC file onto the drop zone, click **Browse Files**, or paste a
   direct link (e.g. `https://example.com/track.mp3`) and click **Import URL**.
2. **Audio Information:** check the filename, format, size, duration, channels and bitrate, and preview the
   original on its waveform. Click the waveform to seek.
3. **Processing Settings:**
   * *Playback speed:* 2× by default (1.25× to 3× available).
   * *Pitch preservation:* always on.
   * *Output format:* MP3, OGG or both. MP3 bitrate defaults to 320 kbps; OGG quality defaults to q8.
   * *Stretch engine:* **Studio (R3)** is recommended. **Fast (R2)** is about 2× quicker.
   * *Clip protection:* a transparent −1 dBFS peak limiter (details below).
4. Click **CONVERT AUDIO TO 2X**. The status panel shows real progress read from FFmpeg, the remaining
   time, elapsed time and processing speed. You can cancel at any point.
5. **Download:** compare original and processed durations, preview each output, and click **Download MP3** /
   **Download OGG**. Files are named like `song_2x.mp3`.

## 5. How the audio processing works

```
source ─► ffmpeg decode ─► rubberband (tempo=2, pitch=1) ─► atrim (exact length) ─► [alimiter −1 dBFS]
                                                                    └─► asplit ─┬─► libmp3lame CBR 320k ─► song_2x.mp3
                                                                                └─► libvorbis q8         ─► song_2x.ogg
```

* **Pitch-preserving time-stretch:** Rubber Band is a phase-vocoder time-stretcher. It changes tempo
  while keeping frequencies, so key and pitch stay the same. SpeedWave never uses sample-rate tricks
  (`asetrate`), because those shift pitch.
* **R3 engine:** FFmpeg's filter defaults to Rubber Band's older R2 engine. In SpeedWave's measurements, R2
  lost up to 3.5 dB of level and drifted up to 5% in pitch on sustained pure tones. R3 ("finer") held level
  within 0.01 dB and pitch within 0.001% from 110 Hz to 5 kHz. FFmpeg has no named option for R3, so
  SpeedWave passes `RubberBandOptionEngineFiner` through the filter's option bitmask. At startup it runs a
  functional test to confirm the engine is really active. The header badge and `/api/health` show which
  engine is in use.
* **One stretch, several encodes:** the audio is stretched once and split to both encoders, with no lossy
  intermediate file.
* **Exact length:** the output is trimmed to `original duration ÷ speed`. Every output is then checked with
  ffprobe for codec, channels and duration before it is offered for download.
* **Stereo** stays stereo, and mono stays mono. Surround input is downmixed to stereo for MP3 only.
  Above-48 kHz input is resampled with SoX-R for MP3, since LAME's maximum is 48 kHz; Vorbis keeps the
  original rate.
* **Clip protection:** speeding up can raise peaks a little, and lossy decoders can overshoot. With the
  option on, a lookahead limiter (no auto-gain, latency compensated) catches only samples above −1 dBFS.
  Audio below that level passes through unchanged; the tests check this. Volume is never normalised.
* **Metadata:** title/artist/album tags are copied. Tags that describe the original length are dropped.

## 6. Privacy, safety and reliability

* Every browser gets an anonymous session cookie. Sources, jobs and downloads are only visible to that
  session.
* Originals are stored read-only and never modified. Outputs go to a separate per-job folder.
* Jobs run in a background queue (`MAX_CONCURRENT_JOBS`), so the UI never blocks. Submitting the same
  file with the same settings twice returns the existing job instead of converting again.
* Files expire automatically (`FILE_TTL_MINUTES`), and leftovers from earlier runs are swept up too.
  **Remove** in the UI deletes them immediately.
* URL import fetches plain HTTP(S) files only. It rejects private/internal addresses (SSRF protection),
  checks every redirect, enforces the size limit while streaming, and refuses streaming-platform pages,
  login-protected links (401/403) and DRM-protected files. It never tries to bypass any of these.

## 7. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Red banner: *"audio engine is incomplete"* | FFmpeg lacks rubberband, LAME or Vorbis. Run the checks in §1, install a full FFmpeg build, or point `SPEEDWAVE_FFMPEG` at one. `curl localhost:8000/api/health` shows what is missing. |
| Header shows **Rubber Band R2** | FFmpeg is linked against Rubber Band 2.x. Conversion still works with good quality. Upgrade librubberband to 3.x (or use Docker) to get R3. |
| *"Cannot reach the SpeedWave server"* | The backend isn't running, or (in dev mode) it isn't on port 8000. Set `SPEEDWAVE_API` for Vite if you use another port. |
| *"Unsupported format"* | Only MP3, WAV, OGG, FLAC, M4A and AAC containers are accepted. Convert other formats first. |
| *"appears to be corrupted"* / *"No playable audio"* | The file doesn't decode, often because it is truncated or mislabelled. Re-export or re-download it. |
| *"DRM-protected"* | Protected files (e.g. iTunes FairPlay `.m4p`/`drms`) cannot be processed. |
| *"This is a YouTube/Spotify… page"* | Only direct file links work. Download the file through the platform's own permitted options and upload it. |
| *"Access denied: requires a login"* | The link needs authentication. Download it in your browser and upload the file. |
| *"points to a web page"* | You copied a page link, not the file link. Right-click the download button and copy the link address. |
| *"private, local or internal network addresses"* | Blocked by SSRF protection. For local use only, set `SPEEDWAVE_ALLOW_PRIVATE_URLS=1`. |
| 413 / *"larger than the … limit"* | Raise `SPEEDWAVE_MAX_UPLOAD_MB` (and any reverse-proxy body limit, e.g. nginx `client_max_body_size`). |
| *"FFmpeg failed while processing"* | The last FFmpeg error line is shown. While a job runs, the full log is in `<DATA_DIR>/<session>/<source>/jobs/<job>/ffmpeg.log`; the server log also has details. |
| *"output duration … does not match"* | The source's header durations are wrong. Re-encode the source (e.g. `ffmpeg -i in.mp3 fixed.wav`) and retry. |
| Slight "phasey" or soft drums | That's a time-stretch artefact. Use **Studio (R3)**; if you chose Fast (R2), switch back. |
| Preview won't play | Some browsers can't play every input format (e.g. FLAC in old Safari). Conversion and downloads are unaffected. |
| Files disappeared | They expired after `FILE_TTL_MINUTES` of inactivity, or the server restarted (the job registry is held in memory). Upload again. |

## 8. API reference

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Engine status (FFmpeg, rubberband + engine, encoders) |
| GET | `/api/config` | Limits and options for the UI |
| POST | `/api/sources/upload` | multipart `file` → source info |
| POST | `/api/sources/url` | `{"url": "..."}` → source info |
| GET | `/api/sources/{id}` · `/audio` · `/waveform` | Info, original audio (supports Range), waveform peaks |
| DELETE | `/api/sources/{id}` | Delete the source and its outputs |
| POST | `/api/jobs` | `{source_id, speed, formats, mp3_bitrate, ogg_quality, quality, clip_protection}` → job (202) |
| GET | `/api/jobs/{id}` | Status, progress, ETA, outputs |
| POST | `/api/jobs/{id}/cancel` | Cancel |
| GET | `/api/jobs/{id}/download/{mp3\|ogg}` | Download (`?inline=1` for preview) |
| GET | `/api/jobs/{id}/waveform/{fmt}` | Waveform peaks of the result |
