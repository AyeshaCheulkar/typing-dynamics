@echo off
title Writing Analytics Prototype - Online Host
echo ============================================================
echo   Starting Writing Analytics Prototype Platform
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/2] Starting Flask backend on http://127.0.0.1:5001 ...
start "Prototype Flask Server" /min .\venv\Scripts\python prototype_platform\app.py

timeout /t 3 /nobreak >nul

echo [2/2] Launching Cloudflare Public Tunnel...
echo ------------------------------------------------------------
echo Look below for your public URL (https://xxxx.trycloudflare.com)
echo ------------------------------------------------------------
cloudflared tunnel --url http://127.0.0.1:5001

pause
