# 10 · Front-End Instructions for F-3: "Integration-Ready UI"

**For:** front-end developer (Track B) · **Start from:** the lead's latest repo (`AutonomousSGHack`, branch `frontend`, at tag `f1-ui` or later). **Don't use your old `airport-risk-ui` folder.**
**Order changed by the lead:** **F-3 now → J-1 (integration and submit) → F-2 (story and pitch) last.** F-2 goes last so the pitch can use the real numbers and real screenshots.

> **Goal in plain words:** when the back end delivers the real `predict()` (B-3), switching the dashboard over should be **one setting**, nothing should crash, and the demo should need **no typing**. Everything here can be built and tested **now**, without the real back end.

---

## Ground rules (unchanged)
- The front end **displays** and never decides. No thresholds, advice text or colour logic.
- The contract files (`contract/schema.json`, `contract/examples/*.json`) are **authoritative and shared**. Don't edit them on your branch. If you need a change, ask the lead for a joint pull request.
- Work on branch `frontend`. Commit small. Pull `main` whenever the lead announces a merge.

---

## F3.1: Neutral Check button (note F-a)
**Why:** on this screen red means "high risk". A red button next to a red card confuses a busy controller.

**Do:** create `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#1f4e79"     # neutral dark blue; red is reserved for risk level
base = "light"

[server]
headless = true
```
**Pass:** the button is blue in the screenshots. Risk colours (`LEVEL_COLOUR`) are unchanged.

## F3.2: Real responses pass through untouched (note F-b)
**Why:** the mock rewrites timestamps, IDs and text so the demo looks right. That must **never** happen to real model output.

**Do:**
- Keep all re-stamping **inside `frontend/mock_backend.py` only** (it is today, so keep it that way).
- `app.py` must not change the response dict in any way. Treat it as read-only. If you need derived values, compute them into **new** variables in `render.py`.
- **Test** `tests/test_passthrough.py`: build a fake `predict` that returns a fixed dict, run it through the app's call path and the render functions, and assert the original dict is **byte-for-byte unchanged** (compare `json.dumps(..., sort_keys=True)` before and after).

**Pass:** the test is green.

## F3.3: Safe switch to the real back end
**Why:** at J-1 we set `BACKEND=real`. If `backend/api.py` is missing or crashes on import, the controller must see the **error card**, never a Python crash screen.

