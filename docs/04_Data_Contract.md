# 04 · Data Contract: The Rules Both Back End and Front End Must Follow

**Status:** **AGREED v1.0** (lead approval at merge `cp0-contract`). Back-end lead: ☑ · Front-end lead: ☑ · Authoritative files: `contract/schema.json` and `contract/examples/*.json` in the repo. If this document and those files ever disagree, the files win and this document gets fixed.

**v1.0 clarifications from the merge:** `recommendation.triggered_by` is **always a string**, never null (GREEN uses `"no RED or AMBER condition met"`). Request fields may be null on refused or error responses only. Optional numbers (`aar_*`) are null or ≥ 0.
**Rule:** this document is the **single source of truth** for what passes between the back end and the front end. If code and this document disagree, **the code is wrong**. Any change needs: (1) both leads to agree, (2) `schema_version` bumped, (3) the example files and the contract test updated **in the same commit**.

> **Plain-language summary:** the back end does all the thinking (cleaning, predicting, deciding the colour, choosing the recommendation). The front end only **asks** and **displays**. Both sides agree in advance on exactly how a question is asked and what an answer looks like, down to time zones, units, rounding and what "missing" means. Then neither side can quietly break the other.

---

## 1. Division of responsibility

| Decision | Owner | The other side must NOT… |
|---|---|---|
| Is the request valid? (3–12 h rule, airport known, dates in range) | **Back end** | The front end may pre-check for a nicer UX, but must still display the back end's refusal if it returns one |
| Probabilities, capacity, ranges | **Back end** | The front end never recalculates, adjusts or smooths numbers |
| Risk colour (GREEN / AMBER / RED) | **Back end** (thresholds in `config.yaml`) | The front end never applies its own thresholds |
| Recommendation text (DO line) | **Back end** (fixed rule table) | The front end never writes or changes advice |
| Confidence level | **Back end** | — |
| Simulated flights | **Back end** generates them and labels them | The front end never invents rows |
| Formatting for display (%, local time, bar lengths) | **Front end** | The back end never returns pre-formatted strings for numbers |

## 2. Shared configuration (`config/config.yaml`)

Both sides read the **same file**. Neither side hard-codes these values.

```yaml
schema_version: "1.0"
lead_time_hours: {min: 3, max: 12}          # inclusive, whole hours only
report_lead_times: [3, 6, 9, 12]            # headline metrics
delay_thresholds_min: [15, 30, 45, 60]      # P(delay > k)
severe_threshold_min: 45                     # brief requirement, highlighted
delay_bands_min: [15, 30, 45, 60]           # bands: <=15, 15-30, 30-45, 45-60, >60 (+cancelled)
data_range_utc: {start: "2023-01-01T00:00:00Z", end: "2025-07-31T23:00:00Z"}
splits:                                       # by TARGET hour, UTC
  train: {start: "2023-01-01", end: "2024-12-31"}
  validation: {start: "2025-01-01", end: "2025-03-31"}
  test: {start: "2025-04-01", end: "2025-07-31"}
airports:
  ATL: {icao: "KATL", tz: "America/New_York", runway_heading_deg: 80}
  DFW: {icao: "KDFW", tz: "America/Chicago",  runway_heading_deg: 180}
risk_rules:            # TUNED at B-3 (L-011): colour from P(>45) only; capacity_index_max null = disabled
  red:   {p_gt45_min: 0.172, capacity_index_max: null, basis: "validation 90th percentile"}
  amber: {p_gt45_min: 0.117, capacity_index_max: null, basis: "validation 70th percentile"}
confidence_rules:
  high:  {max_lead_h: 6,  max_obs_age_h: 1}
  low:   {min_lead_h: 10, min_obs_age_h: 3}   # either condition -> LOW
flight_list: {rows_shown: 5}                  # number of SIMULATED example flights per hour
nominal_arrival_rate: {ATL: null, DFW: null}  # null = show capacity as % only (no external data)
```

## 3. Universal data rules (apply everywhere: files, function calls, JSON)

