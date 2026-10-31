@echo off
REM Fresh setup + build + tests + smoke test + dashboard (docs/11 1-4). Needs Python 3.11 (py -3.11).
REM Needs the CSV at data\raw\Flight_Data_With_Weather_Final.csv
cd /d "%~dp0\.."
if not exist data\raw\Flight_Data_With_Weather_Final.csv (echo Missing data\raw\Flight_Data_With_Weather_Final.csv & exit /b 1)
if not exist .venv (py -3.11 -m venv .venv || exit /b 1)
call .venv\Scripts\activate.bat || exit /b 1
python --version
pip install -r requirements.txt || exit /b 1
python run_all.py || exit /b 1
python -m pytest -q || exit /b 1
python scripts\smoke_real.py || exit /b 1
set BACKEND=real
streamlit run frontend\app.py
