# Checkpoint F-3 Report: "Integration-ready UI"

**Track:** B, Front end · **Status:** ✅ All 6 items complete, submitted for lead review
**Contract:** 04_Data_Contract (1), AGREED v1.0

```
CHECKPOINT: F-3
DONE: F3.1 F3.2 F3.3 F3.4 F3.5 F3.6
EVIDENCE:
  .streamlit/config.toml                       (F3.1)
  frontend/backend_adapter.py                  (F3.2, F3.3)
  frontend/app.py                              (F3.4, F3.5 wiring)
  frontend/demo_cases.py                       (F3.5)
  tests/test_backend_adapter.py                (F3.2, F3.3: 5 tests)
  tests/test_demo_cases.py                     (F3.5: 5 tests)
  tests/test_mock_matches_schema.py            (+1 contract (1) test)
  tests/fixtures/demo_cases_sample.md
  reports/figures/ui_f3_preset_{red,green,refused_2h,refused_13h,refused_airport}.png
  reports/figures/ui_f3_real_backend_missing.png
NUMBERS: 48/48 tests pass (37 from F-1 + 11 new)
DEVIATIONS:
  1. Three refusal presets (2 h, 13 h, unknown airport ORD) are generated from the first
     demo case, so all of J1.1 can be clicked without typing.
  2. In mock mode only, if reports/demo_cases.md is missing, a clearly labelled sample
     file (tests/fixtures/demo_cases_sample.md) fills the picker. In real mode the picker
     is hidden until the back end's file exists.
  3. The UTC line now also shows "back end: mock|real", so a screenshot proves which mode it is.
  4. Contract (1) alignment: GREEN triggered_by = "no RED or AMBER condition met"; request
     fields nullable on refused/error only (strict on ok).
TRAPS TICKED: T15, T18, T19 (unchanged, re-tested) · T22 (demo presets drawn from the test period)
KNOWN PROBLEMS / QUESTIONS:
  - This work was built in the front-end working copy, not the merged shared repo
    (doc 08, 2.1). The contract/ edits and the new files need to go in via one joint pull request.
  - demo_cases.md format assumed: a markdown table with airport / now / target columns
    (UTC, Z). The parser matches columns by keyword. Please confirm with the back end for B3.8.
  - F-c ("Thunderstorm reported: Thunderstorm (code 25)") is mock text; re-check on real output at J-1.
```

## Item detail
| # | Pass condition | How it is met | Proof |
|---|---|---|---|
| F3.1 | Check button not red | Theme `primaryColor = #1f5fa8` (dark blue). Red now appears only on the RED badge and the error box. | All `ui_f3_*` screenshots |
| F3.2 | Real responses reach the screen untouched, test added | Back-end selection moved into `backend_adapter.py`; re-stamping exists only in `mock_backend.py`. Test installs a fake `backend.api` and asserts the response is the **same object** and **unmodified**. | `test_real_response_passes_through_untouched` |
| F3.3 | Real import failure → error card, never a crash | The adapter catches any import error and returns a contract-shaped `BACKEND_UNAVAILABLE` error; exceptions inside `predict()` give `BACKEND_EXCEPTION`. Both validate against the schema and render the error card. | `ui_f3_real_backend_missing.png` + 2 tests |
| F3.4 | `@st.cache_resource`; spinner during real calls | The back end is loaded once per mode via `@st.cache_resource` ("Loading model…"); "Calculating…" spinner on every call; Check disabled while busy. | Code review (`get_predict`) |
| F3.5 | "Demo cases" picker from `reports/demo_cases.md` | Picker above the inputs; choosing a case fills airport, now and target (switching to test mode automatically for refusals); the controller presses Check. Malformed rows are skipped; a missing file hides the picker. | 5 preset screenshots + 5 tests |
| F3.6 | Contract tests green with the merged schema | 48/48 pass, including a new test for the v1.0 clarifications | pytest output |

## Ready for J-1 when the back end delivers
1. `backend/api.py` in the shared repo → start with `BACKEND=real streamlit run frontend/app.py`
2. `reports/demo_cases.md` (B3.8) → the picker fills automatically
3. Then: J1.1 five requests · J1.2 `ui_real_*.png` · J1.3 fresh-clone test · J1.4 recording · J1.5b WHY label check
