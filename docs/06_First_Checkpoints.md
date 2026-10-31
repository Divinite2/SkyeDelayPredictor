# 06 · First Checkpoints: Back End (Data Analysis) and Front End

**Two paths now.** The story and pitch work is split between them:
- **Back end** produces the evidence: the validation report, the time-zone chart, metrics and failure cases.
- **Front end** owns the user story, the screenshots and the 3-minute pitch, because they build the screen the pitch demonstrates.

**How to use this document:** each path works through its checkpoints in order. A checkpoint is **done** only when every box is ticked **and** the report (template at the bottom) has been sent to the lead. Don't start the next checkpoint until the lead replies "pass" or "pass with fixes".

---

## Checkpoint 0 (BOTH, together, before anything else)
**Goal:** both sides agree exactly what the back end will send and the front end will display, so they can then work separately without breaking each other.

- [ ] Repo created with the folder layout from `02_Instructions_Backend.md`
- [ ] `config/config.yaml` written exactly as in `04_Data_Contract.md` §2
- [ ] `contract/schema.json` written (JSON Schema **or** Pydantic. Pick one, write down which.)
- [ ] Six example responses in `contract/examples/`: `ok_red`, `ok_green`, `refused_short`, `refused_long`, `refused_airport`, `error`. **Written together**, and each has 5 simulated flights whose numbers equal the hour risk.
- [ ] Both leads have read the trap register (`05_Initial_Handover.md` §5)
- [ ] `04_Data_Contract.md` header changed to **"Agreed v1.0"** with both names ticked

**Pass condition:** the six example files validate against the schema (one command, both see it pass).

---

## BACK END: Checkpoint B-1, "The data can be trusted" (= Gate 1)
**Goal in plain words:** prove the file has been repaired before any modelling. In particular, prove the weather now lines up with the right hour.

| # | Deliverable | Pass condition (from the lead's checks of the file) |
|---|---|---|
| B1.1 | `run_all.py` runs the data stage from the raw CSV with no manual steps | Runs on a fresh clone. The raw file is never edited. |
| B1.2 | Row count and date range | 148,273 rows · 2023-01-01 → 2025-07-31 · ATL 8,415 departures / 5,429 arrivals · DFW 7,736 / 4,032 |
| B1.3 | **Time-zone repair** plus `reports/figures/timezone_fix.png` (before/after, ATL and DFW, summer and winter) | **Before:** coolest about 10:00, hottest about 20:00 local (ATL summer: 22.7 °C → 31.5 °C). **After:** peak between **13:00 and 18:00 local** for all four panels |
| B1.4 | `weather_hourly.parquet` (one row per airport per UTC hour) | Conflicting readings < 1% (lead measured about 0.07%). Overnight arrivals excluded from building the timeline. |
| B1.5 | Weather coverage figure | Hours per day with a reading at ATL and DFW reported (expected about 9–10) |
| B1.6 | Fake zeros handled | `snow` column dropped. `wpgt` zeros → null, with the non-null share reported and the keep/drop decision logged. |
| B1.7 | Range checks | Out-of-range values nulled and counted. The `wpgt` = 216 and `wspd` = 98.3 rows inspected and explained. |
| B1.8 | Weather code mapping confirmed | Severe-delay rate is highest for codes 25–27 (lead found 45% vs 9.7% in clear weather at ATL/DFW). If not, stop and tell the lead. |
| B1.9 | `flights_clean.parquet` with UTC times and delay bands | Cancelled → `gt60`. 73 cancelled-with-delay rows flagged. 0 duplicates. Arrival time = departure (UTC) + scheduled duration. |
| B1.10 | Split table | Rows and > 45 min rate per split (train / validation / test) per airport. Overall about 9.7%. |
| B1.11 | `reports/validation_report.md` | V1–V10 each marked ✅ or ❌, with a number and the action taken |

**Traps to tick at this checkpoint:** T5 (time-zone shift), T6 (our own time-zone bug), T7 (fake zeros), T9 (cancelled flights), T10 (overnight dates).

**Stop and escalate immediately if:** the temperature peak still isn't 13:00–18:00 after the repair. Everything downstream depends on it (risk R1).

---

## BACK END: Checkpoint B-2, "The model is honest" (= Gate 2)
Listed now so nothing is a surprise. Start it only after B-1 passes.

