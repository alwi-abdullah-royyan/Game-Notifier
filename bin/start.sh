#!/usr/bin/env sh
# Start game-notifier in the background (Linux / macOS desktop).
DIR="$(cd "$(dirname "$0")/.." && pwd)"
nohup "$DIR/.venv/bin/game-notifier" >/dev/null 2>&1 &
echo "game-notifier started"
