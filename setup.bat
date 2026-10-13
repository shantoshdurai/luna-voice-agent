@echo off
title Jarvis Assistant - 1-Click Setup
color 0A

echo ============================================================
echo   Jarvis AI Assistant - 1-Click Automated Setup
echo ============================================================
echo.

cd /d "%~dp0"

REM 1. Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found on your system PATH!
    echo Please install Python 3.10 or 3.11 from https://www.python.org/
    echo Be sure to check the box: "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM 2. Create Python virtual environment if it does not exist
if not exist "venv\Scripts\activate.bat" (
    echo [*] Creating virtual environment (venv)...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully.
)

REM 3. Activate Virtual Environment
echo [*] Activating virtual environment...
call venv\Scripts\activate.bat

REM 4. Install / Verify Dependencies
echo [*] Installing dependencies from requirements.txt...
set PIP_DEFAULT_TIMEOUT=1000
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt
if errorlevel 1 (
    echo [WARNING] Some dependencies had warnings during installation. Continuing...
)

REM 5. Download Fast Speech Recognition Model (Parakeet-EOU ~112MB)
if not exist "models\parakeet-eou-120m\parakeet-eou-encoder.onnx" (
    echo.
    echo [*] Downloading NVIDIA Parakeet-EOU INT8 speech model (~112 MB)...
    python download_parakeet.py
)

REM 6. Initialize .env from .env.example if missing
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [OK] Initialized .env configuration file.
    )
)

echo.
echo ============================================================
echo   Setup Complete!
echo.
echo   Quick Start:
echo     1. Open the '.env' file in Notepad and add your OPENROUTER_API_KEY
echo        (Get a free key at: https://openrouter.ai/keys)
echo     2. Double-click 'Jarvis.exe' or 'fast_jarvis.bat' to launch!
echo     3. Press Ctrl+Shift+Space or say "Hey Jarvis" to talk.
echo ============================================================
echo.
pause