| Topic | Rule | Example | Why |
|---|---|---|---|
| **Time zone** | **All times are UTC**, ISO 8601 with `Z`. Local time exists **only** on screen, converted by the front end using `airports.<code>.tz` | `"2025-06-14T18:00:00Z"` | A 5–6 h time-zone error already exists in the provided file. One convention prevents a second one. |
| **Hours** | An "hour" means the interval **[start, start + 1 h)**, identified by its start. Requests must be on the hour (`mm:ss = 00:00`). | `18:00Z` = 18:00:00–18:59:59 UTC | Avoids off-by-one errors at the edges |
| **Lead time** | `lead_time_h = target_hour_utc − now_utc`, in whole hours. Valid only if **3 ≤ lead ≤ 12**. | now 12:00Z, target 18:00Z → 6 | The agreed 3–12 h window |
| **Airport codes** | Uppercase 3-letter **IATA** codes as in the file (`ATL`). The back end also accepts ICAO (`KATL`) and converts it. Responses always use IATA. | `"ATL"` | The brief says ICAO, the data uses IATA. Accept both, store one. |
| **Probabilities** | Floats in **[0, 1]**, rounded to 3 decimals by the back end. Displayed as whole %. | `0.384` → "38%" | One rounding point |
| **Monotonicity** | Always `p_gt15 ≥ p_gt30 ≥ p_gt45 ≥ p_gt60`. The back end guarantees it. The front end **checks** it and shows an error if violated. | — | Contradictory numbers destroy trust |
| **Capacity index** | Float in [0, 1]: share of scheduled arrival slots delivered on time. Displayed as %. | `0.70` → "70% of scheduled arrivals on time" | Our stated substitute for AAR |
| **Missing values** | JSON `null`. **Never** `0`, `-1`, `""`, `NaN` or `"N/A"` for missing. | `"wpgt_kmh": null` | The provided file already stores missing gusts and snow as 0. We won't repeat that. |
| **Units** | Wind **km/h**, temperature **°C**, pressure **hPa**, precipitation **mm**, delays **minutes**. Field names carry the unit suffix. | `wspd_kmh`, `temp_c` | Prevents unit mix-ups |
| **Weather condition** | Integer `coco` code 1–27 (Meteostat convention, table in §7). The back end supplies the plain-English label. | `25` → "Thunderstorm" | Front end and back end use the same words |
| **Data source labels** | Every flight row carries `"source": "SIMULATED"` (the only allowed value in v1.0) | — | The rubric penalises unlabelled synthetic data |
| **IDs** | `"SIM-{airport}-{YYYYMMDDHH}-{nn}"` | `"SIM-ATL-2025061422-01"` | Stable keys for the table |
| **Determinism** | The same request gives the **same** response (simulated flights use a seed made from airport + target hour) | — | A demo must not change between rehearsals |

## 4. The interface: one function

The front end imports **one Python function**. There's no web server, which keeps things simpler and gives fewer failure points.

```python
# backend/api.py
def predict(airport: str, target_hour_utc: str, now_utc: str) -> dict:
    """Never raises. Always returns a dict that validates against contract/schema.json."""
```

**Mock for the front end:** `frontend/mock_backend.py` has the **same signature**. It returns responses loaded from `contract/examples/*.json`. The front end switches with one setting: `BACKEND=mock` or `BACKEND=real`.

## 5. Response format (schema v1.0)

### 5.1 Successful response: `status = "ok"`
```json
{
  "schema_version": "1.0",
  "status": "ok",
  "request": {
    "airport": "ATL",
    "target_hour_utc": "2025-06-14T22:00:00Z",
    "now_utc": "2025-06-14T16:00:00Z",
    "lead_time_h": 6
  },
  "risk_level": "RED",
  "hour_delay_risk": { "p_gt15": 0.702, "p_gt30": 0.501, "p_gt45": 0.384, "p_gt60": 0.281 },
  "capacity": {
    "index": 0.70, "index_low": 0.60, "index_high": 0.80,
    "aar_est": null, "aar_low": null, "aar_high": null,
    "aar_note": "Nominal arrival rate not configured; capacity shown as share of scheduled arrivals delivered on time."
  },
  "drivers": [
    { "label": "Thunderstorm reported", "value": "Thunderstorm (code 25)", "observed_at_utc": "2025-06-14T15:00:00Z", "effect": "increases" },
    { "label": "Strong wind (crosswind worst case)", "value": "30 km/h", "observed_at_utc": "2025-06-14T15:00:00Z", "effect": "increases" },
    { "label": "Evening peak hour", "value": "18:00 local", "observed_at_utc": null, "effect": "increases" }
  ],
  "recommendation": {
    "rule_id": "RED-1",
    "text": "Consider a pre-emptive arrival-rate reduction or ground delay programme for this hour.",
    "triggered_by": "p_gt45 >= 0.30"
  },
  "confidence": { "level": "MEDIUM", "reasons": ["Lead time 6 h", "Last weather reading 1 h before forecast"] },
  "weather_basis": { "last_obs_utc": "2025-06-14T15:00:00Z", "obs_age_h": 1 },
  "flights": [
    { "flight_id": "SIM-ATL-2025061422-01", "carrier": "DL",
      "origin": "ATL", "dest": "LGA", "sched_dep_utc": "2025-06-14T22:05:00Z",
      "source": "SIMULATED", "p_gt15": 0.702, "p_gt30": 0.501, "p_gt45": 0.384, "p_gt60": 0.281 }
  ],
  "data_period": "TEST",
  "model_version": "delayband-2025xxxx-<git_sha>",
  "generated_at_utc": "2025-06-14T16:00:02Z",
  "refusal": null,
  "error": null
}
```

