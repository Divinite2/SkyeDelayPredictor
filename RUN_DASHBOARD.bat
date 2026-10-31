@echo off
REM One-click start (Windows). First run installs packages (needs internet once). Models are pre-built.
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3.11) || (set PY=python)
if not exist .venv (%PY% -m venv .venv || (echo Python 3.11 not found. See HOW_TO_RUN_AND_TEST.md & pause & exit /b 1))
call .venv\Scripts\activate.bat
if not exist .venv\.installed (pip install -r requirements.txt && echo ok> .venv\.installed)
if not exist models\delayband.txt (echo Models missing - building, about 2 minutes... & python run_all.py)
set BACKEND=real
streamlit run frontend\app.py
pause