**Do:** replace the import at the top of `app.py` with a small adapter in `frontend/backend_adapter.py`:
```python
import os
def get_predict():
    mode = os.getenv("BACKEND", "mock").lower()
    if mode == "real":
        try:
            from backend.api import predict
            return predict, "real"
        except Exception as e:                       # import failed: show error card, don't crash
            msg = f"Real back end unavailable: {type(e).__name__}: {e}"
            def predict(airport, target_hour_utc, now_utc):
                return {"schema_version": "1.0", "status": "error",
                        "request": {"airport": airport, "target_hour_utc": target_hour_utc,
                                    "now_utc": now_utc, "lead_time_h": None},
                        "refusal": None, "error": {"code": "BACKEND_IMPORT", "message": msg}}
            return predict, "real-unavailable"
    from frontend.mock_backend import predict
    return predict, "mock"
```
Also wrap **each call** in `try/except`. If `predict()` itself raises (it shouldn't, but be safe), show the error card with the message.

**Show the mode:** in the footer in small grey text, "Back end: mock" or "Back end: real". This lets judges and testers see which one is running. In mock mode add **"(demo data, not a forecast)"**.

**Pass:**
- `BACKEND=real streamlit run frontend/app.py` today (with no `backend/api.py`) opens the page, and **Check** shows the error card "Real back end unavailable…"
- Unit test with `monkeypatch`: a fake `backend.api` that raises on import → error response that passes the schema

> The error code `BACKEND_IMPORT` is a string, which the schema allows for `error.code`. Confirm by running the schema test on the generated response.

## F3.4: Loading and speed
**Why:** the real model is slower than the mock, and the first call loads files.

**Do:**
- Get the predict function once with `@st.cache_resource` (`get_predict()` above). The back end handles its own model caching inside `predict()`.
- Keep the spinner "Calculating…" and the disabled button while waiting (already built, so check it with a fake `predict` that sleeps 2 s).
- Show the **response time** in the footer in small grey text ("answered in 0.4 s"). The back end must be under 1 s (B3.7), and this makes it visible.

**Pass:** with a fake 2 s `predict`, the spinner is visible and the button can't be double-clicked. The footer shows about 2.0 s.

## F3.5: Demo presets (no typing in the pitch)
**Why:** the 3-minute pitch can't afford typing dates. The back end will choose real demo cases from the test period (B3.8).

**Agreed file (new, shared):** `reports/demo_cases.json`. **The back end owns the content. You build the reader now against this placeholder:**
```json
{
  "version": "placeholder",
  "cases": [
    {"id": "storm", "label": "Storm hour, flagged 6 h ahead", "airport": "ATL",
     "now_utc": "2025-06-14T16:00:00Z", "target_hour_utc": "2025-06-14T22:00:00Z"},
    {"id": "calm", "label": "Calm hour", "airport": "DFW",
     "now_utc": "2025-05-06T11:00:00Z", "target_hour_utc": "2025-05-06T15:00:00Z"},
    {"id": "miss", "label": "Known failure case", "airport": "ATL",
     "now_utc": "2025-07-02T12:00:00Z", "target_hour_utc": "2025-07-02T20:00:00Z"},
    {"id": "too_soon", "label": "Refused: only 2 h ahead", "airport": "ATL",
     "now_utc": "2025-06-14T16:00:00Z", "target_hour_utc": "2025-06-14T18:00:00Z"},
    {"id": "too_far", "label": "Refused: 13 h ahead", "airport": "ATL",
     "now_utc": "2025-06-14T16:00:00Z", "target_hour_utc": "2025-06-15T05:00:00Z"}
  ]
}
```
**Do:**
- A small **"Demo cases"** select box above the input bar: "— choose —" plus each `label`. Choosing one fills airport, now and target (converted to local for display) and runs **Check** automatically.
- If the file is missing or `version` is `"placeholder"`, still work, but show "(placeholder demo cases)" in grey.
- The normal inputs still work. Presets are a shortcut, not a replacement.
- Times in the file are **UTC**, following the contract. Convert them with the existing `zoneinfo` helpers, not new code.

**Pass:** each of the 5 presets produces the expected screen on the mock (2 OK, 1 OK for "miss", 2 refused). Add a test that every case in the file has a valid airport, whole-hour UTC times, and `now < target`.

> Tell the back end through the lead: `reports/demo_cases.json` in this format is part of B3.8. (The lead will add it to the back end's checklist.)

## F3.6: Housekeeping
- Airport list read from `config.airports` (no hard-coded ATL/DFW).
- Remove the mock-only codes `ERR` and `BAD` from **real** mode: in real mode, no special codes.
- `docs/FRONTEND_README.md`: update the run commands (`BACKEND=mock|real`, `DEMO_DATE`, the presets file).
- All tests green: `python -m pytest -q`. Expect the existing 54 plus your new ones.

---

## F-3 deliverables and pass conditions (checklist for the report)
| # | Deliverable | Pass |
|---|---|---|
| F3.1 | `.streamlit/config.toml`, neutral button | Screenshot: blue button, risk colours unchanged |
| F3.2 | Pass-through test | Real-mode response unchanged byte-for-byte |
| F3.3 | `backend_adapter.py`, mode shown in footer | `BACKEND=real` without a back end → error card, no crash, plus a test |
| F3.4 | Cached adapter, spinner, response time | Fake 2 s back end: spinner shown, no double-click, time shown |
| F3.5 | Demo presets from `reports/demo_cases.json` | 5 presets render correctly on the mock, plus a file test |
| F3.6 | Housekeeping | README updated, all tests pass |
| — | Screenshots | `ui_f3_button.png`, `ui_f3_real_unavailable.png`, `ui_f3_presets.png` |

**Traps:** T6 (time zones on presets), T18 and T19 (SIMULATED unchanged), T20 (no decision logic in the UI), T22 (presets use **test-period** dates only).

**Report:** use the template at the bottom of `06_First_Checkpoints.md`. Upload a zip of branch `frontend` together with the report.

---

## After F-3
1. **J-1 (with the back end, after B-3):** set `BACKEND=real`, run the presets, take the `ui_real_*` screenshots, test on a second laptop, record the backup video, then **submit v1**.
2. **F-2 (last, during the freeze):** the story and pitch, using the **real** B-2 numbers and J-1 screenshots. Instructions are unchanged in `08_Next_Checkpoints.md`.
