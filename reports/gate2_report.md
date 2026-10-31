# Gate 2 report: Checkpoint B-2, "The model is honest"

```
CHECKPOINT: B-2 (Gate 2)
DONE: B2.1 B2.2 B2.3 B2.4 B2.5 B2.6 B2.7 B2.8 B2.9 B2.10 B2.11 B2.12  (all 12)
EVIDENCE: reports/metrics.md · reports/failure_cases.md · models/model_card.json ·
          models/delayband.txt · models/capacity.txt · models/baselines.joblib · models/context.joblib ·
          data/processed/features_{train,validation,test}.parquet · cap_features_*.parquet ·
          tests/test_leakage.py · tests/test_wind.py · tests/test_monotonic.py ·
          reports/decisions_log.md (D-013 to D-023)
TESTS: 24 passed, 1 skipped (the driver-time check turns on in B-3 when api.py exists)
TRAPS TICKED: T1 T2 T3 T11 T12 T13 T14 T15 T16 T17
```

## Gate 2 pass conditions
| Condition | Result |
|---|---|
| (a) Leakage test | ✅ 500 rows identical after deleting future weather. 100 rows identical after **injecting a fake extreme storm** after t. No banned columns in the feature list or in either trained model. |
| (b) Beats B0 on Brier > 45 at 3 h and 6 h | ✅ Validation **and** test, at every headline lead time. The 90% bootstrap interval excludes 0 in all 8 cases. |
| (c) Monotonic P(>15) ≥ … ≥ P(>60) | ✅ Asserted on every row of all three splits (band model, so it holds by construction) |
| Smell test (no ROC-AUC > 0.95) | ✅ Maximum 0.731 (ATL, test). Plausible for weather 3–12 h ahead. |

## NUMBERS (overall, ATL + DFW). Severe = "> 45 min late or cancelled"

**Brier score at > 45 (lower is better)**
| Lead | Val B0 | Val B1 | **Val LGBM** | Test B0 | Test B1 | **Test LGBM** | Test n (severe) |
|---|---|---|---|---|---|---|---|
| 3 h | 0.1077 | 0.1033 | **0.1029** | 0.1409 | 0.1340 | **0.1364** | 2,142 (379) |
| 6 h | 0.1076 | 0.1037 | **0.1035** | 0.1416 | 0.1371 | **0.1385** | 2,132 (379) |
| 9 h | 0.1068 | 0.1032 | **0.1030** | 0.1414 | 0.1384 | **0.1385** | 2,134 (379) |
| 12 h | 0.1073 | 0.1038 | **0.1042** | 0.1409 | 0.1383 | **0.1386** | 2,125 (376) |

**Severe detection, test (base rate 17.7%)**
| Lead | PR-AUC B0 | PR-AUC B1 | **PR-AUC LGBM** | ROC-AUC LGBM | RED flags (P(>45) ≥ 0.30) | Precision | Recall |
|---|---|---|---|---|---|---|---|
| 3 h | 0.263 | 0.347 | **0.360** | 0.712 | 46 | 52% | 6.3% |
| 6 h | 0.263 | 0.320 | **0.332** | 0.696 | 52 | 50% | 6.9% |
| 9 h | 0.264 | 0.312 | **0.334** | 0.695 | 53 | 51% | 7.1% |
| 12 h | 0.264 | 0.305 | **0.325** | 0.691 | 45 | 44% | 5.3% |

**Capacity index RMSE (airport-hour, weighted by arrivals)**, test: B0 0.413 → LGBM **0.406** at 3 h (n = 1,348 arrivals in 1,172 hours). The same small gain shows at every lead.
Validation: 0.392 → 0.383.

**Seasonal comparison (note B-b), severe rate in Apr–Jul, ATL + DFW:** 2023 13.5% (n = 2,089) · 2024 **17.0%** (n = 2,217) · 2025 **17.8%** (n = 2,147).
→ The hard test period is **mostly the season**. 2024 was almost as bad. 2023 was milder, which pulls the training average down.

