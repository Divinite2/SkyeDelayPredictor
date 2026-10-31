# Progress Summary: Airport Arrival Capacity and Delay-Risk Forecaster (Back End, Track A)

**Challenge:** Autonomous SG 2026, Airbus Track, Challenge #5
**Status at the time of writing:** Checkpoint 0 (back-end side) done ✅ · **Gate 1 / Checkpoint B-1 done ✅ (waiting for the lead's sign-off)** · Gate 2 not started
**Documents followed:** `01_Workflow(1).md`, `02_Instructions_Backend.md`, `04_Data_Contract.md`, `05_Initial_Handover(1).md`, `06_First_Checkpoints(1).md`
**Input data:** `Flight_Data_With_Weather_Final.csv` (64 MB, 148,273 rows × 123 columns), never edited

---

## 1. Executive summary

The project is set up, the back end ↔ front end data contract is written and passes its tests, and the raw flight and weather file has been **repaired, cleaned and validated**. All of it is rebuilt with one command (`python run_all.py`, about 55 s).

The most important result is the **time-zone repair**. In the file as provided, weather is shifted by 4–6 hours, so the "hottest" hour falls at 20:00–21:00 local. After the repair, the daily temperature peak lands at **14:00–17:00 local** for ATL and DFW, in both summer and winter. That's the physically expected window (13:00–18:00), and it confirms the weather is now on the right hour. Everything downstream depends on this.

All ten required validation checks (V1–V10) pass, plus one extra check I added (V3b) to verify the airport time-zone table against the file itself. Every number your lead measured on the file was reproduced, apart from small definitional differences that are explained in §5.

No modelling has been done yet. That is Gate 2 and needs your go-ahead.

---

## 2. How the work was run

| Rule (from instructions) | How it was applied |
|---|---|
| Worker role; approval before each phase | Each phase started only after explicit approval. Small changes were decided by me and logged, as you instructed. |
| Testing at major checkpoints only (updated instruction) | Tests ran at Checkpoint 0 (schema) and Gate 1 (validation report). Nothing was tested between checkpoints. |
| Only the provided CSV, no external data | Followed. The only reference data added is an airport → time-zone table, which 02 §0 allows. It's checked against the CSV itself (V3b). |
| Never edit the raw file | Followed. All fixes are in code. |
| Test period (Apr–Jul 2025) locked | Only row counts and base rates for that period were computed, for the split table that V9 requires. No model has been scored on it. |
| Log every deviation | 12 entries in `reports/decisions_log.md` (D-001 to D-012). |

---

## 3. Phase 0: Setup and data contract (Checkpoint 0)

### 3.1 What was built
| Item | File | Notes |
|---|---|---|
| Folder layout from 02 §0 | `backend/ config/ contract/ data/ models/ reports/ tests/ frontend/` | `frontend/` is empty and belongs to Track B |
| Pinned dependencies | `requirements.txt` | Python 3.11 · pandas 3.0.6 · pyarrow 26.0.0 · numpy 2.4.6 · lightgbm 4.7.0 · scikit-learn 1.9.1 · pyyaml 6.0.3 · jsonschema 4.26.0 · pytest 9.2.0 · matplotlib 3.11.2 · tabulate 0.10.0. Streamlit is left for the front end to pin. |
| Shared config | `config/config.yaml` | Copied **exactly** from 04 §2, plus a back-end-only `paths:` block (D-001) |
| Response schema | `contract/schema.json` | JSON Schema draft 2020-12, chosen over Pydantic (D-002). Covers `ok`, `refused` and `error` responses, all 6 refusal codes, `source: "SIMULATED"`, and the ID format `SIM-XXX-YYYYMMDDHH-nn`. |
| Six example responses | `contract/examples/*.json` | `ok_red` (ATL, 6 h ahead, thunderstorm), `ok_green` (DFW, 4 h, fair), `refused_short` (2 h), `refused_long` (13 h), `refused_airport` (XYZ), `error`. Made by `contract/make_examples.py` so the flight risk always equals the hour risk (D-003). |
| Contract test | `tests/test_mock_matches_schema.py` | See below |
| Decisions log | `reports/decisions_log.md` | Started |

### 3.2 Checkpoint 0 test result: **9 / 9 pass**
The test checks more than the schema. It also asserts the rules that a schema can't express:
- P(>15) ≥ P(>30) ≥ P(>45) ≥ P(>60), each rounded to 3 decimals
- `lead_time_h` equals target minus now, and lies within the 3–12 h window from config
- every weather driver's `observed_at_utc` and `last_obs_utc` is ≤ `now_utc` (the leakage guarantee the user can see)
- exactly `rows_shown` (5) flights, sorted, all `SIMULATED`, inside the target hour, with probabilities **equal** to the hour risk
- a deliberately broken response (wrong `source`, probability of 1.5) is **rejected**

### 3.3 Still open at Checkpoint 0 (needs people, not code)
- The front-end lead must review the six examples, including two refusal messages I drafted (LEAD_TOO_LONG, UNKNOWN_AIRPORT) because 04 only gives the wording for LEAD_TOO_SHORT.
- `04_Data_Contract.md` still says "DRAFT". Both leads need to sign it as "Agreed v1.0".

---

## 4. Phase 1: Data repair and validation (A1 → Gate 1)

### 4.1 Pipeline
```
raw CSV ─► load.py ─► timezone_fix.py ─► weather_timeline.py ─► weather_hourly.parquet
                          │                                     
                          └──────────► clean_flights.py ─────► flights_clean.parquet
                                                    └─► validate.py ─► validation_report.md + 3 figures
```
| Module | Job |
|---|---|
| `backend/common.py` | Loads the config and resolves file paths |
| `backend/load.py` | A1.1: reads 29 needed columns with fixed types. Also holds the **banned-column list** from 02 §A2 (`is_banned()`), used now and again in the A2 leakage test. |
| `backend/timezone_fix.py` | A1.2: converts local schedule times to UTC with `zoneinfo` (handles daylight saving). **Arrival = departure UTC + scheduled duration.** Re-keys weather (local D H → UTC D H:00). Checks the time-zone table against the data. |
| `backend/weather_timeline.py` | A1.2 + A1.3: builds one weather row per airport per UTC hour from both the origin and destination readings. Leaves overnight arrivals out of this step. Cleans the values. Maps `coco` codes to labels and groups (04 §7). |
| `backend/clean_flights.py` | A1.4: delay bands, cancellation and diversion handling, the capacity label, duplicate check, split assignment |
| `backend/validate.py` | A1.5: V1–V10, the split table, evidence figures and the report |
| `run_all.py` | One command for the data stage. Exits with an error if any hard check fails. |

### 4.2 Key method choices
- **Weather timeline:** 291,090 source readings → **247,700 airport-hours** across all airports. Numeric values use the median; `coco` uses the most frequent value (D-009). Each row keeps `n_source_rows` and `conflict_flag`.
- **Overnight arrivals** (CRS_ARR < CRS_DEP): **5,456 rows (3.7%)** left out of the destination side of the timeline. The flights themselves are kept.
- **Delay bands:** `le15 / 15_30 / 30_45 / 45_60 / gt60`, using a strict ">" comparison (45 minutes exactly is not > 45). **Cancelled → gt60**, and the cancellation overrides any delay value.
- **Capacity label (`delivered`):** 1 if not cancelled, not diverted and ARR_DELAY ≤ 15. Diverted = not delivered. Unknown arrival delay = null (D-012).
- **Splits** use the *target* hour in UTC: train 2023–2024 · validation Jan–Mar 2025 · test Apr–Jul 2025. The 12 h buffer between splits is applied when the training rows are built (A2).

### 4.3 Validation results (`reports/validation_report.md`)

| # | Check | Result | Key number |
|---|---|---|---|
| V1 | Required columns and types | ✅ | 148,273 rows · 123 columns · 2023-01-01 → 2025-07-31 · 136 origin airports · ATL 8,415 dep / 5,429 arr · DFW 7,736 / 4,032 |
| V2 | Duplicates | ✅ | 0 |
| V3 | Time-zone repair | ✅ | Peak moved into 13–18 local in all 4 panels (table below) |
| V3b | Airport time-zone table vs schedule *(added)* | ✅ | Implied local arrival = CRS_ARR_TIME for **100.00%** of flights (99.99% of flights touching ATL/DFW) |
| V4 | Weather conflicts | ✅ | 26 airport-hours: 0.071% of hours with more than one reading, 0.010% of all hours (limit 1%) |
| V5 | Weather coverage (report only) | ✅ | ATL **9.7 h/day**, DFW **8.7 h/day**; no day without any reading |
| V6 | Range violations | ✅ | 0 out-of-range values; 2,857 invalid `coco` (code 0) → null |
| V7 | Fake zeros | ✅ | `snow` never non-zero → dropped. 284,263 `wpgt` zeros → null; only 2.4% of hours still have a value → **`wpgt` dropped** (D-008) |
| V8 | Cancelled and diverted | ✅ | Cancelled 1,901 = raw · diverted 377 = raw · 73 cancelled-with-delay rows flagged |
| V9 | Split sizes | ✅ | Table below |
| V10 | Banned columns | ✅ | None in the weather timeline. Runs again on the feature table in A2. |

**Time-zone repair detail** (figure: `reports/figures/timezone_fix.png`)

| Airport / season | Before: coolest → hottest hour | After: hottest hour | Pass |
|---|---|---|---|
| ATL summer | 10:00 (22.7 °C) → 20:00 (31.5 °C) | **16:00** | ✅ |
| ATL winter | 08:00 → 21:00 | **16:00** | ✅ |
| DFW summer | 12:00 → 21:00 | **17:00** | ✅ |
| DFW winter | 13:00 → 20:00 | **14:00** | ✅ |

The ATL summer "before" values (22.7 °C at 10:00, 31.5 °C at 20:00) **match your lead's numbers exactly**.

**Split table (V9)**

| Airport | Split | Departures | Severe (>45 or cancelled) | Arrivals | Delivered on time |
|---|---|---|---|---|---|
| ATL | train | 6,624 | 9.1% | 4,135 | 81.0% |
| ATL | validation | 723 | 11.6% | 511 | 78.5% |
| ATL | test | 1,067 | 15.8% | 782 | 76.9% |
| DFW | train | 5,919 | 13.7% | 3,083 | 74.9% |
| DFW | validation | 736 | 12.6% | 382 | 74.6% |
| DFW | test | 1,080 | 19.7% | 566 | 65.9% |
| **Both** | train / val / test | 12,543 / 1,459 / 2,147 | 11.3% / 12.1% / **17.8%** | 7,218 / 893 / 1,348 | 78.4% / 76.8% / 72.3% |

### 4.4 Signal check (B1.8): weather type vs severe delay
ATL + DFW departures, using the weather at each flight's own departure hour. **This is evidence only and will never be a feature** (it would be leakage). Figure: `reports/figures/severe_by_weather.png`.

| Weather group | Flights | Severe rate (>45 or cancelled) | Departed >45 min late |
|---|---|---|---|
| Calm (clear to overcast) | 13,922 | 10.5% | 9.7% |
| Low visibility | 479 | 14.6% | 12.9% |
| Rain | 1,547 | 23.3% | 19.5% |
| Showers | 107 | 35.5% | 30.8% |
| **Convective (thunderstorm)** | **69** | **50.7%** | **40.6%** |
| Winter | 21 | 66.7% | 4.8% (mostly cancellations; too few flights to use) |

Thunderstorms are about **5× worse than calm weather**, which confirms the weather-code mapping and that there's a real signal to model.

### 4.5 Outliers inspected (A1.3)
| Row | Value | Assessment |
|---|---|---|
| SEA, 2023-10-19 (2 flights) | wspd 98.3 km/h, overcast, 19 °C | Almost certainly a feed error, but inside the 0–200 range rule, so kept. Not ATL/DFW. |
| DCA, 2025-04-27 | wpgt 216 km/h with mean wind 20.5 km/h | Physically implausible. Irrelevant because `wpgt` is dropped. |

---

## 5. Findings for the lead

1. **The time-zone repair is confirmed** (R1 resolved for ATL and DFW). No airport needs to be excluded.
2. **The test period is much harder than training:** 17.8% severe vs 11.3% (summer storm season). The test is fair, but the climatology baseline (B0) will under-predict, and absolute scores on test will be worse than on validation. The pitch should say this.
3. **Storm sample is small:** only 69 thunderstorm and 107 shower departures at ATL+DFW in total (R3). The planned explicit interaction features (storm × evening, storm × traffic) are justified. Every rate will be reported with its count (T17).
4. **Small differences in the overall severe rate:** the documents say 9.7%. I get 10.1% when "severe" means *departed* > 45 min late, and 11.3% when cancellations count as > 60, as the rules require. The difference is a matter of definition, not an error.
5. **Gaps in weather readings:** ATL has a reading in about 10 hours per day and DFW in about 9, so readings are often several hours old. `obs_age_h`, the confidence rule and the NO_RECENT_WEATHER refusal are all needed.
6. **No gust variable:** `wpgt` is too sparse. Wind is represented by mean speed only, alongside the existing "no wind direction" limitation.

---

## 6. Decisions log (summary of `reports/decisions_log.md`)

| ID | Decision | Against instructions? |
|---|---|---|
| D-001 | The CSV location is set in config (`paths.raw_csv`) because file links aren't supported here. The code uses `data/raw/` first if the CSV is there. | Minor layout change |
| D-002 | JSON Schema (not Pydantic) for the contract | No: 04 says pick one |
| D-003 | Examples made by a script; two refusal messages drafted by me | Needs front-end sign-off |
| D-004 | Streamlit pinning left to the front end | No |
| D-005 | Request fields may be null on refusal/error responses | No: refinement |
| D-006 | The 3-decimal rule is checked in the tests (the schema's built-in check fails on ordinary floats) | No |
| D-007 | Added a time-zone table for all 350 airport codes, plus check V3b | No: 02 §0 allows time-zone reference settings |
| D-008 | `wpgt` dropped (2.4% non-missing, under the 10% rule) | No: follows the rule |
| D-009 | `coco` takes the most frequent value, not the median | Minor |
| D-010 | `wpgt` range set to 0–300; the outliers above explained | No |
| D-011 | Added `common.py` and `validate.py` modules | Minor layout addition |
| D-012 | Unknown arrival delay → `delivered` = null | No |

---

## 7. Traps ticked so far (05 §5)
| Trap | Status |
|---|---|
| T5 Time-zone shift in the provided weather | ✅ Repaired and proven (V3, figure) |
| T6 A second time-zone bug on our side | ✅ Everything is UTC internally, `zoneinfo` handles daylight saving, and the table is checked against the data at 100% (V3b) |
| T7 Missing stored as 0 | ✅ `snow` dropped, `wpgt` zeros → null and then dropped, `coco` 0 → null |
| T9 Cancelled flights | ✅ → gt60 and not delivered |
| T10 Overnight arrival dates | ✅ Arrival = departure UTC + duration; overnight rows left out of the timeline |
| T11, T12, T13 | Partly: the date split is in place and the test set is untouched. Purge, training-period-only rates and tuning on validation come in A2/A3. |
| T1–T4, T14–T26 | Due in Gate 2 / Gate 3 |

---

## 8. Deliverables
| Path | Content |
|---|---|
| `run_all.py` | One-command rebuild (data stage) |
| `backend/*.py` | `common, load, timezone_fix, weather_timeline, clean_flights, validate` |
| `config/config.yaml`, `config/airport_timezones.yaml` | Shared config and the time-zone reference table |
| `contract/schema.json`, `contract/examples/*.json`, `contract/make_examples.py` | Data contract |
| `tests/test_mock_matches_schema.py` | Checkpoint 0 test (9/9) |
| `data/processed/flights_clean.parquet` | 148,273 flights with UTC times, labels and splits |
| `data/processed/weather_hourly.parquet` | 247,700 cleaned airport-hours (UTC) |
| `reports/validation_report.md` | V1–V10 with full detail |
| `reports/gate1_report.md` | Gate 1 report in the lead's format |
| `reports/decisions_log.md` | D-001 to D-012 |
| `reports/figures/timezone_fix.png` | Before/after proof (for the pitch, C2) |
| `reports/figures/weather_coverage.png` | Readings by local hour |
| `reports/figures/severe_by_weather.png` | Evidence chart (for the pitch, C2) |

**To reproduce:** `pip install -r requirements.txt` → put the CSV in `data/raw/` → `python run_all.py` → `python -m pytest tests`.

---

## 9. Next steps (Gate 2: "The model is honest"; waiting for approval)
1. **A2 features:** training rows for each (departure at T, lead L = 3…12), issued at t = T − L. Weather joined with `merge_asof(backward)` on obs_time ≤ t, plus 3 h/6 h history, storm flags, worst-case crosswind (plus a unit-tested `wind_components()` using runway headings 80°/180°), time-of-day features, traffic relative to each airport's normal level, interaction terms, `lead_time_h`, and a training-period-only airport rate. 12 h buffer at split boundaries.
2. **`tests/test_leakage.py`:** delete future weather → features unchanged; no banned columns; driver times ≤ now; stop if any ROC-AUC > 0.95.
3. **A3:** baselines B0 (climatology) and B1 (logistic regression) first, then the LightGBM 5-band delay model and the capacity-index model. Metrics per lead time: Brier at each threshold, RPS, PR-AUC at > 45, precision/recall at RED, capacity RMSE. Tuning on validation only. Failure cases (one miss, one false alarm).
4. **A4:** `predict()` with the refusal rules, WHY (from `pred_contrib`), DO rules, confidence, and the simulated flight list. Plus `tests/test_contract.py`.
5. **Gate 2 checks:** leakage test passes · Brier at > 45 beats B0 at 3 h and 6 h (or an honest explanation) · risk numbers never out of order.
