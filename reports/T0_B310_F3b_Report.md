```
CHECKPOINT: T-0 + B3.10 + F-3b
BASE: commit c4b8916 (main; tag f3-merged = 7fe06ef + one docs commit "F-3b reassigned (L-020)"). Branch: integration.
      Commits added: 7571b1f (B3.10 + smoke script), 6be2bfd (F-3b + setup scripts)
ENVIRONMENT: Ubuntu 24.04.5 LTS (Linux x86_64), Python 3.11.17, fresh venv from requirements.txt
             Tests: 123 passed on untouched base -> 133 passed after F-3b
```

## T-0 results (run on the code as delivered, before any change)
| # | Result | Evidence |
|---|---|---|
| T0.1 | ✅ | `run_all.py` exit 0, V1–V10 (+V3b) PASS, 2 min 14 s. **123 passed** (docs/14 says 112. That was the `b3-api` count; `f3-merged` has 123, matching docs/15). |
| T0.2 | ✅ | `git diff reports/metrics.md`: no change, so the build is deterministic. Changed after rebuild: `demo_cases.json` (only `version`, which contains the git sha) and 3 PNGs in `reports/figures/` (bytes only; likely font/rendering, not data). |
| T0.3 | ✅ | `test_leakage.py`: (a) truncates weather to `obs_time_utc <= issue time` for 500 rows; (b) injects 12 h of extreme fake storm after issue time for 100 rows; features compared with `allclose`. Banned-column check loops over `delayband` **and** `capacity` models. |
| T0.4 | ✅ | D-022/D-023 + `gate2_report.md` state dev runs used `--no-test`; `run_all.py` gates `evaluate("test")` on that flag. (Only verifiable from the log; there's no run history.) |
| T0.5 | ✅ | `features_test.parquet` ATL T=2025-06-28 12:00Z lead 6: issue 06:00Z, `obs_age_h = 7.0` (last obs 23Z on 27 Jun), `coco_convective = 1`, `hours_since_storm = 7`, `storm_last_6h = 0`. |
| T0.6 | ✅ | `scripts/smoke_real.py`, `scripts/setup_and_run.sh`, `scripts/setup_and_run.bat`. The `.sh` was run end to end in a fresh `git clone` (exit 0, 133 passed, smoke OK; the final streamlit step was skipped for the headless run). The `.bat` has **not** been run, because no Windows machine was available. |
| T0.7 | ✅ | Table below (pre-B3.10). Calm showed LOW, as expected. First call 0.16 s (the model loads fast); all calls < 1 s. |
| T0.8 | ✅ | `test_contract.py`: all 6 refusal codes, determinism for all 20 requests, forced error via monkeypatched `_load`, drivers ≤ now. |
| T0.9 | ✅ | Independent: LightGBM `delayband.txt` on `features_validation.parquet`, P(>45) = bands 45–60 + >60, deduped to airport×T×lead (n = 11,436). **q90 = 0.1725, q70 = 0.1165** → 0.172 / 0.117. |
| T0.10 | ✅ | 3 random test hours (seed 2026): ATL 2025-04-10T10Z L5, ATL 2025-06-27T12Z L8, ATL 2025-07-14T17Z L12. All monotonic, 5 SIMULATED flights equal to the hour risk, driver times ≤ now. |

Smoke table, pre-B3.10:
```
true_red | RED p>45=0.40 cap=0.41 conf=HIGH | 0.16s
calm | GREEN p>45=0.05 cap=0.86 conf=LOW | 0.10s
miss | GREEN p>45=0.10 cap=0.82 conf=LOW | 0.10s
too_soon | refused LEAD_TOO_SHORT | 0.00s
too_far | refused LEAD_TOO_LONG | 0.00s
bad_airport | refused UNKNOWN_AIRPORT | 0.00s
not_on_hour | refused NOT_ON_THE_HOUR | 0.00s
out_of_range | refused OUT_OF_DATA_RANGE | 0.00s
icao_code | AMBER p>45=0.13 cap=0.75 conf=LOW | 0.13s     (airport returned as DFW)
```

## B3.10 (I-001)
- **Chosen:** ATL, now 2025-04-10T10:00Z → target 2025-04-10T16:00Z (**Thu 10 Apr 2025 12:00 local**), P(>45) **0.062**, **GREEN, confidence HIGH**. 3 of 3 sampled departures were on time.
- **Candidates:** 79 hours met rules 1–3 + 5; 65 of them also met rule 4 (HIGH/MEDIUM). **Fallback not used.**
- Label: "True GREEN: calm daytime hour, all flights on time, confidence HIGH (ATL, 6 h ahead)".
- The rule is written into `reports/demo_cases.md`. Only the calm selection plus its label/notes in `build_demo_cases()` changed. true_red, miss and the refusals are identical.

Smoke table, post-B3.10 + F-3b (also reproduced in the fresh clone):
```
true_red | RED p>45=0.40 cap=0.41 conf=HIGH | 0.14s
calm | GREEN p>45=0.06 cap=0.86 conf=HIGH | 0.09s
miss | GREEN p>45=0.10 cap=0.82 conf=LOW | 0.09s
too_soon | refused LEAD_TOO_SHORT | 0.00s
too_far | refused LEAD_TOO_LONG | 0.00s
bad_airport | refused UNKNOWN_AIRPORT | 0.00s
not_on_hour | refused NOT_ON_THE_HOUR | 0.00s
out_of_range | refused OUT_OF_DATA_RANGE | 0.00s
icao_code | AMBER p>45=0.13 cap=0.75 conf=LOW | 0.13s
```

## F-3b
| # | Result | Evidence |
|---|---|---|
| F3b.1 | ✅ | The picker shows exactly the 5 JSON labels, verbatim and in order. No auto-refusals. `ui_f3b_picker.png` |
| F3b.2 | ✅ | Tests cover missing and 8 invalid shapes. Manual check in real mode with the JSON removed: the picker is hidden, "Demo cases not available" is shown, and Check still works. Mock mode only uses `tests/fixtures/demo_cases_sample.json`. |
| F3b.3 | ✅ | The `aar_note` from the response is shown as grey text under the capacity line. `ui_f3b_true_red.png` |
| F3b.4 | ✅ | **133 passed** |
| F3b.5 | ✅ | Both screenshots taken with `BACKEND=real` (headless Chromium via Playwright, installed outside the project venv) |

## Glue files
`scripts/smoke_real.py`, `scripts/setup_and_run.sh`, `scripts/setup_and_run.bat`, plus this report.

## Issues for owners (not fixed, awaiting the lead)
1. **Back end, wording:** the true_red WHY line says "Thunderstorm reported **recently**: 22 h before the forecast". 22 h isn't "recent" for a 6 h controller forecast. Proposed: change the label wording in `backend/drivers.py`.
2. **Front end, J-1 4.1 will fail as-is:** the footer shows `Model … · generated …` but **not** "Back end: real" or a response time. The mode only appears in the grey UTC note. Proposed: add mode + measured `predict()` time to the footer.
3. **Front end:** driver observation times show only `HH:MM TZ`. An observation 22 h old shows "(16:00 CDT)" with no date, which reads as later than "now" (14:00 CDT). Proposed: show the date when it differs from the target date.
4. **Lead / back end, problem statement (updated PDF):** challenge #5 now provides `challenge5_hourly_weather_ATL_DFW.csv` with wind direction and headwind, crosswind and tailwind for runway headings (ATL 80°, DFW 180°). The repo doesn't use it: the feature is `crosswind_worst_kmh` = raw speed, and the driver says "Wind (all treated as crosswind)". "Ignoring runway directionality" is listed under "want to avoid". This file isn't in the zip. Raised for a scope decision only.
5. **Minor:** `demo_cases.json` `version` embeds the git sha at build time, so it never matches the commit that contains it, and every rebuild changes the file. Also, `run_all.py` re-renders 3 PNGs with different bytes on each machine.

## Deviations
- `smoke_real.py` has one added line (`sys.path.insert`) so it runs as `python scripts/smoke_real.py` from the repo root. Without it, `backend` isn't importable from `scripts/`. Logged in I-000.
- Rule 5 "between 08:00 and 18:00 local" was read as **inclusive** (8 ≤ local hour ≤ 18). The chosen case (12:00) is unaffected either way.
- Rule 2's "predict() returns GREEN" is checked on the live `predict()` response as well as the hour table.
- Unused `tests/fixtures/demo_cases_sample.md` was left in place rather than deleted.
- J-1 not started: it waits for the lead's tags `t0-check`, `b3-10`, `f3-ready`.
