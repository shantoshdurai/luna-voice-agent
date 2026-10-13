@echo off
cd /d "%~dp0"

if not exist "venv\Scripts\pythonw.exe" (
    echo [Notice] First-time setup detected. Running setup.bat...
    call "%~dp0setup.bat"
)

if "%1"=="--console" (
    title Jarvis AI Fast Agent (Console Debug Mode)
    color 0B
    if exist "venv\Scripts\python.exe" (
        "venv\Scripts\python.exe" fast_agent.py --console
    ) else (
        python fast_agent.py --console
    )
    pause
    exit /b 0
)

if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" fast_agent.py %*
) else (
    start "" pythonw fast_agent.py %*
)
exit /b 0
