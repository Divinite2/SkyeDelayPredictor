#!/usr/bin/env bash
# Fresh setup + build + tests + smoke test + dashboard (docs/11 §1-§4, docs/14 §1). Run from anywhere.
# Needs Python 3.11 and the CSV at data/raw/Flight_Data_With_Weather_Final.csv.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3.11}"
"$PY" --version
[ -f data/raw/Flight_Data_With_Weather_Final.csv ] || { echo "Missing data/raw/Flight_Data_With_Weather_Final.csv"; exit 1; }
[ -d .venv ] || "$PY" -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_all.py
python -m pytest -q
python scripts/smoke_real.py
BACKEND=real streamlit run frontend/app.py
