# 02 · Back-End Instructions: Data, Model, Evaluation, `predict()`

**For:** Track A (data / ML developers)
**You must also read:** `04_Data_Contract.md` (binding), `05_Initial_Handover.md` §5 (trap register)
**Scope:** everything in this document is **P0** (must have) unless it's marked *Removed*. There's no P1. Do the work in the order of this document. If a step gets stuck, use the fallbacks in `01_Workflow.md` §4.

> **What the back end does, in plain words:** take the hackathon's flight file, fix its problems, learn from 2023–2024 how weather and traffic lead to delays, and answer one question: *"For this airport and this hour, 3–12 hours from now, how likely are delays, how much arrival capacity will there be, and why?"* Answers must use **only information that existed at the moment the question was asked**.

---

## 0. Ground rules
1. **Only the provided CSV is used.** No downloads or external datasets. Reference settings (time zones, runway headings from the brief) live in `config.yaml`.
2. **Never edit the raw file.** Every fix happens in code, so `python run_all.py` reproduces everything.
3. **The test period (Apr–Jul 2025) is locked.** Don't look at test scores while choosing features, thresholds or settings. Tune on validation (Jan–Mar 2025). Test is used **once per submitted version**.
4. **Log every deviation** from these instructions in `reports/decisions_log.md` (what, why, effect).

> 🔧 **Stack:** Python 3.11, pandas, pyarrow, numpy, lightgbm, scikit-learn, pyyaml, pydantic or jsonschema, pytest, matplotlib. Pin versions in `requirements.txt`. Set `random_state=42` everywhere.

**Repository layout**
```
config/config.yaml
backend/  load.py  timezone_fix.py  weather_timeline.py  clean_flights.py  features.py
          baselines.py  train.py  evaluate.py  drivers.py  rules.py  simulate.py  api.py
contract/ schema.json  examples/
frontend/ (Track B)
data/raw/  data/processed/   models/   reports/figures/
tests/    run_all.py   requirements.txt   README.md
```

---

## Step A1 (P0): Load, repair, validate

### What we already know about the file (verified by the lead)
| Fact | Number |
|---|---|
| Rows × columns | 148,273 × 123 |
| Date range | 2023-01-01 → **2025-07-31** (no data after July 2025) |
| Airports | 136. ATL: 8,415 departures / 5,429 arrivals. DFW: 7,736 / 4,032 |
| It's a **sample** | About 6 arrivals per day at ATL in the file, versus roughly 1,000 in reality. About 1 flight per airport-hour. |
| Weather columns | `temp, prcp, wspd, wpgt, pres, snow, coco` for `_ORIGIN` and `_DEST`. **No wind direction.** |
| Fake zeros | `snow` = 0 in **100%** of rows. `wpgt` = 0 in **98%** of rows. |
| Time-zone shift | Weather was looked up with **local** scheduled time treated as **UTC**. Summer ATL temperature by local departure hour is coolest around 10:00 and hottest around 20:00. |
| Weather keys | `_ORIGIN` weather follows the `CRS_DEP_TIME` hour. `_DEST` weather follows the `CRS_ARR_TIME` hour. Rows for the same airport, date and hour agree 99.93% of the time, so it's one underlying table. |
| Severe delays | 9.7% of departures > 45 min. 20.5% > 15 min. Cancelled 1.3%. Diverted 0.25%. |

### Tasks
**A1.1 Load** with explicit dtypes. Keep only the columns listed in §A2 "allowed" plus the label columns.

**A1.2 Repair the time-zone shift and rebuild one hourly weather timeline per airport.**
- The weather attached to a row with local date `D` and local hour `H` is really the observation at **UTC `D H:00`**. Build `weather_hourly` keyed by `(airport, obs_time_utc = D + H hours, as UTC)`, collecting values from both the `_ORIGIN` side (hour of `CRS_DEP_TIME`) and the `_DEST` side (hour of `CRS_ARR_TIME`).
- **Overnight arrivals** (`CRS_ARR_TIME < CRS_DEP_TIME`, 3.7% of rows): the date used for `_DEST` weather is ambiguous. **Exclude them from timeline building**. Still keep the flights themselves.
- Keep `n_source_rows`. Set `conflict_flag` where rows disagree (expected about 0.07%) and take the median.
- **Prove the repair:** plot mean temperature by **local** hour (from the repaired UTC timestamps, converted with `zoneinfo`) for ATL and DFW, summer and winter. **Pass:** the peak falls between 13:00 and 18:00 local. Save the before/after figure as `reports/figures/timezone_fix.png`. Track C needs it for the pitch.
- If the check fails for an airport, **exclude that airport** and log it. Don't force it.

