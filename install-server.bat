@echo off
echo === Window OCR - Server Install ===

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating venv and installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements-server.txt

echo.
echo Done. Run with: venv\Scripts\pythonw ocr_server.py
echo Or use PM2:    pm2 start ecosystem.config.js
pause
