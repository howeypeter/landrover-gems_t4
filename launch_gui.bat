@echo off
REM Launch gems_t4 GUI from the dist folder
cd /d "%~dp0"
if exist "dist\gems_t4\gems_t4_gui.exe" (
    start "" "dist\gems_t4\gems_t4_gui.exe"
) else (
    echo Error: gems_t4_gui.exe not found. Did you run the PyInstaller build?
    echo.
    echo To build: cd packaging ^&^& python -m PyInstaller gems_t4.spec --noconfirm
    pause
)
