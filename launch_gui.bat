@echo off
REM Launch the gems_t4 GUI from the project's virtual environment.
REM This runs the LIVE source, so it always reflects the current code
REM (no PyInstaller rebuild needed) - the whole point after a git pull.
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    REM pythonw = no extra console window for the GUI.
    start "" ".venv\Scripts\pythonw.exe" -m gems_t4 gui %*
) else if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" -m gems_t4 gui %*
) else (
    echo Error: .venv not found next to this script.
    echo Create it and install the app, then run this again:
    echo     python -m venv .venv
    echo     .venv\Scripts\pip install -e ".[gui]"
    pause
)
