@echo off
chcp 65001 >nul
echo ========================================
echo   Window OCR - Manual Test Launcher
echo ========================================
echo.

cd /d "%~dp0server-go"

echo [1/3] Building server-go ...
go build -o server.exe .
if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    pause
    exit /b %ERRORLEVEL%
)
echo Build succeeded.

echo.
echo [2/3] Starting server on http://localhost:8618 ...
start "" server.exe

echo.
echo [3/3] Opening browser ...
timeout /t 2 /nobreak >nul
start "" http://localhost:8618

echo.
echo Server is running. Close this window when done.
pause