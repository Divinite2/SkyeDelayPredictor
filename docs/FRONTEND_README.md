# Airport Capacity & Delay Risk: Controller Dashboard (front end)

Single-screen Streamlit app for a traffic flow controller at ATL / DFW.
It **only displays** what `predict()` returns (see `contract/schema.json`).

## Run
```bash
pip install -r requirements.txt
streamlit run frontend/app.py            # BACKEND=mock (default)
BACKEND=real streamlit run frontend/app.py   # once backend/api.py exists
python -m pytest -q                      # front-end tests (48)
```
Run from the project root so `.streamlit/config.toml` (neutral theme) is picked up.

## Back end switch
- `BACKEND=mock` (default): `frontend/mock_backend.py`, which re-stamps example times to the request.
- `BACKEND=real`: `backend.api.predict`, loaded once (`@st.cache_resource`). Responses are shown **untouched**.
  If the import fails, the page shows the error card instead of crashing.

## Demo cases picker
Filled from `reports/demo_cases.md` (back end, B3.8): a markdown table with `airport`, `now…` and
`target…` columns (UTC, `Z`). Three refusal presets (2 h, 13 h, unknown airport) are added from the
first case. In mock mode, if that file is missing, `tests/fixtures/demo_cases_sample.md` is used.
Opens at http://localhost:8501. No internet needed.

## Layout
```
config/config.yaml            shared settings (contract §2)
contract/schema.json          response contract (JSON Schema 2020-12, authoritative)
contract/examples/*.json      six example responses
frontend/app.py               the page
frontend/render.py            pure formatting functions (tested)
frontend/mock_backend.py      stand-in for backend.api.predict
frontend/backend_adapter.py   mock/real switch, safe import, pass-through
frontend/demo_cases.py        demo preset parser
.streamlit/config.toml        neutral theme (Check button not red)
tests/                        schema + render tests, broken fixture
```

## Demo / test mode (mock only)
Tick **Test mode** to type any airport and target hour:
| Input | Shows |
|---|---|
| ATL/DFW, even target hour (UTC) | RED card |
| ATL/DFW, odd target hour (UTC) | GREEN card |
| target < 3 h or > 12 h ahead | refused card |
| `ORD` (any unknown code) | "Airport not in data" |
| `ERR` | error card |
| `BAD` | broken response (P>45 > P>30) → error card (safety check) |
| a "now" date before Apr 2025 | yellow "not a fair test" banner |

Optional: `DEMO_DATE=2025-07-10 streamlit run frontend/app.py` sets the default date.
