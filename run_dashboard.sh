#!/usr/bin/env bash
# One-click start (Mac/Linux). First run installs packages (needs internet once). Models are pre-built.
set -euo pipefail
cd "$(dirname "$0")"
PY="$(command -v python3.11 || command -v python3)"
[ -d .venv ] || "$PY" -m venv .venv
source .venv/bin/activate
[ -f .venv/.installed ] || { pip install -r requirements.txt && touch .venv/.installed; }
[ -f models/delayband.txt ] || { echo "Models missing - building (about 2 minutes)..."; python run_all.py; }
BACKEND=real streamlit run frontend/app.py
