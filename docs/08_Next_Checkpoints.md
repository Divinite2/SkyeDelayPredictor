# 08 · Lead Review of Checkpoints 0 / B-1 / F-1, and the Next Checkpoints

## 1. Verdicts

| Checkpoint | Verdict | One-line reason |
|---|---|---|
| **0: Contract** | ✅ **PASS, after the lead's merge fix** | Both sides built a contract, but they built **two different ones** (see 2.1). The lead merged them into one repo and one contract. Tag `cp0-contract`. |
| **B-1: Data trusted** | ✅ **PASS** | The lead re-ran `run_all.py` from scratch: V1–V10 all pass, and the time-zone chart clearly moves the peak into 13:00–18:00 in all 4 panels. Numbers match the lead's own checks. Tag `b1-data`. |
| **F-1: Screen on fake data** | ✅ **PASS with 2 small fixes** (do them in F-3) | All 11 items are delivered, and the lead re-ran the tests (37/37). The screenshots follow the display rules. Tag `f1-ui`. |

**Combined repo after the merge:** 54/54 tests pass (8 lead + 9 back end + 37 front end), and `run_all.py` passes on the merged code.

## 2. What the lead found (quick check)

### 2.1 Critical: the contract had split in two (fixed by the lead)
- Each path built its own repo with its **own `schema.json`, `config.yaml` and examples**. Neither started from the lead's `cp0-draft` repo.
- **A real bug resulted:** the back end's GREEN example had `recommendation.triggered_by = null`. The front end's schema rejects null there. **So every real GREEN forecast would have shown the "Do not rely on this tool" error card.** This would only have surfaced at integration.
- **Fix applied:**
  - one repo
  - the front end's schema and examples are authoritative
  - `triggered_by` is always a string
  - the back end's generator is patched
  - logged as L-001 to L-006 in `reports/decisions_log.md`
- **Rule from now on:** work only in the shared repo. Changes to `config/` or `contract/` go through **one joint pull request**, approved by the lead.

### 2.2 Other back-end notes
| # | Finding | Action |
|---|---|---|
| B-a | `paths.raw_csv` pointed at `/mnt/session/uploads/...`, which breaks on any other machine | Fixed by the lead: now relative (`data/raw/...`) |
| B-b | **The test period is much harder:** 17.8% severe vs 11.3% in training (summer storms) | Good catch. In B-2, also report the severe rate for **Apr–Jul 2023 and 2024**, so we can say whether this is the season (expected) or a real shift. The pitch must state it. |
| B-c | Only **69 thunderstorm + 107 shower** departures at ATL/DFW | Report every rate with its count. Don't add more storm features than those already planned. |
| B-d | Gust (`wpgt`) dropped, only 2.4% present | Correct under the 10% rule. Add it to the limitations slide. |
| B-e | Severe rate wording: 9.7% (departed > 45) vs 11.3% (incl. cancelled) | Both are right. **From now on, quote 11.3% train / 17.8% test with the definition "> 45 min late or cancelled".** |

### 2.3 Front-end notes
| # | Finding | Action (in F-3) |
|---|---|---|
| F-a | The **Check button is red** | Red means "high risk" on this screen. Make the button neutral (blue or grey). |
| F-b | The mock re-stamps times, IDs and driver text to match the request | Fine for the mock. **Must not run in `BACKEND=real`.** Add a test that real responses pass through unchanged. |
| F-c | "Thunderstorm reported: Thunderstorm (code 25)" repeats itself | Mock text only. The real labels come from the back end, so check it again at J-1. |

---

## 3. Next checkpoints

```
 BACK END:   B-2 Model honest ──► B-3 predict() ready ──┐
                                                         ├──► J-1 Integrate + SUBMIT v1 ──► FREEZE
 FRONT END:  F-2 Story & pitch ─┐                        │
             F-3 Integration-ready UI ──────────────────┘
```

### B-2: "The model is honest" (Gate 2), back end
| # | Deliverable | Pass condition |
|---|---|---|
| B2.1 | `backend/features.py` with training rows (departure × lead 3…12) | Row count reported per split. Weather joined with `merge_asof(backward)` on `obs_time_utc ≤ issue time`. 12 h purge at split edges. Training-period-only airport rate. |
| B2.2 | `wind_components()` with unit tests | Runway 80° / 180°: a wind straight down the runway gives 0 crosswind, a wind at 90° gives full crosswind, a tailwind is detected. The feature used is worst case = `wspd`. |
| B2.3 | `tests/test_leakage.py` | Deleting future weather leaves 500 sampled rows **identical**. No banned columns. Fails loudly. |
| B2.4 | Baselines B0 (climatology) and B1 (logistic regression) **before** LightGBM | Scores in `reports/metrics.md` |
| B2.5 | LightGBM 5-band delay model | P(>15) ≥ P(>30) ≥ P(>45) ≥ P(>60) on every row (asserted) |
| B2.6 | Capacity index model | RMSE vs B0 per lead time, with the number of arrivals behind each figure |
| B2.7 | Metrics table **on validation**, at 3 / 6 / 9 / 12 h | Brier at each threshold, RPS, **PR-AUC at > 45 with the base rate**, precision/recall at the RED threshold. **Beat B0 on Brier > 45 at 3 h and 6 h**, or give an honest explanation. |
| B2.8 | Smell test | No ROC-AUC > 0.95. If there is one, stop and report it. |
| B2.9 | **One test-set run** after all tuning is frozen | The same table on test, run once and logged. Include the seasonal comparison from B-b. |
| B2.10 | `reports/failure_cases.md` | One miss (GREEN predicted, severe delays happened) and one false alarm (RED predicted, flights on time), each with inputs, timestamps, the reason and a fix |
| B2.11 | `models/` plus `model_card.json` | Version, training dates, features, validation scores |

