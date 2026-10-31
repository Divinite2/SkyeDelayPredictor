# Airport Capacity & Delay Risk: Controller Dashboard (front end)

Single-screen Streamlit app for a traffic flow controller at ATL / DFW.
It **only displays** what `predict()` returns (see `contract/schema.json`).

## Run
```bash
pip install -r requirements.txt
streamlit run frontend/app.py            # BACKEND=mock (default)
BACKEND=real streamlit run frontend/app.py   # once backend/api.py exists
python -m pytest -q                      # front-end tests
```
Opens at http://localhost:8501. No internet needed.

## Layout
```
config/config.yaml            shared settings (contract §2)
contract/schema.json          response contract (JSON Schema 2020-12, authoritative)
contract/examples/*.json      six example responses
frontend/app.py               the page
frontend/render.py            pure formatting functions (tested)
frontend/mock_backend.py      stand-in for backend.api.predict
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
