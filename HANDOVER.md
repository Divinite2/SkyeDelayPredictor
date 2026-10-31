# HANDOVER: Airport Delay & Capacity Forecaster (Autonomous SG 2026, Airbus Challenge #5)

**Who this is for:** a new team that has never seen this project. Read this file first. It explains what the product does, how it's built, how to run it, how to change it safely, and what's unfinished.
**Version at handover:** v1.1 (git tag `v1.1-handover`) · data contract v1.1 · 134 automated tests passing.

---

## 1. The product in one minute
A **traffic flow controller** at Atlanta (ATL) or Dallas Fort Worth (DFW) picks an **airport**, the **current time ("now")** and a **target hour 3–12 hours ahead**, then presses **Check**. One card answers:

| Section | Meaning |
|---|---|
| Colour badge **RED / AMBER / GREEN** | How risky the hour is for severe departure delays (> 45 min or cancelled) |
| **LIKELY DELAY** | *Middle estimate* (median delay band, e.g. "under 15 min") and *Bad case, 1-in-4 chance* (e.g. "more than 45 min (31%)") |
| **DEPARTURE DELAY RISK** | P(delay > 15 / 30 / 45 / 60 min). The > 45 row is the brief's "severe" line. |
| **ARRIVAL CAPACITY** | Share of scheduled arrivals expected on time (our substitute for the Arrival Acceptance Rate, which isn't in the data) |
| **WHY** | Top 3 factors, each with the time it was observed (always before "now") |
| **DO** | A fixed-rule suggestion. **The controller decides.** |
| **CONFIDENCE** | HIGH / MEDIUM / LOW, with reasons |

Requests under 3 h or over 12 h ahead, unknown airports, and similar cases are **refused** with an explanation. Under 3 h a controller already sees the trend; over 12 h weather is too unreliable.

**What it is not:** it doesn't predict individual flights, doesn't use live data (it replays 2023–2025 history), and doesn't replace the controller.

---

## 2. Run it

### Fastest (the models are already built in the package)
- **Windows:** double-click `RUN_DASHBOARD.bat`
- **Mac/Linux:** `./run_dashboard.sh`

The first start installs Python packages (internet needed once). The browser then opens `http://localhost:8501`. **Python 3.11 is required.** See `HOW_TO_RUN_AND_TEST.md` for a click-by-click test.

### Developer setup
```bash
python3.11 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_all.py                 # rebuild everything from the raw CSV (~2 min)
python -m pytest -q               # expect 134 passed
python scripts/smoke_real.py      # real predict() on the demo cases + refusal cases
BACKEND=real streamlit run frontend/app.py      # Windows: set BACKEND=real & streamlit run frontend\app.py
```
`BACKEND=mock` (the default) runs the screen on fixed example answers. Use it for UI work without the model.

---

## 3. Architecture

```
data/raw/Flight_Data_With_Weather_Final.csv   (provided; never edited)
        │
        ▼  python run_all.py
┌─────────────────────────── BACK END (backend/) ───────────────────────────┐
│ load.py → timezone_fix.py → weather_timeline.py → clean_flights.py → validate.py │  DATA stage (checks V1–V10)
│ features.py (leakage-safe, hour-level) → baselines.py → train.py → evaluate.py   │  MODEL stage
│ outputs: models/*.txt|*.joblib|model_card.json · reports/*.md|figures/*.png      │
│                                                                                  │
│ api.py: predict(airport, target_hour_utc, now_utc) -> dict   ◄── the ONLY entry point │
│   uses: features.Context.hour_features · rules.py (colour + DO) · drivers.py (WHY)    │
│         delay_estimate.py (likely-delay range) · confidence rules (config)            │
└──────────────────────────────────────┬───────────────────────────────────┘
                                       │ dict that follows contract/schema.json (v1.1)
┌──────────────────────────────────────▼───────────────────────────────────┐
│ FRONT END (frontend/, Streamlit)                                          │
│ backend_adapter.py picks real/mock and never crashes · app.py draws the page │
│ render.py = pure formatting (tested) · demo_cases.py reads reports/demo_cases.json │
└──────────────────────────────────────────────────────────────────────────┘
```
**Golden rule:** the **back end decides** (numbers, colour, advice, confidence, refusals). The **front end only displays** what `predict()` returns. Shared settings live in `config/config.yaml`. The response format is fixed by `contract/schema.json`.

---

## 4. Repository map
| Path | What's in it |
|---|---|
| `config/config.yaml` | **Shared settings:** airports (time zone, runway heading), lead-time window 3–12, delay thresholds, data splits, risk thresholds (RED ≥ 0.172, AMBER ≥ 0.117), confidence rules, likely-delay cut-offs, file paths |
| `config/airport_timezones.yaml` | Time zone for every airport code in the CSV (used by the time-zone repair) |
| `contract/schema.json`, `contract/examples/` | **The data contract** (JSON Schema) and 6 example responses. Authoritative. |
| `backend/` | Data pipeline, models, `predict()` (table in §3) |
| `frontend/` | Streamlit dashboard |
| `run_all.py` | One command: data → features → baselines → models → evaluation → test run → demo cases → severe-delay date list |
| `scripts/` | `smoke_real.py` (end-to-end check) · `list_severe_dates.py` · `setup_and_run.sh/.bat` (full rebuild + tests + run) |
| `tests/` | 134 tests: contract, leakage, monotonicity, wind maths, rendering, adapter, demo cases |
| `models/` | Trained models (rebuilt by `run_all.py`; shipped in the package for convenience) |
| `reports/` | Evidence: `validation_report.md`, `metrics.md`, `failure_cases.md`, `demo_cases.json/.md`, `severe_delay_dates.md`, `decisions_log.md`, figures, screenshots |
| `story/` | Draft pitch material (user story, why 3–12 h, pitch outline, limitations) |
| `docs/` | Full project history: plans, instructions, reviews (index in §11) |
| `data/processed/` | Intermediate files (git-ignored, rebuilt by `run_all.py`) |

---

## 5. Data: what you must know before touching anything
- **Source:** one provided CSV, 148,273 US flights (Jan 2023–Jul 2025, 136 airports) plus Meteostat-style hourly weather (`temp, prcp, wspd, wpgt, pres, snow, coco`) at origin and destination.
- **It's a ~1% sample.** About 6 ATL arrivals per day versus about 1,000 in reality. Hourly counts are tiny (about 1 flight per airport-hour). That's why we use a capacity *index* instead of real arrival rates, and show no capacity range.
- **Time-zone bug in the provided data, repaired:** weather had been matched on local time treated as UTC (a 4–6 h shift). `timezone_fix.py` repairs it, and check V3 proves it (the temperature peak moves to 14:00–17:00 local; see `reports/figures/timezone_fix.png`). **Everything internal is UTC.** Local time appears only on screen.
- **No wind direction** in the CSV, so crosswind is taken as the worst case (`crosswind_worst_kmh = wspd`). The proper function `features.wind_components()` exists and is tested (ATL runway 80°, DFW 180°). See open issue #1 in §9.
- **Fake zeros:** `snow` is always 0 (dropped). `wpgt` is 0 in 98% of rows (treated as missing, then dropped).
- **Weather coverage:** ATL/DFW have readings only about 9–10 h per day (hours where a sampled flight existed), so readings can be hours old. `obs_age_h` is a feature, the confidence rules use it, and anything over 12 h old leads to a refusal.
- **Splits by target hour:** train 2023–2024 · validation Jan–Mar 2025 · **test Apr–Jul 2025 (never used for tuning)**, with a 12 h buffer at the boundaries.
- **Severe** = departure > 45 min late **or cancelled** (cancelled goes in the top band).

## 6. Model: what it does and how good it is
- **Delay model:** LightGBM multiclass over 5 ordered bands (≤15, 15–30, 30–45, 45–60, > 60 or cancelled). P(> k) is the sum of the bands above k, so the probabilities can never contradict each other.
- **Capacity model:** LightGBM binary, "arrival delivered on time" (not cancelled, not diverted, ≤ 15 min late). The hourly index is the predicted share.
- **Features (31, hour-level, all known at forecast time):** latest weather and its age, 3 h/6 h wind and rain history, storm flags, worst-case crosswind, time of day, day of week, month, scheduled traffic (relative to the airport's own normal), interaction terms (storm × evening, storm × traffic, wind × traffic), lead time, the airport's historical severe rate. List: `backend/features.py: FEATURES`.
- **Leakage protection:** a training row for departure hour T and lead L uses only weather observed at or before T − L. `tests/test_leakage.py` deletes future weather and injects fake future storms; features must stay identical.
- **Results (test period, honest):**
  - Better than the historical-average baseline by a **small but real** margin (Brier at > 45 is 3–4% lower; bootstrap-confirmed). A simple logistic regression does about as well.
  - **RED rule:** catches about **half** of severely delayed flights 6 h ahead; one in three RED flights is severe, against a 17.8% base rate (**1.9× lift**).
  - Accuracy is almost flat from 3 h to 12 h. About 58% of the signal is season, time of day and traffic; storm features contributed ~0% (too few storm hours in the sample).
  - Thresholds come from winter validation data, so **in summer about 1 hour in 4 is RED**.
  - Full tables: `reports/metrics.md`. Failure cases: `reports/failure_cases.md` (e.g. ATL 28 Jun 2025 08:00, a miss the morning after a storm, last reading 7 h old; the tool *did* say LOW confidence).
- **Likely delay (v1.1, `backend/delay_estimate.py`):** derived from the 4 probabilities, no extra model.
  - Middle estimate = the first k where P(> k) < 0.5 gives the band below k.
  - Bad case = the largest k with P(> k) ≥ 0.25.
  - Because severe delays are rare in this data, the middle estimate is nearly always "under 15 min". The bad-case line carries the information.

---

## 7. How to change things (recipes)

> **Before any change:** run `python -m pytest -q` (expect 134 passed). After it: run it again, plus `python scripts/smoke_real.py`. Log every decision in `reports/decisions_log.md`.

### 7.1 Change a threshold or setting (no code)
Edit `config/config.yaml`:
- `risk_rules.red/amber.p_gt45_min` (colour thresholds; **choose them on validation data, never test**)
- `confidence_rules`
- `lead_time_hours`
- `delay_estimate.typical_prob` / `bad_case_prob`

Then run `python run_all.py` (it checks that the config thresholds match the validation percentiles; if you deliberately change the rule, update that check in `run_all.py`), then run the tests.

### 7.2 Add a field to what the dashboard shows (e.g. a new number)
1. **Contract first:** add the field to `contract/schema.json` (and to `required` if it's mandatory), bump `schema_version` in **both** `config.yaml` and the schema `const`, and update the 6 files in `contract/examples/`.
2. **Back end:** compute it in `backend/api.py` (put the logic in its own module, as `delay_estimate.py` does).
3. **Front end:** add a formatter in `frontend/render.py` (`view_model`) and draw it in `frontend/app.py` (`ok_card`). **Formatting only.**
4. **Tests:** add to `tests/test_contract.py` (real output) and `tests/test_render.py` (display).
5. Update `frontend/mock_backend.py` if it needs to re-stamp the field.

*Worked example:* v1.1 did exactly this when it replaced `flights` with `delay_estimate` (see `docs/16_Change_List_v1.1.md` and the git history).

### 7.3 Add a model feature
1. Add the column in `backend/features.py` → `Context.hour_features()`. **Only use data with time ≤ issue time.**
2. Add its name to `FEATURES`. Map it to a plain-language group in `backend/drivers.py` (otherwise WHY can't explain it).
3. `python run_all.py --no-test` while developing (this **doesn't touch the test set**). Compare validation scores in `reports/metrics.md`.
4. `tests/test_leakage.py` must still pass.
5. Run the test set **once**, at the end, and log it.

### 7.4 Add an airport (e.g. ORD)
1. `config/config.yaml` → `airports:` add `ORD: {icao: "KORD", tz: "America/Chicago", runway_heading_deg: <heading>}`. The time zone must also exist in `config/airport_timezones.yaml`.
2. `python run_all.py`. The pipeline is airport-agnostic (`HUBS` = the configured airports), so the data checks, features, models and refusals pick it up.
3. Check V3 (time-zone repair) for the new airport in `reports/validation_report.md`.
4. The front-end airport list comes from config automatically.

### 7.5 Change the screen
Only `frontend/app.py` (layout, CSS) and `frontend/render.py` (text/formatting). Run with `BACKEND=mock` for fast iteration. Never compute risk, colour or advice in the front end.

### 7.6 Change refusal rules or messages
`backend/api.py` `predict()`. Checks run in a fixed order: on the hour → airport → data range → 3–12 h → weather ≤ 12 h old. Codes are listed in the schema. Front-end titles are in `render.py: REFUSAL_TITLES`.

### 7.7 Demo cases and test dates
- `run_all.py: build_demo_cases()` writes `reports/demo_cases.json` (the dashboard picker) using documented selection rules. Labels must stay honest.
- `scripts/list_severe_dates.py` writes `reports/severe_delay_dates.md`: test hours with real severe delays and what the tool said 6 h earlier, including misses.

---

## 8. Rules the previous team followed (keep them)
1. **No data leakage:** features only from data known at forecast time. Banned post-event columns are listed in `backend/load.py`.
2. **Test set (Apr–Jul 2025) is for final measurement only.** Tune on validation (Jan–Mar 2025). Development runs use `--no-test`.
3. **Back end decides, front end displays.** The contract is changed only deliberately, with version bump, examples and tests together.
4. **Everything UTC internally.**
5. **Honesty:** show uncertainty (confidence, refusals), report failures, never present illustrative data as real.
6. **No LLM in the decision path.** Statistics and fixed rules only (judging rubric).

## 9. Known limitations and open issues (prioritised backlog)
| # | Item | Why it matters | Suggested approach |
|---|---|---|---|
| **1** | **Updated problem statement provides `challenge5_hourly_weather_ATL_DFW.csv` with wind direction and head/cross/tailwind for ATL 80° / DFW 180°.** It isn't in this repo (we never received it). | The brief lists "ignoring runway directionality" as a trap. We use worst-case crosswind. | Add it in `weather_timeline.py` (join on airport + UTC hour; **check its time zone**), feed `features.wind_components()` or the provided components as features, retrain on validation, run test once |
| 2 | ~1% flight sample | Hourly results are noisy; no meaningful capacity range | Use the full BTS on-time data if rules allow |
| 3 | Weather signal weak (storm features ~0% importance) | The model leans on season and time of day | More data, TAF forecasts, storm-duration and knock-on features |
| 4 | RED covers ~24% of summer hours (winter thresholds) | Alert fatigue | Season-aware thresholds chosen on more validation data |
| 5 | Capacity is an on-time index, not true AAR | Brief metric is AAR RMSE | Real AAR data (FAA ASPM) if allowed |
| 6 | Only ATL and DFW configured | — | Recipe 7.4 |
| 7 | `demo_cases.json` `version` embeds the build-time git sha; rebuilds change 3 PNGs by bytes | Cosmetic diffs | Use the model card version without the sha |
| 8 | `scripts/setup_and_run.bat` / `RUN_DASHBOARD.bat` not tested on Windows | — | Test once on Windows |

## 10. Glossary
| Term | Meaning |
|---|---|
| Lead time | Hours between "now" (forecast issue time) and the target hour (3–12) |
| Severe | > 45 min late or cancelled |
| Brier score | Accuracy of a probability (lower is better) |
| PR-AUC | How well risky hours are ranked above safe ones (higher is better; compare with the base rate) |
| Climatology (B0) | Baseline: historical rate for the same airport, hour and month |
| Capacity index | Share of scheduled arrivals delivered on time (our stand-in for AAR) |
| Leakage | Using information that wasn't available at forecast time |
| Contract | `contract/schema.json`, the exact format of `predict()`'s answer |

## 11. Document index (history and detail)
| Doc | Use it for |
|---|---|
| `HOW_TO_RUN_AND_TEST.md` | Click-by-click run and test guide |
| `docs/04_Data_Contract.md` | Contract rules in prose (time zones, units, nulls, refusal codes) |
| `docs/16_Change_List_v1.1.md` | The last change: flights removed, likely-delay range added |
| `docs/02_…`, `docs/03_…` | Original back-end and front-end build instructions (design rationale) |
| `docs/05_Initial_Handover.md` | Original decisions D1–D12, data findings, the 26-item trap register |
| `docs/08`, `docs/12`–`docs/15` | Checkpoint reviews and lead decisions L-001 to L-020 |
| `docs/11_…`, `docs/14_…` | Integration and testing procedures |
| `reports/decisions_log.md` | Every decision (D-, L-, I- numbers) with its reason |

## 12. State at handover (verified by the lead)
- `python run_all.py`: exit 0, data checks V1–V10 pass, gate checks pass
- `python -m pytest -q`: **134 passed**
- `scripts/smoke_real.py`:
  - true RED case (DFW 19 May 2025 20:00) → RED, middle estimate "15–30 min", bad case "more than 60 min (33%)"
  - calm case → GREEN, HIGH
  - failure case → GREEN, LOW
  - all 5 refusal types correct
  - every call under 0.2 s
- Screenshot of the v1.1 screen on the real back end: `reports/figures/ui_v11_real.png`
