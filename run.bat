@echo off
cd /d "%~dp0"
if not exist venv python -m venv venv
venv\Scripts\python -m pip install -q -r requirements.txt
start "" cmd /c "timeout /t 3 >nul & start http://127.0.0.1:8000"
venv\Scripts\python -m uvicorn main:app --reload
pause