@echo off
chcp 65001 >nul
echo ========================================
echo   Window OCR - Rebuild & PM2 Restart
echo ========================================
echo.

REM 1) Stop & delete existing PM2 process (ignore errors)
echo [1/3] Stopping existing PM2 process ...
pm2 delete window-ocr-server 2>nul

REM 2) Rebuild server.exe
echo [2/3] Building server-go ...
cd /d "%~dp0server-go"
go build -o server.exe .
if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    pause
    exit /b %ERRORLEVEL%
)
echo Build succeeded.
cd /d "%~dp0"

REM 3) Start with PM2
echo [3/3] Starting with PM2 ...
pm2 start ecosystem.config.js

echo.
echo Done! Use "pm2 status" to check.
pause