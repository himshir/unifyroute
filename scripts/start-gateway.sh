#!/usr/bin/env bash
set -e

# Source .env if it exists
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

# Default port to 6565 if not set
PORT="${PORT:-6565}"
HOST="${HOST:-0.0.0.0}"

# Locate uv
UV="uv"
if ! command -v uv &>/dev/null; then
  if [ -x "$HOME/.local/bin/uv" ]; then
    UV="$HOME/.local/bin/uv"
  else
    echo "❌ Error: 'uv' not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
  fi
fi

echo "Starting UnifyRoute Unified Launcher on $HOST:$PORT..."
"$UV" run --package launcher uvicorn --app-dir launcher/src launcher.main:app --port "$PORT" --host "$HOST"