- [ ] Leakage test passes (features unchanged after deleting future weather. No banned columns.)
- [ ] Baseline B0 (climatology) and B1 (logistic regression) scored **before** LightGBM
- [ ] Brier score at > 45 min, model vs B0, at 3 / 6 / 9 / 12 h. Must beat B0 at 3 h and 6 h, **or** an honest explanation.
- [ ] P(> 15) ≥ P(> 30) ≥ P(> 45) ≥ P(> 60) in every row
- [ ] Capacity index RMSE vs B0, with the number of arrivals behind it
- [ ] One miss and one false alarm written up in `reports/failure_cases.md`
- [ ] No ROC-AUC above 0.95 (if there is one, investigate it as possible leakage)

---

## FRONT END: Checkpoint F-1, "The screen works on fake data"
**Goal in plain words:** a controller could use the screen today, even though the numbers are fake, and every possible answer from the back end is displayed correctly and safely.

| # | Deliverable | Pass condition |
|---|---|---|
| F1.1 | `streamlit run frontend/app.py` with `BACKEND=mock` | Opens with no errors on a fresh clone |
| F1.2 | Input bar | Airport (ATL/DFW, ICAO shown) · "now" date and hour defaulting to a date in Apr–Jul 2025 · target hour · **Check** button. Whole hours only. Local time with zone label, UTC shown in small grey text. |
| F1.3 | **OK card, RED** (`ok_red`) | Header colour **and** word · four risk bars with **> 45 marked "severe"** · capacity line with range · up to 3 WHY bullets with local observation times · DO text verbatim with rule ID · confidence with reasons |
| F1.4 | **OK card, GREEN** (`ok_green`) | Same layout, green, no alarming wording |
| F1.5 | **Simulated flight table** | Titled "Example flights in this hour (simulated)" · 5 rows, every one tagged SIMULATED, italic grey · the ⓘ note **always** shown |
| F1.6 | **Refused cards** (short, long, airport) | Grey, **no numbers, no bars, no colour**. Correct title. Message verbatim. |
| F1.7 | **Error card** | No numbers. "Do not rely on this tool for this request." |
| F1.8 | Safety checks | A response that breaks the schema **or** has P(> 30) < P(> 45) shows the error card (test it with a deliberately broken example) |
| F1.9 | Period warning | A yellow banner when `data_period` isn't `TEST` |
| F1.10 | Tests pass | `test_mock_matches_schema.py` · `test_render.py` (0.384 → "38%", null hidden, monotonic violation → error, **daylight-saving dates** 2024-03-10 and 2024-11-03 for ATL and DFW convert correctly, SIMULATED tag always present) |
| F1.11 | Screenshots | `reports/figures/ui_mock_*.png` for all six states |

**Traps to tick at this checkpoint:** T6 (time-zone conversion on screen), T15 (contradictory risks), T18 (simulated flights mistaken for predictions), T19 (unlabelled synthetic data), T23 (wording: "suggests; controller decides").

**Rule check:** the front end calculates nothing except formatting. If you find yourself writing a threshold or a sentence of advice, stop. It belongs to the back end.

---

## FRONT END: Checkpoint F-2, "Story and pitch draft" (in parallel with F-1, or straight after)
- [ ] One-page user story: **traffic flow controller at ATL/DFW** · today they reduce arrival rates once the weather arrives · the cost (airborne holding, taxi-out with engines running, cancellations) · our tool gives a warning 3–12 h ahead with reasons · the controller decides
- [ ] Why 3–12 h, in two sentences (`01_Workflow.md` §2)
- [ ] Pitch outline in 6 parts (`01_Workflow.md` §7), with placeholders for the back end's numbers
- [ ] A "limitations and next steps" slide: sampled data, capacity index instead of AAR, no wind direction (worst-case crosswind), simulated flights, and the list of removed items

---

## Joint checkpoint J-1, "Integration" (= Gate 3, after B-2 and F-1)
- [ ] Switch to `BACKEND=real`. Contract test passes on real output.
- [ ] Five live requests on an unseen test-period day: normal hour · storm hour · 2 h ahead (refused) · 13 h ahead (refused) · unknown airport (refused)
- [ ] Screenshots `reports/figures/ui_real_*.png`
- [ ] Fresh-clone test on a second laptop (see `03_Instructions_Frontend.md`, Step RUN)
- [ ] Short screen recording of the demo saved as a backup
- [ ] **Submit v1**, then freeze

---

## Report template (send to the lead at each checkpoint)
```
CHECKPOINT: <0 / B-1 / B-2 / F-1 / F-2 / J-1>
DONE: <item numbers ticked>
EVIDENCE: <file paths>
NUMBERS: <the pass-condition values you actually got>
DEVIATIONS: <anything different from the instructions, and why>
TRAPS TICKED: <T-numbers>
KNOWN PROBLEMS / QUESTIONS: <...>
```
