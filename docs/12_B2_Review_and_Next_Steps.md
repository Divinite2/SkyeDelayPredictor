# 12 · Lead Review of B-2, Decisions for B-3, and Next Steps

## 1. Verdict: B-2 ✅ PASS (tag `b2-model`)

**What the lead checked:**
- Merged the B-2 code into the shared repo.
- Re-ran `python run_all.py` from scratch, which takes about 2 minutes. **Every metric reproduced exactly** (`reports/metrics.md` is identical to the worker's). Gate checks: beats B0 at 3 h ✅ and 6 h ✅, max ROC-AUC 0.731 ✅, monotonic ✅.
- Full test suite on the merged repo: **69 passed, 1 skipped**. The skipped one is the driver-time test, which switches on in B-3.

**Why it passes:** all three Gate 2 conditions are met, the test set was used once (D-023), and the report is **honest about weak results**. That's exactly what the judges reward ("Honest evaluation", 20%).

**What the results actually say, in plain words:**
| Finding | Meaning for us |
|---|---|
| The model beats the simple baseline by a **small but real** margin (Brier 3–4% better, PR-AUC +0.06–0.10, bootstrap-confirmed) | We can honestly claim "better than the historical average", but not "much better" |
| **Logistic regression is about as good** (slightly better Brier on test, worse at ranking) | Show it in the evidence. That's honest and costs nothing. |
| Accuracy is almost **flat from 3 h to 12 h**, and **~58% of the model's signal is season, time of day and traffic**. Storm features got **0%**. | In this ~1% sample with ~9–10 readings per day, weather 3+ h ahead says little. **The 3–12 h window is justified operationally, not by our numbers.** The pitch must say so. |
| The test period is hard mostly because of **season** (Apr–Jul: 2023 13.5%, 2024 17.0%, 2025 17.8%) | The test is fair. Say "summer storm season". |
| Best failure case: **ATL 2025-06-28 08:00**, a miss the morning after a thunderstorm, when the last reading was 7 h old | This is our pitch's failure story. It shows sparse readings and the knock-on effect we cut from scope. |

**Process problem (again):** the back end worked in its **own old copy** (D-013), not the shared repo. That's partly the lead's fault, because the merged repo didn't reach them. The lead has merged it again. **From now on, every worker starts from the lead's latest zip/bundle, or from `AutonomousSGHack` on GitHub. Uploads based on an older copy will be sent back.**

---

## 2. Lead decisions (answers to the back end's four questions, plus three more)

| # | Question | Decision | Why |
|---|---|---|---|
| L-007 | Main model: LightGBM or logistic regression (B1)? | **Keep LightGBM.** Report B1 next to it in `metrics.md` and the pitch. | Best at ranking risky hours (PR-AUC), which is what RED/AMBER needs. Brier difference is tiny. Switching now costs time and adds no score. |
| L-008 | Capacity range ≈ [0, 1] | **Don't show a range.** Return `index_low` and `index_high` as **null**, with `aar_note`: *"Range not shown: the sample has about one arrival per hour, too few for a meaningful interval."* | A [0, 1] range is meaningless and looks broken. The schema already allows null, and the front end already hides the range when it's null. |
| L-009 | Pitch wording on 3–12 h | **Approved:** "Window chosen for operational reasons. Our accuracy barely changes across it, because in this sampled data most of the signal is season, time of day and traffic, not weather." | Honest, and it pre-empts the judges' question |
| L-010 | Hours with no sampled departure | **Approved:** traffic features from the schedule (0), confidence **LOW**, reason "No scheduled flights in the sample for this hour" | The model never trained on such hours |
| L-011 | **Risk colours** (new) | **Colour is decided by delay risk only.** Remove the capacity conditions from the rules (`capacity_index_max: null`, null means disabled). **Tune on validation:** RED = P(> 45) at or above the validation **90th percentile** (riskiest 10% of hours). AMBER = at or above the **70th percentile** (next 20%). GREEN = the rest. Write the chosen values into `config.yaml` and log them. Report test precision and recall for this rule once. | The capacity model is barely better than the baseline (RMSE 0.406 vs 0.413), and its 0.60/0.80 conditions turned about half of all hours AMBER. Percentiles are easy to explain to a controller ("RED = among the riskiest 10% of hours"). |
| L-012 | **No re-tuning** (new) | Don't lower `min_data_in_leaf` or change features to make storms count. Test scores have been seen, so any change now would be tuning on the test set (T12). | Put it on the "next steps" slide: more data or full schedules would let the storm features work |
| L-013 | **Demo cases** (new; B3.8 updated) | We may not have a storm hour flagged RED. Demo cases are: (1) **a true RED**, the highest-P(> 45) test hour where severe delays actually happened, whatever the weather; (2) **a true GREEN** calm hour; (3) **the failure case** ATL 2025-06-28 08:00 local (target) at 6 h ahead; (4) refused 2 h; (5) refused 13 h. Labels must say what each is **honestly**. Never "storm correctly flagged" unless it's true. | Honest demo |

**Config change process for L-011:** the back end makes the change in `config/config.yaml` together with the code that treats `null` as disabled (`evaluate.py` currently compares against these values, so changing the config alone would break it). One pull request, the lead approves, and the front end is told (the front end doesn't read `risk_rules`, so no front-end change is needed).

---

## 3. Next steps: 4 checkpoints left, plus one parallel check

```
 BACK END:  B-3 predict() ready ───────────────────────────┐
 FRONT END: F-3 integration-ready UI (+F3.7) ──────────────┼──► J-1 integrate, test, SUBMIT v1 ──► FREEZE: F-2 pitch
 TESTING:   T-0 independent check of B-2 + J-1 prep ───────┘
```

### B-3: "`predict()` is ready", back end (updated items in bold)
| # | Deliverable | Pass condition |
|---|---|---|
| B3.0 | **Start from the lead's latest repo** (tag `b2-model`) | The decisions log contains L-001 to L-013 |
| B3.1 | `backend/api.py: predict()` | As in `08_Next_Checkpoints.md`. Never raises. Refusal order unchanged. |
| B3.2 | **Risk rules per L-011** | Percentile thresholds from validation written into `config.yaml`. Capacity conditions null. Test precision and recall for the rule reported once. |
| B3.3 | Drivers | Top 3 by contribution, in **plain words for non-weather drivers too** (e.g. "Summer peak month (July)", "Evening hour", "Busier than usual for this hour"). Weather drivers carry `observed_at_utc ≤ now`. No repeated wording (note F-c). |
| B3.4 | Confidence | Config rules **plus L-010**: LOW when there are no sampled flights in the hour |
| B3.5 | Simulated flights | Unchanged |
| B3.6 | **Capacity per L-008** | `index_low` / `index_high` null, with the agreed `aar_note` |
| B3.7 | Contract test on real output, speed under 1 s | Unchanged. The skipped driver-time test now runs and passes. |
| B3.8 | **Demo cases per L-013** | `reports/demo_cases.json` (format in `10_F3_Instructions.md` F3.5) plus `reports/demo_cases.md` with one honest line per case |
| B3.9 | `run_all.py` builds everything, including `demo_cases.json` | Fresh clone → one command |

### F-3: integration-ready UI, front end (one item added)
Everything in `10_F3_Instructions.md`, **plus:**
| # | Deliverable | Pass condition |
|---|---|---|
| **F3.7** | When `capacity.index_low` / `index_high` are null, show `aar_note` **as visible grey text** under the capacity line, not only as a hover tooltip | Screenshot shows "Range not shown: …". The text comes from the response, not hard-coded. |

**Start from the lead's latest repo** (tag `b2-model` or later).

### T-0: independent check of B-2, testing expert (now, in parallel)
Do this while B-3 and F-3 are being built. **Read-only: report findings, don't change model code.**
| # | Check | Pass |
|---|---|---|
| T0.1 | Clean clone of the latest repo on **your** machine → `pip install -r requirements.txt` → `python run_all.py` → `python -m pytest -q` | Exit 0 · 69 passed, 1 skipped (or more once B-3 lands) |
| T0.2 | Compare `reports/metrics.md` with the lead's copy | Numbers identical (deterministic). If anything differs, report it. |
| T0.3 | Read `tests/test_leakage.py` | Confirm it really deletes future weather **and** injects a fake future storm, and that the banned-column check covers both models |
| T0.4 | Check `reports/decisions_log.md` D-023 and the run flags | The test set was evaluated only by the final run. Development used `--no-test`. |
| T0.5 | Spot-check the failure case ATL 2025-06-28 in `data/processed/features_test.parquet` | Last observation about 7 h old, thunderstorm code at about 23Z the day before, `storm_last_6h = 0` |
| T0.6 | Prepare J-1 | Draft `scripts/smoke_real.py` and `scripts/setup_and_run.sh`/`.bat` from `11_J1_Integration_Instructions.md`, ready to run once B-3 lands |

**Report:** short, using the usual template, `CHECKPOINT: T-0`.

### J-1: integrate, test, submit v1
`11_J1_Integration_Instructions.md`, with two updates:
- Smoke-test expectation: the **true RED** demo case gives `RED`, the **failure case** gives `GREEN` (that's the honest miss), and the calm case gives `GREEN`.
- Capacity line shows **no range**, plus the grey note (L-008, F3.7).

### F-2: story and pitch (last, during the freeze)
As in `08_Next_Checkpoints.md`, **plus** these required lines:
- "Better than the historical average, by a small but statistically real margin (Brier −3–4%). A simple logistic regression does about as well. We show both."
- The L-009 wording on the 3–12 h window.
- Failure case: ATL 2025-06-28, the morning after a storm, last reading 7 h old.
- Next steps: full schedule data, wind direction, TAF forecasts, storm-duration and knock-on features.
