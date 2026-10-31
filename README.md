# ATC Weather Risk: 3–12 h delay & capacity forecaster (Autonomous SG 2026 · Airbus Challenge #5)

A traffic flow controller enters an **airport and an hour**. The tool returns delay risk (>15/30/45/60 min), arrival capacity, why, a suggested action, confidence, and simulated example flights. Requests under 3 h or over 12 h ahead are refused.

## Start here
1. `docs/05_Initial_Handover.md`: read first
2. `docs/06_First_Checkpoints.md`: what to deliver, in order
3. Back end: `docs/02_Instructions_Backend.md` · Front end: `docs/03_Instructions_Frontend.md`
4. Shared rules: `docs/04_Data_Contract.md` · Version control: `docs/07_Version_Control.md`

## Setup
```
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# put the provided CSV at data/raw/Flight_Data_With_Weather_Final.csv
pytest -q tests/test_contract_examples.py           # Checkpoint 0 check
```
## Run (once built)
```
python run_all.py                 # stage 1: clean, train, reports
streamlit run frontend/app.py     # stage 2: dashboard at http://localhost:8501
```
## Version control
The project lead owns `main` and the tags. Work on `backend` / `frontend` branches; see `docs/07_Version_Control.md`.
