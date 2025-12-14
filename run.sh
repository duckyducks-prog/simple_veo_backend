#!/usr/bin/env bash
set -euo pipefail

# Create virtualenv (if missing), install requirements, and run uv/uvicorn
VENV_DIR=".venv"
REQ_FILE="requirements.txt"
PORT=${PORT:-8080}

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment in $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

# Activate venv for this script
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# Upgrade pip and install requirements
python -m pip install --upgrade pip
if [ -f "$REQ_FILE" ]; then
  pip install -r "$REQ_FILE"
fi

# Prefer `uv` then `uvicorn`
if command -v uv >/dev/null 2>&1; then
  CMD=uv
elif command -v uvicorn >/dev/null 2>&1; then
  CMD=uvicorn
else
  echo "uv/uvicorn not found after installing requirements. Exiting." >&2
  exit 1
fi

echo "Starting $CMD on 0.0.0.0:$PORT"
exec "$CMD" main:app --host 0.0.0.0 --port "$PORT" --reload
