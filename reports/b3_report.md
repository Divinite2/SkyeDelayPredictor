# B-3 report: "`predict()` is ready"

```
CHECKPOINT: B-3
DONE: B3.0 B3.1 B3.2 B3.3 B3.4 B3.5 B3.6 B3.7 B3.8 B3.9  (all)
BASE: the lead's repo, tag b2-model (commit 0046350); decisions log has L-001 to L-013 ✅ (B3.0)
EVIDENCE: backend/api.py · backend/rules.py · backend/drivers.py · backend/simulate.py ·
          config/config.yaml (risk_rules) · tests/test_contract.py · reports/demo_cases.json + .md ·
          reports/metrics.md (rule precision/recall) · models/model_card.json (risk_rules block) ·
          reports/decisions_log.md D-024 to D-031
TESTS: 112 passed, 0 skipped (the driver-time leakage test now runs and passes)
RUN: python run_all.py → data → features → baselines → models → reports → model card → demo cases, ~1 min 50 s
TRAPS TICKED: T1 (driver times ≤ now, tested) · T15 · T18 · T19 · T20 · T22 · T23
```

## What was built
| Item | Result |
|---|---|
| B3.1 `predict()` | Never raises (the 20-request test includes broken input and a forced model failure → `status: "error"`). Refusal order: on the hour (target **and** now) → airport (IATA or ICAO, case-insensitive) → data range → 3–12 h → weather within 12 h. Features are built with **the same `Context.hour_features()` as training**. |
| B3.2 Risk rules (L-011) | Validation percentiles of hour-level P(>45), all leads (n = 11,436): **RED ≥ 0.172** (90th), **AMBER ≥ 0.117** (70th). Capacity conditions `null` = disabled. Written to `config.yaml`. `run_all.py` fails if config drifts. `triggered_by` example: `"p_gt45 >= 0.172 (validation 90th percentile)"`; GREEN: `"no RED or AMBER condition met"`. |
| B3.3 Drivers | `pred_contrib` for bands 45_60 + gt60, grouped into 13 plain-language groups. RED/AMBER: top 3 that increase risk. GREEN: top 3 that decrease it (D-026). Examples: "Evening hour · 20:00 local", "Summer peak month · July", "Busier than usual for this hour · 3.7× the usual scheduled flights (sampled)" (DFW 11 Jul 18:00 local), "Thunderstorm reported recently · 22 h before the forecast". Weather drivers carry `observed_at_utc` ≤ now (tested). Label and value never repeat each other (tested, note F-c). |
| B3.4 Confidence | Config rules + L-010: hours with no sampled departure → LOW, with reason "No scheduled flights in the sample for this hour" |
| B3.5 Simulated flights | 5 rows, seeded (crc32, identical across processes), sorted, `SIMULATED`, IDs `SIM-ATL-2025062812-01…`, probabilities equal to the hour risk |
| B3.6 Capacity (L-008) | `index` only. `index_low` / `index_high` null. `aar_note` = the agreed sentence, verbatim. |
| B3.7 Contract test + speed | 20 fixed requests (normal ×2, storm ×3, lead 12, no sampled flights, ICAO, lowercase, a training-period date, all 6 refusal codes incl. NOT_ON_THE_HOUR on "now", target in the past, a non-hub airport, an error) + determinism + forced-error test. **Every call < 1 s** (typically 0.1–0.2 s; first call ~1 s including model load). |
| B3.8 Demo cases (L-013) | Below |
| B3.9 One command | `python run_all.py` builds everything, including `demo_cases.json` (run through the real `predict()`) |

## B3.8 Demo cases (test period, 6 h ahead)
| id | Case | predict() | What happened | Honest label |
|---|---|---|---|---|
| true_red | DFW Mon 19 May 2025 20:00 local | **RED**, P(>45) 0.403, HIGH | 1 of 1 sampled departure severely delayed | Highest-risk test hour where severe delays happened. Drivers: evening hour, a thunderstorm 22 h earlier, rain at the issue time. **Not** presented as "storm correctly flagged". |
| calm | ATL Sat 5 Apr 2025 07:00 local | **GREEN**, P(>45) 0.054, **LOW** | 2 of 2 on time | Calm, dry morning. Confidence is LOW because the last reading was 7 h old (overnight gap). That's honest, but see question 2. |
| miss | ATL Sat 28 Jun 2025 08:00 local | **GREEN**, P(>45) 0.099, LOW | 2 of 2 severely delayed (+248, +83 min) | The honest failure case: the morning after a storm, last reading 7 h old |
| too_soon | DFW, 2 h ahead | refused LEAD_TOO_SHORT | — | — |
| too_far | DFW, 13 h ahead | refused LEAD_TOO_LONG | — | — |

