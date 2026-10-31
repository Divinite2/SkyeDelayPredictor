# 03 · Front-End Instructions: The Controller's Dashboard

**For:** Track B (dashboard developer)
**You must also read:** `04_Data_Contract.md` (binding), `05_Initial_Handover.md` §5 (trap register)
**Scope:** everything here is **P0** (must have) except the two **Optional** items at the end, which are only done after v1 is submitted.

> **What the front end does, in plain words:** a busy controller enters **an airport and an hour**, presses one button, and within about 10 seconds of reading knows: *how risky that hour is, why, what to consider doing, how sure the tool is, and which flights are affected.* The front end **only displays** what the back end returns. It never calculates risk, picks colours or writes advice itself.

---

## 0. Ground rules
1. **Start immediately on mock data.** Don't wait for the model. `frontend/mock_backend.py` returns the example files in `contract/examples/`.
2. **One screen.** No tabs, no charts to explore, no chatbot. The controller is busy.
3. **Display, don't decide.** The colour, recommendation, confidence and refusals all come from the back end (contract §1).
4. **Every number shown must trace to a field in the response.** If a field is `null`, show "—" or leave the line out. **Never show 0 for missing.**

> 🔧 **Stack:** Streamlit (≥ 1.30). Plain Streamlit components plus a little HTML/CSS for the bars. Plotly isn't needed for P0. Switch with the `BACKEND=mock|real` environment variable: `from backend.api import predict` or `from frontend.mock_backend import predict`.

**Files**
```
frontend/app.py            # the single page
frontend/mock_backend.py   # same signature as backend.api.predict
frontend/render.py         # pure functions: response dict -> display pieces (unit-testable)
tests/test_mock_matches_schema.py
tests/test_render.py
```

---

## Step B1 (P0): Skeleton on mock data
- `mock_backend.predict(airport, target_hour_utc, now_utc)` returns:
  - `example_refused_short.json` / `example_refused_long.json` if the lead time is outside 3–12
  - `example_refused_airport.json` for an unknown airport
  - `example_error.json` if the airport is `"ERR"` (for testing)
  - otherwise `example_ok_red.json` or `example_ok_green.json`, alternating by hour
- On load, **validate every response against `contract/schema.json`**. If validation fails, show the error state (see B2).

## Step B2 (P0): The page

### Input bar (top, one row)
| Field | Control | Rules |
|---|---|---|
| Airport | Select box: ATL, DFW | Accepts IATA. Shows the ICAO code beside it (from config) |
| "Now" (forecast time) | Date + hour picker | **Whole hours only.** Defaults to a demo date in the **test period** (Apr–Jul 2025) |
| Target hour | Hour picker, offered as **now + 3 … now + 12 h** | Pre-filtering is only for convenience. The back end still enforces the rule. Also allow free entry so the refusal can be demonstrated. |
| Button | **Check** | One click → one `predict()` call |

All times are **entered and shown in the airport's local time with the zone label** (e.g. "18:00 EDT"), and **converted to UTC before calling `predict()`** using `config.airports.<code>.tz` with `zoneinfo`. Under the inputs, show the UTC equivalent in small grey text so judges can verify it.

### Result card (status = "ok"), in this order, top to bottom
```
┌──────────────────────────────────────────────────────────────────────┐
│ ATL (KATL) · 18:00–19:00 EDT · forecast made 6 h ahead     🔴 RED     │
├──────────────────────────────────────────────────────────────────────┤
│ DEPARTURE DELAY RISK                                                  │
│  > 15 min  ██████████████░░░░░░  70%                                  │
│  > 30 min  ██████████░░░░░░░░░░  50%                                  │
│  > 45 min  ████████░░░░░░░░░░░░  38%   ◀ severe                       │
│  > 60 min  ██████░░░░░░░░░░░░░░  28%                                  │
│                                                                       │
│ ARRIVAL CAPACITY  70% of scheduled arrivals on time (likely 60–80%)  │
│                                                                       │
│ WHY   • Thunderstorm reported (11:00 EDT)                             │
│       • Strong wind 30 km/h, crosswind worst case (11:00 EDT)         │
│       • Evening peak hour                                             │
│ DO    Consider a pre-emptive arrival-rate reduction or ground delay   │
│       programme for this hour.      (rule RED-1: P>45 ≥ 30%)          │
│ CONFIDENCE  MEDIUM · lead time 6 h · last weather reading 1 h old     │
├──────────────────────────────────────────────────────────────────────┤
│ EXAMPLE FLIGHTS IN THIS HOUR (SIMULATED)  >15   >30   >45   >60       │
│ SIM-01  DL  ATL→LGA  18:05  SIMULATED     70%   50%   38%   28%       │
│ SIM-02  WN  ATL→BWI  18:20  SIMULATED     70%   50%   38%   28%       │
│ SIM-03  AA  ATL→DFW  18:35  SIMULATED     70%   50%   38%   28%       │
│ ⓘ Simulated flights. Each shows the risk for the whole hour.        │
└──────────────────────────────────────────────────────────────────────┘
```

