@echo off
REM Start FastAPI API, then the Express website
cd /d "%~dp0"
start "MediAssist API" cmd /k "call venv\Scripts\activate.bat && set PYTHONPATH=%cd%\backend && echo API http://localhost:8000 && uvicorn src.api.main:app --reload --port 8000"
timeout /t 4 /nobreak >nul
cd frontend
if not exist node_modules call npm install
call npm run build:css
echo Open http://localhost:3000  (demo: demo@clinic.local / demo123)
node server.js
