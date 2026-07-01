@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   Window OCR - Rebuild and PM2 Restart
echo ========================================
echo.

REM 1) Build server.exe
echo [1/2] Building server-go ...
pushd "%~dp0server-go" || (
    echo [ERROR] Failed to change directory to server-go!
    pause
    exit /b 1
)

go build -o server.exe .
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed with error code %ERRORLEVEL%
    popd
    exit /b %ERRORLEVEL%
)
echo [OK] Build succeeded.
popd
echo.

REM 2) Start with PM2
echo [2/2] Starting with PM2 ...
call pm2 start ecosystem.config.js
if errorlevel 1 (
    echo [ERROR] PM2 restart failed!
    exit /b 1
)

echo.
echo ========================================
echo   Done! Use "pm2 status" to check.
echo ========================================
