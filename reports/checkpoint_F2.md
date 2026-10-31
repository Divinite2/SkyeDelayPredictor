# Checkpoint F-2 Report: "Story and pitch draft"

**Track:** B, Front end (owns user story C1 and pitch C4)
**Status:** ✅ All 4 items drafted against the updated pass conditions in `08_Next_Checkpoints.md`
**Contract:** aligned to **04_Data_Contract (1), AGREED v1.0**

```
CHECKPOINT: F-2
DONE: F2.1 user story · F2.2 why 3–12 h · F2.3 pitch outline (6 parts) · F2.4 limitations slide
EVIDENCE:
  story/01_User_Story.md
  story/02_Why_3_to_12_Hours.md
  story/03_Pitch_Outline.md
  story/04_Limitations_and_Next_Steps.md
NUMBERS: pitch planned at 2:45 (~400 words, 15 s buffer).
         Only lead-agreed figures quoted: severe = "> 45 min late or cancelled",
         11.3% train / 17.8% test; 69 thunderstorm + 107 shower departures (ATL/DFW);
         gust present in 2.4% of rows; ~1% flight sample.
         All model metrics left as [BE: …] placeholders (12 in the pitch).
DEVIATIONS:
  1. Added a timing plan, demo click-script, rehearsal checklist and prepared judge Q&A
     to the pitch outline (beyond the 6-part outline asked for).
  2. Added a "proof by lead time" placeholder table to the 3–12 h document.
  3. The earlier 9.7% → 45% figures were removed (old definition, note B-e). The
     thunderstorm-specific severe rate is now a [BE] placeholder until severe_by_weather.png
     is produced with the agreed definition.
TRAPS TICKED: T21 (failure case built in), T22 (demo date must be in the test period),
              T23 (suggests / controller decides), T25 (measured vs estimated kept separate),
              T26 (timed script under 3 min)
KNOWN PROBLEMS / QUESTIONS:
  - Needs from the back end: thunderstorm severe rate (agreed definition, n = 69);
    the seasonal comparison for Apr–Jul 2023/2024 (note B-b); Brier per lead time vs
    baseline; capacity RMSE vs baseline; one miss and one false alarm; hit rate and
    false-alarm rate; demo cases (B3.8).
  - Slides not yet designed (content is ready). Confirm the format wanted.
```

## Checklist against 08_Next_Checkpoints.md
| # | Pass condition | Where | ✅ |
|---|---|---|---|
| F2.1 | Controller at ATL/DFW · rates cut once weather arrives · cost: holding, taxiing with engines running, cancellations · 3–12 h warning with reasons · controller decides | 01 | ✅ |
| F2.2 | Why 3–12 h in two sentences | 02 (top) | ✅ |
| F2.3 | Fits in 3 minutes | 03 (timing plan, 2:45) | ✅ |
| F2.3 | Placeholders for the B-2 numbers | 03 (`[BE: …]`) | ✅ |
| F2.3 | Uses `timezone_fix.png` and `severe_by_weather.png` | 03 (Slide 2 inset, Slide 1 inset) | ✅ |
| F2.3 | Severe rates with the agreed definition; storm count 69 | 01, 03, 04 | ✅ |
| F2.4 | ~1% sample · capacity index · no wind direction · **no gust data** · simulated flights · **harder summer test period** · removed scope as next steps | 04 | ✅ |

## Contract (1) alignment, done alongside F-2
| Clarification | Front-end change |
|---|---|
| `triggered_by` always a string; GREEN uses "no RED or AMBER condition met" | `example_ok_green.json` updated |
| Request fields may be null on refused/error only | `schema.json`: request fields nullable in general, strict (string / UTC / integer) on `ok` |
| `aar_*` null or ≥ 0 | Already enforced; unchanged |

Per the lead's rule (doc 08, section 2.1), changes to `contract/` go through one joint pull request in the shared repo. These edits align this working copy with the already-agreed v1.0; they need to be checked against the merged repo's files, which take priority. Tests will be re-run in F-3 (F3.6).
