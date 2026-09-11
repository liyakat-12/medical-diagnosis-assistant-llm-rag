@echo off
REM Start FastAPI API, then the Vite website
cd /d "%~dp0"
start "MediAssist API" cmd /k "call venv\Scripts\activate.bat && set PYTHONPATH=%cd%\backend && echo API http://localhost:8000 && uvicorn app.main:app --reload --port 8000"
timeout /t 4 /nobreak >nul
cd frontend
if not exist node_modules call npm install
echo Open http://localhost:5173
npm run dev
