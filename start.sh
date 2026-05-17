#!/bin/bash
# UAV Watcher — start both watcher and web config UI
cd "$(dirname "$0")"

PYTHON=$(command -v python3 || command -v python)

if command -v termux-wake-lock &>/dev/null; then
    termux-wake-lock
    echo "[UAV] Wake lock активовано"
fi

# Start web config UI in background
"$PYTHON" web_config.py &
WEB_PID=$!
echo "[UAV] Web Config UI запущено: http://localhost:8422 (PID $WEB_PID)"

# Start watcher (foreground — logs go to stdout)
echo "[UAV] Запуск UAV Watcher..."
"$PYTHON" uav_watcher.py

# If watcher exits, kill web UI too
kill $WEB_PID 2>/dev/null
