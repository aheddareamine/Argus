@echo off
setlocal
echo ==========================================================
echo  🌐 Argus DevOps Health Map - Initialization ^& Setup
echo ==========================================================

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set VENV_DIR=%PROJECT_ROOT%\backend\venv
set ARGUS_BIN=%VENV_DIR%\Scripts\argus.exe

:: 1. Setup Python Virtual Environment and Backend Dependencies
if not exist "%ARGUS_BIN%" (
    echo 📦 Initializing Python environment for the first time...
    cd /d "%PROJECT_ROOT%"
    
    python -m venv backend\venv
    call "%VENV_DIR%\Scripts\activate.bat"
    
    echo ⬇️  Installing backend requirements...
    pip install -r backend\requirements.txt
    
    echo ⬇️  Installing argus-cli...
    pip install -e argus-cli
    
    echo ✅ Python setup complete!
) else (
    call "%VENV_DIR%\Scripts\activate.bat"
)

:: 2. Build Frontend if missing
if not exist "%PROJECT_ROOT%\final_front_end\out" (
    echo 📦 Building the Next.js frontend UI...
    cd /d "%PROJECT_ROOT%\final_front_end"
    call npx pnpm install
    call npx pnpm run build
    echo ✅ Frontend build complete!
)

echo.
echo ==========================================================
echo  🌐 Argus DevOps Health Map - Incident Simulation Demo
echo ==========================================================

cd /d "%PROJECT_ROOT%"
echo 🔥 Launching in Active Incident Simulation Mode...
"%ARGUS_BIN%" start "%SCRIPT_DIR%" --simulate-incident --no-browser
