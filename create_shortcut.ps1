# Create a Windows shortcut for the gems_t4 GUI
# Run this script in PowerShell from the project root:
#   .\create_shortcut.ps1

$projectRoot = (Get-Location).Path
$exePath = Join-Path $projectRoot "dist\gems_t4\gems_t4_gui.exe"
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "gems_t4 GUI.lnk"

if (-not (Test-Path $exePath)) {
    Write-Host "Error: $exePath not found. Did you run the PyInstaller build?" -ForegroundColor Red
    Write-Host ""
    Write-Host "To build: cd packaging; python -m PyInstaller gems_t4.spec --noconfirm"
    exit 1
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exePath
$shortcut.WorkingDirectory = $projectRoot
$shortcut.WindowStyle = 1  # Normal window
$shortcut.Description = "TestBook T4 — GEMS ECU Diagnostic Tool"
$shortcut.Save()

Write-Host "Shortcut created: $shortcutPath" -ForegroundColor Green
Write-Host "You can now launch the GUI from the desktop."