This matches the J-1 smoke expectation: true RED → RED, failure case → GREEN, calm → GREEN.

## B3.2 Test precision/recall for the rule (reported once, D-025). Severe = "> 45 min late or cancelled"
| Lead | Flights flagged RED | Precision at RED | Recall at RED | Flagged AMBER or RED | Precision | Recall | Base rate |
|---|---|---|---|---|---|---|---|
| 3 h | 575 of 2,142 (27%) | **34%** | **51%** | 1,201 (56%) | 25% | 78% | 17.7% |
| 6 h | 519 of 2,132 (24%) | 34% | 46% | 1,164 (55%) | 25% | 77% | 17.8% |
| 9 h | 514 of 2,134 (24%) | 33% | 45% | 1,142 (54%) | 25% | 76% | 17.8% |
| 12 h | 507 of 2,125 (24%) | 32% | 43% | 1,122 (53%) | 26% | 77% | 17.7% |

Hour level, all leads: **validation RED 10.2% / AMBER 19.6% (by design); test RED 23.6% / AMBER 30.8%.** RED share by test month: April 16%, May 28%, June 22%, July 28%.

## ⚠ Finding for the lead: in summer, "RED = riskiest 10% of hours" isn't true
The thresholds come from **winter** validation data (Jan–Mar). The model correctly predicts more risk in summer (month is its top feature). So on the test period, **RED covers about 24% of hours, and AMBER or RED about 54%**. RED is still informative: precision 34% vs a 17.7% base rate (**1.9× lift**), catching about half of severe flights. But:
- The pitch line "RED = among the riskiest 10% of hours" would be **false** for the demo season. Suggested wording: "RED = above the level of the riskiest 10% of hours in our winter validation data. In summer, about one hour in four reaches it."
- Alert fatigue: in summer, more than half of hours are AMBER or RED.
- **Not changed** (L-012: no re-tuning after test, and validation is the only tuning set). Options for the lead (any change would need the lead's sign-off):
  - (a) keep it and state it honestly (my suggestion);
  - (b) percentiles per season, computed on training-period predictions (in-sample, so a more optimistic baseline);
  - (c) next-steps slide only.

## DEVIATIONS (decisions_log D-024 to D-031)
- D-024: added a `basis` key in `risk_rules` (text used in `triggered_by`). **This is a config change.** It goes in the same PR as the L-011 values. The front end doesn't read `risk_rules`.
- D-026: GREEN drivers show the factors that *decrease* risk (02 says "top 3 positive"; the contract allows "decreases").
- D-027: `generated_at_utc` = `now_utc` (deterministic responses).
- D-028: bad time format → `error`; non-string airport → UNKNOWN_AIRPORT.
- D-031: `joblib==1.6.0` added to `requirements.txt`.

## KNOWN PROBLEMS / QUESTIONS
1. **RED share in summer** (above): which option, (a), (b) or (c)? Pitch wording to be fixed in F-2 either way.
2. **The calm demo case has LOW confidence** (7 h-old reading, 07:00 local). Keep it (honest; shows the confidence logic) or pick a calm hour with HIGH confidence? Picking a different one is a selection choice, not tuning.
3. **Smoke-test `icao_code` case** in 11 §3 (KDFW, 2025-05-06 11:00 → 17:00Z, 6 h) → `ok`, airport `DFW` ✅ (covered in `test_contract.py`).
4. Front end: F-3 hasn't added the demo-preset reader yet. `reports/demo_cases.json` follows the F3.5 format exactly (`version` = model version, not "placeholder"). The ids are `true_red`, `calm`, `miss`, `too_soon`, `too_far` (the placeholder used `storm`; renamed per L-013).
5. Git: committed on branch `b3-api` in the lead's repo (based on `b2-model`). The lead merges and tags `b3-api`.
