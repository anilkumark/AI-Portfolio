@echo off
REM Start WishCall on Windows
cd /d "%~dp0"
if not exist .venv (
  py -3 -m venv .venv 2>nul || python -m venv .venv
  if errorlevel 1 (
    echo Python 3.10 or newer is needed: https://www.python.org/downloads/
    pause
    exit /b 1
  )
)
call .venv\Scripts\activate.bat
python -m pip install -q --upgrade pip
pip install -q -r requirements.txt
echo.
echo   WishCall is running. Open http://localhost:8000 in your browser.
echo   Close this window to stop it.
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
