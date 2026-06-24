@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   Window OCR - Rebuild and PM2 Restart
echo ========================================
echo.

REM 1) Stop and delete existing PM2 process (ignore errors)
echo [1/3] Stopping existing PM2 process ...
call pm2 delete window-ocr-server 2>nul
if errorlevel 1 (
    echo [WARN] No process named window-ocr-server found, continue...
) else (
    echo [OK] Process deleted.
)
echo.

REM 2) Build server.exe
echo [2/3] Building server-go ...
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

REM 3) Start with PM2
echo [3/3] Starting with PM2 ...
call pm2 start ecosystem.config.js
if errorlevel 1 (
    echo [ERROR] PM2 start failed!
    exit /b 1
)

echo.
echo ========================================
echo   Done! Use "pm2 status" to check.
echo ========================================
