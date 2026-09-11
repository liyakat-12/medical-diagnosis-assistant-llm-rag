@echo off
REM React + Vite frontend on http://localhost:5173 (needs API on port 8000)
cd /d "%~dp0frontend"
if not exist node_modules call npm install
echo Open http://localhost:5173
npm run dev
