#!/usr/bin/env bash
# Argus Demo Launcher
# Spawns Argus CLI with rich incident simulation mode on demo-project

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
ARGUS_BIN="$PROJECT_ROOT/backend/venv/bin/argus"

echo "=========================================================="
echo " 🌐 Argus DevOps Health Map — Incident Simulation Demo"
echo "=========================================================="
echo " Target Project: $SCRIPT_DIR"
echo " Options:"
echo "   1) Launch Rich Incident Simulation Mode (Default)"
echo "   2) Launch Healthy Pipeline Map Mode"
echo "=========================================================="

MODE="${1:---simulate}"

if [ "$MODE" == "--healthy" ] || [ "$1" == "2" ]; then
    echo "🟢 Launching in Normal Health Map Mode..."
    exec "$ARGUS_BIN" start "$SCRIPT_DIR" --no-browser
else
    echo "🔥 Launching in Active Incident Simulation Mode..."
    exec "$ARGUS_BIN" start "$SCRIPT_DIR" --simulate-incident --no-browser
fi