> 🔧 Convert flight times: `sched_dep_utc = localize(FL_DATE + CRS_DEP_TIME, tz).astimezone(UTC)` with `zoneinfo`, which handles daylight saving. Compute `sched_arr_utc = sched_dep_utc + CRS_ELAPSED_TIME minutes`. Don't use `CRS_ARR_TIME` plus a date guess. HHMM integers: `h = t // 100`, `m = t % 100`. Treat `2400` as next day 00:00, although none were found.

**A1.3 Clean the weather values**
- `snow` → drop the column (no information).
- `wpgt` → `null` where 0. Keep it as a feature only if more than 10% of rows are non-null after that. Otherwise drop it and log.
- Range checks (out of range → `null`, never delete the row): temp −40…55 °C, pres 900…1100 hPa, wspd 0…200 km/h, prcp 0…200 mm. Note: the file contains `wpgt` = 216 and `wspd` = 98.3. Inspect those rows.
- `coco` → integer 1–27, otherwise `null`. Add `coco_label` and `coco_group` using `04_Data_Contract.md` §7.

**A1.4 Clean the flights**
- Labels: `dep_delay_min = DEP_DELAY`, with `delay_band` ∈ {`le15`, `15_30`, `30_45`, `45_60`, `gt60`}. **Cancelled → `gt60`.** Delays are compared as `>` (a delay of exactly 45 is **not** > 45).
- Flag the 73 rows that are cancelled but have a `DEP_DELAY` value. The cancellation wins.
- Diverted flights: they did depart, so they keep their departure delay. For the arrival capacity label, **diverted = not delivered**.
- Duplicate check on `(FL_DATE, OP_UNIQUE_CARRIER, OP_CARRIER_FL_NUM, ORIGIN, DEST)`. The lead found 0. Assert this.

**A1.5 Validation report → `reports/validation_report.md`**, one row per check with ✅/❌, the number found and the action taken:

| # | Check | Pass rule |
|---|---|---|
| V1 | Required columns and dtypes | all present |
| V2 | Duplicates | 0 |
| V3 | Time-zone repair | temperature peak 13:00–18:00 local, ATL and DFW, summer and winter |
| V4 | Weather conflicts | < 1% of airport-hours |
| V5 | Weather coverage | report hours per day with an observation (expected about 9–10 at ATL/DFW). No pass/fail, but it **must be reported**. |
| V6 | Range violations | counted and nulled |
| V7 | Fake zeros | `snow` dropped, `wpgt` zeros → null |
| V8 | Cancelled and diverted handling | counts match the raw file |
| V9 | Split sizes | rows and severe-delay rate per split per airport |
| V10 | Banned columns | none present in the feature table (see A2) |

**→ GATE 1.** Send the gate report (format in `01_Workflow.md` §6) to the lead.

---

## Step A2 (P0): Leakage-safe features

### The core idea in plain words
Each training example asks: *"Standing at time **t** (the forecast moment), what will happen to flights in hour **t + L**?"*, with L between 3 and 12. The model may only see things that were **known at time t**. Weather at the flight's own departure time **is not allowed**. That's the brief's "Data Leakage Across Time Steps" trap.

> 🔧 **Training rows:** for every departing flight at ATL/DFW with scheduled departure hour `T` and every `L ∈ {3,…,12}`, create a row with `issue_time t = T − L`. That's about 16k flights × 10 ≈ 160k rows. Weather features come from `weather_hourly` with **`pd.merge_asof(direction="backward")` on `obs_time_utc ≤ t`**, plus lags. Include `lead_time_h` as a feature, which gives **one model for all lead times**. Assign train/validation/test by **target hour T**. **Purge** rows whose `t` falls in the previous split (a 12 h buffer at each boundary).

