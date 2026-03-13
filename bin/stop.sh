#!/usr/bin/env sh
# Stop a running game-notifier instance via its PID file.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$DIR/data/game-notifier.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "game-notifier does not appear to be running (no PID file found)."
    exit 1
fi

APP_PID=$(cat "$PID_FILE")
echo "Stopping game-notifier (PID $APP_PID)..."
kill "$APP_PID" 2>/dev/null && rm -f "$PID_FILE"
echo "Done."