**Traps:** T1, T2, T3, T11, T12, T13, T14, T15, T16, T17.

### B-3: "`predict()` is ready", back end
| # | Deliverable | Pass condition |
|---|---|---|
| B3.1 | `backend/api.py: predict(airport, target_hour_utc, now_utc)` | Never raises. Checks in this order: on the hour → airport → data range → 3–12 h → weather within 12 h → otherwise refuse with the right code |
| B3.2 | Risk level and DO line from `config.risk_rules`, tuned **on validation** | Chosen thresholds and the false-alarm rate logged in the decisions log. `triggered_by` always a string. |
| B3.3 | WHY drivers | Top 3 from `pred_contrib` (bands 45–60 and > 60), mapped to plain words, each with its real value and `observed_at_utc ≤ now` |
| B3.4 | Confidence | From `config.confidence_rules`, with reasons |
| B3.5 | 5 simulated flights | Seeded, sorted, `SIMULATED`, probabilities equal to the hour risk |
| B3.6 | `tests/test_contract.py` on **real** output | 20 fixed requests (normal, storm, all 6 refusal codes, error) validate against `contract/schema.json`. Same request gives the same answer. |
| B3.7 | Speed | Under 1 s per call after the first load |
| B3.8 | **Demo list** → `reports/demo_cases.md` | From the **test period**: (1) a storm hour correctly flagged RED 6 h ahead, (2) a calm GREEN hour, (3) the failure case. Airport, now and target for each, handed to the front end. |
| B3.9 | `run_all.py` builds everything | Data → features → baselines → models → reports → model card in one command |

### F-2: "Story and pitch draft", front end (start now, no code)
| # | Deliverable | Pass condition |
|---|---|---|
| F2.1 | One-page user story | Traffic flow controller at ATL/DFW · today: arrival rates cut once the weather arrives · cost: holding, taxiing with engines running, cancellations · our tool: 3–12 h warning with reasons · the controller decides |
| F2.2 | Why 3–12 h | Two sentences (`01_Workflow.md` §2) |
| F2.3 | 6-part pitch outline (`01_Workflow.md` §7) | **Fits in 3 minutes.** Placeholders for the B-2 numbers. Uses `timezone_fix.png` and `severe_by_weather.png`. |
| F2.4 | Limitations and next-steps slide | ~1% sample · capacity index instead of AAR · no wind direction (worst-case crosswind) · no gust data · simulated flights · harder summer test period · the removed-scope items as next steps |

### F-3: "Integration-ready UI", front end
| # | Deliverable | Pass condition |
|---|---|---|
| F3.1 | Fix F-a | Check button not red |
| F3.2 | Fix F-b | In `BACKEND=real`, responses go to the screen untouched (test added) |
| F3.3 | Real adapter | `BACKEND=real` imports `backend.api.predict`. If the import fails, the **error card** shows, never a crash. |
| F3.4 | Loading | `@st.cache_resource` for anything heavy. The spinner shows during real calls. |
| F3.5 | Demo presets | A small "Demo cases" picker filled from `reports/demo_cases.md` (B3.8), so the pitch needs no typing |
| F3.6 | Contract tests still green | All tests pass with the merged schema |

### J-1: "Integration and SUBMIT v1", both
| # | Deliverable | Pass condition |
|---|---|---|
| J1.1 | `BACKEND=real` end to end | The 3 demo cases plus 2 h (refused), 13 h (refused) and unknown airport, all displayed correctly |
| J1.2 | Screenshots | `reports/figures/ui_real_*.png` |
| J1.3 | Fresh-clone test on a second laptop | `pip install -r requirements.txt` → `python run_all.py` → `streamlit run frontend/app.py` |
| J1.4 | Backup | Short screen recording of the demo |
| J1.5 | Trap register | All 26 ticked or explained |
| J1.6 | **Submit v1** | The lead tags `v1-submitted`. **Freeze.** |

---

## 4. Report back
Same template as before (`06_First_Checkpoints.md`, bottom). Send B-2 and F-2 first. The lead tags `b2-model`, `b3-api`, `f2-story`, `f3-ready` and `v1-submitted` as each one is approved.
