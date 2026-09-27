#!/usr/bin/env bash
# Argus Demo Launcher
# Automatically installs dependencies and launches the demo

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
VENV_DIR="$PROJECT_ROOT/backend/venv"

# Handle Windows (Git Bash) vs Linux/Mac paths
if [ -d "$VENV_DIR/Scripts" ]; then
    VENV_BIN="$VENV_DIR/Scripts"
else
    VENV_BIN="$VENV_DIR/bin"
fi
ARGUS_BIN="$VENV_BIN/argus"

echo "=========================================================="
echo " 🌐 Argus DevOps Health Map — Initialization & Setup"
echo "=========================================================="

# 1. Setup Python Virtual Environment and Backend Dependencies
if [ ! -f "$ARGUS_BIN" ]; then
    echo "📦 Initializing Python environment for the first time..."
    cd "$PROJECT_ROOT"
    
    # Use python3 if available, else python (common on Windows)
    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    else
        PYTHON_CMD="python"
    fi
    
    $PYTHON_CMD -m venv backend/venv
    
    # Re-evaluate VENV_BIN in case it just got created
    if [ -d "$VENV_DIR/Scripts" ]; then
        VENV_BIN="$VENV_DIR/Scripts"
    else
        VENV_BIN="$VENV_DIR/bin"
    fi
    ARGUS_BIN="$VENV_BIN/argus"
    
    source "$VENV_BIN/activate"
    echo "⬇️  Installing backend requirements..."
    pip install -r backend/requirements.txt
    echo "⬇️  Installing argus-cli..."
    pip install -e argus-cli
    echo "✅ Python setup complete!"
else
    source "$VENV_BIN/activate"
fi

# 2. Build Frontend if missing
if [ ! -d "$PROJECT_ROOT/final_front_end/out" ]; then
    echo "📦 Building the Next.js frontend UI..."
    cd "$PROJECT_ROOT/final_front_end"
    npx pnpm install
    npx pnpm run build
    echo "✅ Frontend build complete!"
fi

echo ""
echo "=========================================================="
echo " 🌐 Argus DevOps Health Map — Incident Simulation Demo"
echo "=========================================================="
echo " Target Project: $SCRIPT_DIR"
echo " Options:"
echo "   1) Launch Rich Incident Simulation Mode (Default)"
echo "   2) Launch Healthy Pipeline Map Mode"
echo "=========================================================="

MODE="${1:---simulate}"

cd "$PROJECT_ROOT"

if [ "$MODE" == "--healthy" ] || [ "$1" == "2" ]; then
    echo "🟢 Launching in Normal Health Map Mode..."
    exec "$ARGUS_BIN" start "$SCRIPT_DIR" --no-browser
else
    echo "🔥 Launching in Active Incident Simulation Mode..."
    exec "$ARGUS_BIN" start "$SCRIPT_DIR" --simulate-incident --no-browser
fi
