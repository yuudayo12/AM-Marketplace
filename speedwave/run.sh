#!/usr/bin/env bash
# Build the frontend (if needed) and start SpeedWave on http://localhost:8000
set -euo pipefail
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || { echo "ffmpeg not found. Install FFmpeg built with librubberband (see README)."; exit 1; }
if [ ! -d backend/.venv ]; then python3 -m venv backend/.venv; fi
backend/.venv/bin/pip install -q -r backend/requirements.txt
if [ ! -d frontend/dist ] || [ "${REBUILD:-0}" = "1" ]; then
  (cd frontend && npm install --no-audit --no-fund && npm run build)
fi
cd backend && exec .venv/bin/uvicorn app.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