**Display rules**
| Element | Source field | Rule |
|---|---|---|
| Header colour and word | `risk_level` | **Colour plus the word** (RED/AMBER/GREEN). Never colour alone, for colour-blind users and printed slides. |
| Risk bars | `hour_delay_risk.p_gt*` | Whole %, standard rounding. The > 45 row is **bold and marked "severe"** (brief requirement). Thresholds and labels come from `config.delay_thresholds_min`, not hard-coded. |
| Monotonic check | same | If `p_gt15 ≥ p_gt30 ≥ p_gt45 ≥ p_gt60` fails, show the **error state**. Don't show inconsistent numbers. |
| Capacity | `capacity.index`, `index_low`, `index_high` | "X% of scheduled arrivals on time (likely L–H%)". If `aar_est` isn't null, also show "≈ N arrivals/h (L–H)". Otherwise don't show arrivals/h. Show `aar_note` as a hover tooltip. |
| WHY | `drivers[]` | Up to 3 bullets: label, value, and observation time in **local time**. No time shown when `observed_at_utc` is null. |
| DO | `recommendation.text` + `rule_id` + `triggered_by` | Shown **verbatim**. Rule ID in small grey text (traceability). |
| Confidence | `confidence.level` + `reasons` | Level in bold, reasons joined by " · " |
| Flight table | `flights[]` | Title "Example flights in this hour (simulated)". Rows in the order received, *italic grey*, each with a visible **SIMULATED** tag. **Always** show the ⓘ note: "Simulated flights to illustrate a full schedule. Each shows the risk for the whole hour, not an individual flight prediction." Empty list → hide the table. |
| Period warning | `data_period` | If it isn't `TEST`, show a yellow banner: "This date is in the model's TRAINING/VALIDATION period, so it isn't a fair test. Use Apr–Jul 2025 for honest demos." |
| Footer | `model_version`, `generated_at_utc` | Small grey text |

### Refused card (status = "refused")
- A neutral grey card. **No numbers, no bars, no colours.**
- Title by code: `LEAD_TOO_SHORT` → "Too soon to forecast". `LEAD_TOO_LONG` → "Too far ahead to forecast". `UNKNOWN_AIRPORT` → "Airport not in data". `NOT_ON_THE_HOUR`, `OUT_OF_DATA_RANGE`, `NO_RECENT_WEATHER` → "Cannot forecast this request".
- Body: `refusal.message` **verbatim**.
- This is a **feature**, not a failure. The pitch shows it deliberately.

### Error state (status = "error", or the schema or monotonic check fails)
- A red-bordered box: "The forecast could not be produced. Do not rely on this tool for this request." plus `error.message` in small text. **No numbers.**

### Loading
- A spinner with the text "Calculating…". Disable the button while waiting.

## Step INT (P0): Switch to the real back end
- Set `BACKEND=real`. Run the five Gate 3 requests (`01_Workflow.md` §5) and save a **screenshot of each** in `reports/figures/ui_*.png` for Track C.

---

## Step RUN (P0): How the app is run and demoed
**In plain words:** this is a Python web app that opens in a browser on the team laptop. It needs **no internet**, so venue Wi-Fi can't break the demo.

| Item | Rule |
|---|---|
| Two stages | **Stage 1 (once):** `python run_all.py` cleans the data, trains the models and saves files. **Stage 2 (live):** `streamlit run frontend/app.py` opens the dashboard at `http://localhost:8501`. |
| No separate server | The page imports `predict()` directly. There's no HTTP API, no ports to manage and no network calls. |
| Speed | Load the model and weather timeline **once** with `@st.cache_resource`, so each **Check** answers instantly |
| Fresh-clone test | `pip install -r requirements.txt` → `python run_all.py` → `streamlit run frontend/app.py` must work on a second laptop (part of Gate 3) |
| Demo backup | Before the pitch, save the `ui_real_*.png` screenshots **and** a short screen recording of the demo flow, in case the laptop fails |
| Hosted link | **Only if the submission requires a URL**, and only after v1 is submitted: push to GitHub and deploy free on Streamlit Community Cloud |

> 🔧 Add `streamlit` to the shared `requirements.txt` with a pinned version. Commit the trained model files **or** run `run_all.py` in the deploy step. Choose one and write it in the README.

## Optional (only after v1 is submitted and frozen)
| ID | Task |
|---|---|
| X1 | **Accept / Dismiss** buttons under the DO line. Append `{time, airport, target_hour, rule_id, choice}` to `reports/decision_log.csv`. Shows the human stays in control. |
| X2 | A collapsed "Details for reviewers" expander: lead-time accuracy table and data limitations, read from `reports/metrics.md`. Collapsed by default. |

---

## Front-end tests (P0)
- `test_mock_matches_schema.py`: every example file validates.
- `test_render.py`, pure functions:
  - 0.384 → "38%"
  - null capacity → line hidden
  - monotonic violation → error state
  - UTC ↔ local conversion correct on a **daylight-saving change date** (2024-03-10 and 2024-11-03 for both ATL and DFW)
  - SIMULATED rows always carry the tag

## Front-end checklist before each submission
- [ ] Works with `BACKEND=mock` and `BACKEND=real`
- [ ] Refused and error states show no numbers
- [ ] All displayed times are local with a zone label. UTC is visible in small text.
- [ ] Colour is never the only signal
- [ ] Every SIMULATED row is labelled
- [ ] No number on screen is calculated by the front end other than formatting
- [ ] Five Gate 3 screenshots saved