### Banned columns (only known after the event, so never a feature)
`DEP_TIME, DEP_DELAY*, DEP_DEL15, DEP_DELAY_GROUP, TAXI_OUT, WHEELS_OFF, WHEELS_ON, TAXI_IN, ARR_TIME, ARR_DELAY*, ARR_DEL15, ARR_DELAY_GROUP, CANCELLED, CANCELLATION_CODE, DIVERTED, ACTUAL_ELAPSED_TIME, AIR_TIME, CARRIER_DELAY, WEATHER_DELAY, NAS_DELAY, SECURITY_DELAY, LATE_AIRCRAFT_DELAY, FIRST_DEP_TIME, TOTAL_ADD_GTIME, LONGEST_ADD_GTIME, DIV*`, and **all raw `*_ORIGIN` / `*_DEST` weather columns** (they're used only to build the timeline).

### Allowed (known in advance)
Schedule (`FL_DATE, CRS_DEP_TIME, CRS_ARR_TIME, CRS_ELAPSED_TIME, DISTANCE`, carrier, origin, destination), calendar fields, and the weather timeline up to `t`.

### P0 feature list (hour-level: describes the airport and the target hour)
| Group | Features | Why |
|---|---|---|
| Latest weather at t | `temp_c, prcp_mm, wspd_kmh, pres_hpa, coco_group` (one-hot), `obs_age_h` (hours since that reading) | Current state. Age tells the model how stale it is (coverage is only about 9–10 h/day). |
| Recent history | max `wspd` and sum of `prcp` over the last 3 h and 6 h up to t; `storm_last_6h` (any `coco_group = convective`), `hours_since_storm` | Captures building weather |
| **Runway wind** | `crosswind_worst_kmh = wspd_kmh` (direction unknown, so worst case). Write the full function `wind_components(wspd, wdir, runway_heading)` returning headwind/crosswind/tailwind, and unit-test it. **It isn't fed real directions because the file has none.** | Brief trap "Ignoring Runway Directionality". We show the method and state the limitation. |
| Time | target local hour (sin/cos), `evening_flag` (17:00–23:00 local), day of week, month | Delays build up through the day |
| **Traffic** | `sched_deps_in_hour` and `sched_arrs_in_hour` (sampled counts for the target hour), **`rel_volume`** = count ÷ this airport's training-period mean for the same hour-of-week | The brief says **normalise**. Raw counts would just mean "big airport". |
| **Interactions** | `storm_last_6h × evening_flag`, `storm_last_6h × rel_volume`, `wspd_kmh × rel_volume` | From the lead's check of the file: thunderstorm or shower departures in the evening are delayed > 45 min 34% of the time, against 10% in the morning. In the busiest quarter it's 35% against 23% in the quietest. Few storm rows exist, so make the combination explicit. |
| Horizon | `lead_time_h` | Accuracy should fall with lead time |
| Airport | `airport_hist_severe_rate` (training period only) | Generalises without one-hot airport IDs |

### Automated leakage test (P0, mandatory): `tests/test_leakage.py`
1. For 500 random rows, **delete every weather row with `obs_time_utc > t`** from the timeline, recompute the features, and assert they're **identical**.
2. Assert that no banned column appears in the feature matrix.
3. Assert `drivers[].observed_at_utc ≤ now_utc` in API responses.
4. **Smell test:** if any model scores ROC-AUC > 0.95 on validation, stop and investigate. Weather can't predict delays that well 3 h ahead, so a score like that means leakage.

---

## Step A3 (P0): Baselines, then models

### Baselines (build these first, because everything is compared against them)
| Name | What it does |
|---|---|
| **B0 Climatology** | P(delay > k) = training-period rate for the same airport × local hour × month. For capacity, the same idea. |
| **B1 Logistic regression** | Same P0 features. One model per threshold k, monotonicity enforced after prediction. |

### Model 1: delay bands (main model)
- **LightGBM multiclass** over the 5 ordered bands. **P(delay > k) = sum of the probabilities of the bands above k.** Monotonic by construction.
- **Why not four separate yes/no models:** they can contradict each other (P(>45) > P(>30)), and a controller would stop trusting the tool.
- Starting parameters: `num_leaves=31, learning_rate=0.05, min_data_in_leaf=100, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0`, early stopping on validation multi-logloss. Small search only (≤ 20 configurations), **on validation**.
- Class imbalance: **don't** oversample. We need honest probabilities. Use the Brier score and PR-AUC instead of accuracy.

### Model 2: arrival capacity index (our stated substitute for AAR)
- **Label per arriving flight at ATL/DFW:** `delivered = 1` if not cancelled, not diverted, and `ARR_DELAY ≤ 15`.
- **Capacity index for an airport-hour** = share of scheduled arrivals delivered (by scheduled arrival hour, UTC).
- **Model:** LightGBM binary on arrival rows with the same feature design (arrival airport's weather timeline, `lead_time_h`, etc.). Predicted hour index = mean predicted probability for that hour's arrivals, or for a hypothetical arrival using hour-level features when the hour has none.
- **Range (`index_low` / `index_high`):** the 10th–90th percentile of validation errors at the same lead time, added to the prediction and clipped to [0, 1]. Simple and honest.
- **Metric (brief requirement):** **RMSE** of predicted vs observed capacity index per airport-hour, weighted by the number of arrivals, per lead time, against B0.
- **State clearly everywhere:** "AAR isn't in the provided data. This is a delivered-on-time arrival index from a ~1% flight sample."

### Metrics → `reports/metrics.md`
For each lead time 3…12 (headline 3/6/9/12), each airport and overall, model vs B0 vs B1:
| Metric | For |
|---|---|
| Brier score for each k ∈ {15, 30, 45, 60} | Delay |
| Ranked Probability Score (all bands) | Delay |
| **PR-AUC at > 45 min** (brief requirement) plus the base rate | Delay |
| Precision / recall at the **RED** threshold | Delay. Used for impact claims. |
| **RMSE**, capacity index | Capacity |

**Gate 2 pass (with honesty rule):** (a) leakage test passes; (b) the model's Brier score at > 45 beats B0 at L = 3 and L = 6; (c) monotonicity is never violated. **If the model doesn't beat B0 at 9–12 h, that's an acceptable result. Report it.** It supports the 12 h cut-off.

### Failure cases → `reports/failure_cases.md` (P0)
From the **validation** set first (and the test set after the final run), pick:
1. **A miss:** the hour with the highest observed severe-delay share where the model predicted GREEN. Explain why (e.g. the storm formed after the last observation, or there was no reading for 5 h).
2. **A false alarm:** RED predicted, but flights left on time.
For each: timestamps, the inputs the model saw, the prediction, what happened, the reason, and what would fix it (e.g. TAF forecasts, wind direction, full schedule).

---

## Step A4 (P0): `predict()`, WHY, DO, confidence
Implement exactly `04_Data_Contract.md` §4–5.

**Order of operations in `predict()`:**
1. Parse and validate: on the hour → airport known → in data range → `3 ≤ lead ≤ 12` → weather observed within 12 h before `now` → otherwise **refuse** with the right code.
2. Build features **as of `now_utc`**, using the same code as training (no copy-pasted logic).
3. Predict bands → exceedance probabilities → round to 3 decimals → assert monotonic.
4. Predict the capacity index and range.
5. **Risk level** from `config.risk_rules`: RED if either RED condition holds, otherwise AMBER if either AMBER condition holds, otherwise GREEN.
6. **DO line** from a fixed rule table in `backend/rules.py`:

| rule_id | Condition | Text |
|---|---|---|
| RED-1 | RED | "Consider a pre-emptive arrival-rate reduction or ground delay programme for this hour." |
| AMBER-1 | AMBER | "Elevated risk: prepare contingency and re-check at the next forecast update." |
| GREEN-1 | GREEN | "No action suggested by the model." |

   Thresholds are **starting values**. Tune them on **validation** to a stated false-alarm rate, and record the chosen values and the reasoning in `decisions_log.md`.
7. **WHY (drivers):** LightGBM `pred_contrib=True`. Sum the contributions for the bands `45_60` and `gt60`, take the top 3 features with positive contributions, and map them to plain labels using a dictionary in `drivers.py`. Attach the **actual value and its `obs_time_utc`**. Label in docs as "approximate influence".
8. **Confidence:** from `config.confidence_rules`. LOW if `lead ≥ 10` **or** `obs_age_h ≥ 3`. HIGH if `lead ≤ 6` **and** `obs_age_h ≤ 1`. Otherwise MEDIUM. List the reasons. **Adjust these rules if validation shows a different pattern, and log it.**
9. **Flights (simulated only):** `simulate.py` generates `config.flight_list.rows_shown` dummy departures for the airport and target hour. Carrier, destination and scheduled minute are sampled from the **training-period** pattern for that airport and local hour (use the real file only to learn the pattern). Seed = hash(airport + target hour), so the list is identical every time. Every row gets `source: "SIMULATED"`, an ID `SIM-{airport}-{YYYYMMDDHH}-{nn}`, and **the hour-level risk** (the same four probabilities as the card). No per-flight model.
10. Wrap everything in `try/except` → `status: "error"`. **Never raise.**

**Contract test:** `tests/test_contract.py` (see contract §8).

**`run_all.py`:** load → validate → timeline → features → baselines → train → evaluate → write reports → write model card. Fails loudly if any P0 check fails.

**→ GATE 2, then integration with the front end → GATE 3 → SUBMIT v1.**

---

## Removed from scope (mention as "next steps" in the pitch; don't build)
Per-flight risk with real flights and flight features (airline, destination weather) · calibration · ATL↔DFW transfer test · extra factors (pressure trend, storm duration, knock-on delay, temperature extremes) · 3-hour block scores · all 136 airports.

> **Honesty note for the evaluation pack:** the simulated flights all share the hour's risk. They show **how the list would look with a full schedule**. They are **not** individual predictions, and the pitch must say so.

---

## Back-end checklist before each submission
- [ ] `python run_all.py` from a fresh clone works
- [ ] V1–V10 reported. Leakage test passes. Contract test passes.
- [ ] Metrics per lead time vs B0 and B1 in `reports/metrics.md`
- [ ] At least one miss and one false alarm in `reports/failure_cases.md`
- [ ] Test set touched only for this version's final run, and noted in `decisions_log.md`
- [ ] Every trap in `05_Initial_Handover.md` §5 ticked
