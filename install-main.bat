@echo off
echo === Window OCR - Main App Install ===

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating venv and installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements-main.txt

echo.
echo Done. Run with: venv\Scripts\python main.py
pause
