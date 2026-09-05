@echo off
REM Quick launcher for the Medical Diagnosis Assistant (Streamlit UI)
cd /d "%~dp0"
call venv\Scripts\activate.bat
streamlit run app\streamlit_app.py