## Honest reading of the results (for the lead and the pitch)
1. **The model beats climatology, but by a small margin:** about 3–4% lower Brier at > 45 and +0.06–0.10 PR-AUC. The bootstrap says the gain is real (not noise) at every lead time.
2. **Logistic regression (B1) is as good as LightGBM.** It's slightly better on test Brier at every lead (e.g. 0.1340 vs 0.1364 at 3 h). LightGBM is better on PR-AUC and ROC-AUC (ranking). With ~12.5k training flights and a weak signal, the trees have little to exploit: early stopping chose **19 trees**. I kept LightGBM as the main model because the instructions require it (D3, D4) and it ranks severe hours best. If you prefer B1, that's a decision for you.
3. **Accuracy barely drops between 3 h and 12 h.** Most of the model's information is **not weather**. Month, time of day, day of week and traffic carry **~58%** of the gain. Pressure (11%), temperature (7%) and wind (~10%) make up most of the rest. **The storm features (`storm_last_6h` and its two interactions, `coco_convective`) get 0% of the gain.** With only 69 storm departures and `min_data_in_leaf` = 400 (chosen on validation), the trees never split on them. With ~9–10 weather readings per day in a ~1% sample, the weather signal 3+ h ahead is weak. So **our numbers don't prove the 12 h cut-off**; it rests on the operational reasoning in 01 §2. That's the "report it honestly" case of Gate 2. It also means **a storm hour won't necessarily come out RED**, which matters for the B3.8 demo case ("storm hour correctly flagged RED"). I'll search the test period for one and report honestly if there isn't one.
4. **The RED threshold is too strict for this model.** At P(>45) ≥ 0.30, LightGBM flags about 2% of hours, with ~50% precision but only ~6–7% recall. Tuning the RED/AMBER thresholds on validation is B3.2. The capacity conditions (≤ 0.60 / ≤ 0.80) sit near the 72–78% base rate, so the starting rules put about half the hours into AMBER.
5. **The capacity range is too wide to help.** The 10th–90th percentile of validation errors is about −0.78 to +0.28 at every lead, because an "hour" usually has a single sampled arrival (observed index 0 or 1). With the 02 rule, almost every range comes out as roughly [0, 1]. For B-3 I'd keep the rule as instructed and label the range "very uncertain (sampled data)". The alternative needs your approval.

## Failure cases (`reports/failure_cases.md`), 6 h ahead
| Set | Type | Case | Why |
|---|---|---|---|
| Validation | Miss | ATL 2025-02-13 17:00 local, GREEN (P(>45) = 0.08); 2 of 2 flights severe (+963, +174 min) | Weather was benign before and after. Non-weather cause (aircraft/crew, upstream), outside the inputs. |
| Validation | False alarm | DFW 2025-03-28 18:00 local, RED (P(>45) = 0.36, capacity 0.53); 1 of 1 on time | Rain at the issue time, cleared within an hour. No forecast data to show the clearing. |
| Test | Miss | ATL 2025-06-28 08:00 local, GREEN (P(>45) = 0.10); 2 of 2 severe (+248, +83 min) | **The last reading was 7 h old and showed a thunderstorm** at 23Z the evening before. That's just outside the 6 h storm window, so `storm_last_6h` = 0 (the knock-on morning after a storm). Shows the cost of sparse readings, and of the storm-duration / knock-on features that were cut from scope. |
| Test | False alarm | DFW 2025-04-02 17:00 local, RED (P(>45) = 0.42, capacity 0.46); 1 of 1 on time | Rain and falling pressure (1001 hPa) at the issue time, cleared afterwards. |

## DEVIATIONS (all in decisions_log)
- D-013: the lead's merge fixes are recreated in this copy, because the merged repo wasn't uploaded. **The front end's `schema.json` wins at the merge.**
- D-014: smoothing in `rel_volume` (+0.5). D-015: B0 shrinkage. D-016: rows without recent weather dropped (mirrors the refusal rule).
- D-018: validation was used for both early stopping and the 20-configuration selection, so validation scores are slightly optimistic. Test is the clean figure.
- D-019: leakage tolerance 1e-9, plus the injected-storm test. D-021: bootstrap and feature-importance table added.
- D-023: **the test set was evaluated once, after the freeze.** All development runs used `--no-test`.

## KNOWN PROBLEMS / QUESTIONS
1. **Main model:** keep LightGBM (required, best at ranking), or switch to B1 (best Brier on test)? I suggest keeping LightGBM and showing B1 in the evidence.
2. **Capacity range:** OK to ship the 02 rule with an "uncertain" label (point 5)?
3. **Pitch wording:** the 3–12 h window is justified operationally, not by a drop in accuracy (point 3). F-2 should use this wording.
4. Hours with **no sampled departure** (sched_deps = 0) never appear in training, but `predict()` must answer them in B-3. I'll fill traffic features from the schedule, which is 0 for such hours, and flag LOW confidence there unless you prefer otherwise.
