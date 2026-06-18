@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Update yt-dlp

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Environment not set up yet. Run start.bat first.
    pause
    exit /b 1
)

echo Updating yt-dlp (key to beating YouTube blocks; run this when playback breaks)...
echo.
venv\Scripts\python.exe -m pip install -U yt-dlp
echo.
echo Done.
pause
