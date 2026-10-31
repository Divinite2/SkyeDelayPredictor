# 16 · Change List for v1.1: Remove Simulated Flights, Add a Likely-Delay Range

**Requested by:** project owner. **Implemented by:** project lead (final changes before handover).
**Status:** ✅ implemented. See §4 for the verification results.

## 1. What changes and why
| # | Change | Why |
|---|---|---|
| C1 | **Remove the simulated example flight table** (back end, contract, front end, tests) | The 5 SIMULATED rows always repeated the hour's risk, so they added nothing a controller could use |
| C2 | **Add a "likely delay" range** for the chosen airport and hour: *"Most likely: under 15 min"* and *"1-in-4 chance of: more than 45 min"* | The owner wants the delay **amount** for a chosen date and time, not only percentages. It's a range, not a single number of minutes, because the model predicts delay **bands**. |
| C3 | **List of test-period dates with severe delays** (`reports/severe_delay_dates.md`), produced by a script | So testers and presenters can type in dates that really produced severe delays and see what the tool said |
| C4 | Fix 3 small issues raised by the integration expert: (a) the driver "Thunderstorm reported **recently**" also appeared for storms 22 h earlier; (b) the footer didn't show back-end mode or response time; (c) driver observation times had no date, so an observation from yesterday looked like it came after "now" | Accuracy and trust on screen |

## 2. How the likely-delay range is calculated (back end, `backend/delay_estimate.py`)
It uses the four existing probabilities P(>15), P(>30), P(>45), P(>60). **No retraining**, so all model scores stay valid.

- **Middle estimate (median band; shown as "Middle estimate", because it's the 50/50 point, not necessarily the single most common band):** the first threshold k in 15, 30, 45, 60 where P(delay > k) < 0.5 gives the band just below k:
  - P(>15) < 0.5 → "under 15 min"
  - P(>15) ≥ 0.5 but P(>30) < 0.5 → "15–30 min"
  - … · all four ≥ 0.5 → "over 60 min"
- **Bad case (1-in-4):** the largest k with P(delay > k) ≥ 0.25 → "more than k min", shown with that probability. If even P(>15) < 0.25 → "15 min or less".
- Both cut-offs (0.5 and 0.25) live in `config.yaml` → `delay_estimate`.
- **Honest note:** in this sampled data, P(>15) is under 0.5 in about 98% of test hours, so the middle estimate is nearly always "under 15 min". **The bad-case line is the informative one** (e.g. "more than 45 min" in risky hours). The screen shows the probability behind each line so the controller can judge it.

## 3. File-by-file list
| Area | File | Change |
|---|---|---|
| Config | `config/config.yaml` | `schema_version: "1.1"` · `flight_list` removed · new `delay_estimate: {typical_prob: 0.5, bad_case_prob: 0.25}` |
| Contract | `contract/schema.json` | v1.1: `flights` removed; new required `delay_estimate` object on `ok` |
| Contract | `contract/examples/*.json` | `flights` removed, `delay_estimate` added, `schema_version` 1.1 |
| Back end | `backend/delay_estimate.py` (new) | The rule in §2 |
| Back end | `backend/api.py` | No flight pattern. Adds `delay_estimate`. |
| Back end | `backend/simulate.py` | **Deleted** |
| Back end | `run_all.py` | No longer writes `models/flight_pattern.joblib` |
| Back end | `backend/drivers.py` | C4a: storm label depends on age ("…recently" only if ≤ 6 h old, otherwise "Thunderstorm earlier") |
| Front end | `frontend/render.py`, `frontend/app.py` | Flight table removed. New **LIKELY DELAY** block above the percentage bars. C4b footer: "Back end: real/mock · answered in X s". C4c: observation times show the date when it isn't the target date. |
| Front end | `frontend/mock_backend.py` | No flight re-stamping |
| Tests | `tests/*` | Flight assertions replaced by `delay_estimate` checks. New unit tests for the rule. |
| Scripts | `scripts/smoke_real.py` | Checks `delay_estimate` instead of flights |
| Scripts | `scripts/list_severe_dates.py` (new) | Writes `reports/severe_delay_dates.md` (C3) |
| Docs | `docs/04_Data_Contract.md` | v1.1 note · plus the handover set (`HANDOVER.md`, `docs/17_Developer_Guide.md`) |

## 4. Verification (done by the lead after implementation)
See the bottom of `HANDOVER.md` → "State at handover" for the test count, smoke results and screenshots.