**Field rules**
- `drivers`: 0–3 items, ordered by influence. `effect` is `"increases"` or `"decreases"`. `observed_at_utc` **must be ≤ `now_utc`** (that's the leakage guarantee, visible to the user), or `null` for non-weather drivers (time of day, traffic).
- `confidence.level`: `HIGH` | `MEDIUM` | `LOW`. At least one reason.
- `flights`: `flight_list.rows_shown` simulated rows, sorted by `sched_dep_utc`. Each row's four probabilities **equal** `hour_delay_risk` (there's no per-flight model in v1.0). The contract test asserts this equality, so no one can accidentally present them as individual predictions.
- `data_period`: `TRAIN` | `VALIDATION` | `TEST`, the split the **target hour** falls in. The front end shows a warning on anything except `TEST` ("the model has seen this period, so this isn't a fair test").

### 5.2 Refused: `status = "refused"`
```json
{
  "schema_version": "1.0", "status": "refused",
  "request": { "airport": "ATL", "target_hour_utc": "2025-06-14T18:00:00Z", "now_utc": "2025-06-14T16:00:00Z", "lead_time_h": 2 },
  "refusal": { "code": "LEAD_TOO_SHORT",
               "message": "18:00 UTC is only 2 h ahead. Below 3 h, current observations and controller judgement are more reliable. This tool forecasts 3 to 12 h ahead." },
  "error": null
}
```
| `refusal.code` | When |
|---|---|
| `LEAD_TOO_SHORT` | lead < 3 h (including target in the past) |
| `LEAD_TOO_LONG` | lead > 12 h |
| `NOT_ON_THE_HOUR` | minutes or seconds not zero |
| `UNKNOWN_AIRPORT` | code not in the processed data |
| `OUT_OF_DATA_RANGE` | target or now outside `data_range_utc` |
| `NO_RECENT_WEATHER` | no weather observation in the 12 h before `now_utc` (we refuse rather than guess) |

All other fields may be absent on refusal.

### 5.3 Error: `status = "error"`
```json
{ "schema_version": "1.0", "status": "error", "request": {...},
  "refusal": null, "error": { "code": "INTERNAL", "message": "Model file not found: models/delayband.txt" } }
```
The back end catches **all** exceptions inside `predict()` and returns this. The front end shows a neutral error box and **no numbers**.

## 6. Files on disk (back end internal, but fixed so Track C and the tests can rely on them)

| File | One row = | Key columns (all times UTC) |
|---|---|---|
| `data/raw/Flight_Data_With_Weather_Final.csv` | Provided file, **never edited** | — |
| `data/processed/flights_clean.parquet` | one flight | `flight_id, airport_dep, airport_arr, sched_dep_utc, sched_arr_utc, carrier, dep_delay_min, arr_delay_min, cancelled, diverted, delay_band` |
| `data/processed/weather_hourly.parquet` | one airport-hour observation | `airport, obs_time_utc, temp_c, prcp_mm, wspd_kmh, wpgt_kmh (null if 0), pres_hpa, coco, coco_label, n_source_rows, conflict_flag` |
| `data/processed/features_<split>.parquet` | one (flight, lead time) training row | `flight_id, issue_time_utc, target_hour_utc, lead_time_h, <features>, label` |
| `models/` | trained models plus `model_card.json` (version, training dates, features list, validation scores) | — |
| `reports/validation_report.md`, `reports/metrics.md`, `reports/failure_cases.md`, `reports/figures/*.png` | evidence for Track C | — |

## 7. Weather condition codes (`coco`, Meteostat convention)

| Code | Label | Group |
|---|---|---|
| 1–4 | Clear, Fair, Cloudy, Overcast | `calm` |
| 5–6 | Fog, Freezing fog | `low_visibility` |
| 7–9 | Light rain, Rain, Heavy rain | `rain` |
| 10–16 | Freezing rain, Heavy freezing rain, Sleet, Heavy sleet, Light snow, Snow, Heavy snow | `winter` |
| 17–22 | Rain shower, Heavy rain shower, Sleet shower, Heavy sleet shower, Snow shower, Heavy snow shower | `showers` |
| 23–27 | Lightning, Hail, Thunderstorm, Heavy thunderstorm, Storm | `convective` (thunderstorm) |
| 0 / anything else | not a valid code | → `null` |

> 🔧 The back end must confirm this mapping against the data (for example, codes 25–27 should show the highest delay rates). If the evidence disagrees, it raises this with the lead **before** building features on it.

## 8. Contract tests (both sides run them)

- `tests/test_contract.py`, run by the **back end**:
  - every response from `predict()` for a fixed list of 20 requests (normal, storm, all six refusal codes, error) validates against `contract/schema.json`
  - monotonicity holds
  - `observed_at_utc ≤ now_utc`
  - identical requests give identical responses
  - every flight row has `source = "SIMULATED"` and probabilities equal to `hour_delay_risk`
- `tests/test_mock_matches_schema.py`, run by the **front end**: every file in `contract/examples/` validates against the same schema.
- **Neither side merges a change while these tests fail.**

> 🔧 Write `contract/schema.json` as JSON Schema (draft 2020-12) or as Pydantic v2 models in `contract/models.py` exporting the schema. Pick one and treat it as authoritative. Required example files: `example_ok_red.json`, `example_ok_green.json`, `example_refused_short.json`, `example_refused_long.json`, `example_refused_airport.json`, `example_error.json`.
