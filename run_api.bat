@echo off
REM FastAPI backend on http://localhost:8000
cd /d "%~dp0"
call venv\Scripts\activate.bat
set PYTHONPATH=%cd%\backend
echo API http://localhost:8000/docs
uvicorn app.main:app --reload --reload-dir backend --port 8000
