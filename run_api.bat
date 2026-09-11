@echo off
REM FastAPI RAG API only. Website is run_web.bat on port 3000.
cd /d "%~dp0"
call venv\Scripts\activate.bat
set PYTHONPATH=%cd%\backend
echo API http://localhost:8000/docs
uvicorn src.api.main:app --reload --port 8000
