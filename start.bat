@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Discord Music Bot

echo ============================================
echo    Discord Music Bot - launcher
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and tick "Add to PATH".
    echo         https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo [SETUP] First run: creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
    echo [SETUP] Installing packages, this can take a few minutes...
    venv\Scripts\python.exe -m pip install --upgrade pip
    venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Package install failed. Check your internet connection.
        pause
        exit /b 1
    )
    echo [SETUP] Done.
    echo.
)

if not exist ".env" (
    echo [ERROR] .env not found. Copy .env.example to .env and add your token.
    pause
    exit /b 1
)

findstr /C:"PASTE_YOUR_BOT_TOKEN_HERE" .env >nul
if not errorlevel 1 (
    echo [ERROR] DISCORD_TOKEN in .env is not filled in yet.
    echo         Open .env in Notepad and paste your token after DISCORD_TOKEN=
    echo.
    pause
    exit /b 1
)

echo [RUN] Bot starting. Close this window or press Ctrl+C to stop.
echo --------------------------------------------
venv\Scripts\python.exe bot.py

echo --------------------------------------------
echo Bot stopped.
pause
