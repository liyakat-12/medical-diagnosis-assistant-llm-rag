@echo off
REM Express + Tailwind website (needs the FastAPI API on port 8000)
cd /d "%~dp0frontend"
if not exist node_modules call npm install
call npm run build:css
echo Open http://localhost:3000  (demo: demo@clinic.local / demo123)
node server.js
