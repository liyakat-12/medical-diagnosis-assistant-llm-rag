@echo off
REM Quick launcher for the FastAPI backend
cd /d "%~dp0"
call venv\Scripts\activate.bat
uvicorn src.api.main:app --reload --port 8000
