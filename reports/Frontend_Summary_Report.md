# Front-End Summary Report: Controller Dashboard

**Project:** Predictive Airport Capacity & Risk Model (Autonomous SG 2026, Airbus Track, Challenge #5)
**Track:** B, Front end (single-screen dashboard; also owns user story and pitch)
**Contract:** 04_Data_Contract (1), **AGREED v1.0**
**Stack:** Python 3.11 · Streamlit 1.66.1 · JSON Schema 2020-12 · pytest · Playwright (screenshots only)

---

## 1. Executive summary

| Checkpoint | Status | Lead verdict |
|---|---|---|
| 0: Contract (front-end share) | ✅ Delivered | PASS after the lead's merge; **the front-end schema and examples were made authoritative** |
| F-1: Screen works on fake data | ✅ 11/11 items | **PASS with 2 small fixes**, both done in F-3 |
| F-2: Story and pitch draft | ✅ Drafted, **paused by user decision** | Not yet submitted (pitch material deferred to the final stages) |
| F-3: Integration-ready UI | ✅ 6/6 items | Submitted for review |
| J-1: Integration + Submit v1 | ⏳ Waiting on the back end | Needs `backend/api.py` and `reports/demo_cases.md` |

**Overall:** the dashboard is complete on mock data and ready to connect to the real model. When the back end delivers `predict()`, switching is one setting (`BACKEND=real`). **48 automated tests pass. 14 screenshots** document every screen state.

---

## 2. What the product does (controller's view)

A traffic flow controller at ATL or DFW picks an airport and an hour **3 to 12 hours ahead** (or a ready-made demo case) and presses **Check**. One card answers:

1. **How risky** the hour is: RED / AMBER / GREEN as colour, word and shape.
2. **Chance of departure delays** over 15, 30, 45 and 60 minutes, with **>45 min marked severe**.
3. **Arrival capacity:** share of scheduled arrivals on time, with a likely range.
4. **Why:** up to 3 reasons, each with the local time it was observed.
5. **What to consider:** a fixed-rule suggestion with its rule ID; "suggestion, controller decides".
6. **Confidence**, with its reasons.
7. **Example flights**, every row tagged **SIMULATED**, with an explanatory note.

Requests outside 3–12 h, or for unknown airports, get a **grey refusal card** with no numbers. Any failure or invalid answer gets a **red-bordered error card**: "Do not rely on this tool for this request."

---

## 3. Working method

| Principle | Applied as |
|---|---|
| One feature at a time | Contract → input bar → result card → flight table → refused/error/safety → banner → tests → integration readiness |
| Explain and ask before building | Rationale and options given before each step; later, the user delegated small design calls and asked to be consulted only on deviations from instructions |
| Display, don't decide | No thresholds, advice text or risk logic in the front end; formatting only |
| Low cognitive load | One screen, no tabs or charts; only the header carries colour; neutral bars and button |
| Test once at the end of each checkpoint | No incremental runs; one consolidated test and screenshot pass per checkpoint, then fixes and a re-run |

---

## 4. Checkpoint 0: contract groundwork (front-end share)

| File | Purpose |
|---|---|
| `config/config.yaml` | Shared settings, copied exactly from contract §2 |
| `contract/schema.json` | Response rulebook (JSON Schema 2020-12): required fields per status, probabilities in [0, 1], UTC format, refusal codes, `source = "SIMULATED"`, flight-ID format |
| `contract/examples/*.json` | 6 samples: `ok_red` (ATL storm), `ok_green` (DFW calm), `refused_short`, `refused_long`, `refused_airport`, `error`; 5 simulated flights each in the OK samples |
| `frontend/mock_backend.py` | Stand-in for `predict()`, same signature, never raises, deterministic |

**Lead outcome:** the two tracks had built separate contracts. The lead merged them, made the **front-end schema and examples authoritative**, and found that the back end's GREEN example (`triggered_by = null`) would have shown the error card on every real GREEN forecast. Our schema caught this before integration.

---

## 5. Checkpoint F-1: the screen on fake data

### Deliverables
| # | Item | Result |
|---|---|---|
| F1.1 | App runs on mock | ✅ |
| F1.2 | Input bar: airport with ICAO, "now" date and hour (test-period default), target hour dropdown (+3…+12 h, user chose option A), Check, local time with zone label, UTC in grey | ✅ |
| F1.3 / F1.4 | RED and GREEN cards, full layout per instructions | ✅ |
| F1.5 | Simulated flight table, tags and note always shown | ✅ |
| F1.6 / F1.7 | Refused cards (3 titles) and error card, no numbers | ✅ |
| F1.8 | Safety: schema break or contradictory risks → error card | ✅ |
| F1.9 | Yellow banner outside the test period | ✅ |
| F1.10 | Tests incl. daylight-saving dates | ✅ 37/37 |
| F1.11 | Screenshots | ✅ 8 |

### Design decisions
- Risk badge uses **colour + word + shape** (● ▲ ■), for colour-blind users and print.
- Bars are **one neutral grey**; the severe row is darker and labelled.
- The target-hour list is built in UTC, so clock changes never skip or repeat an hour.
- **Test mode** allows a typed airport and free hour, to demonstrate refusals. Mock trigger codes: `ERR` (error) and `BAD` (broken answer).
- Missing values show "—", never 0.

### Issues found in the final run and fixed
Clipped page title · "-11 h ahead" for past hours · "ATL→ATL" routes · reasons naming the wrong hour.

### Lead verdict
**PASS with 2 fixes:** (F-a) the Check button was red; (F-b) the mock's re-stamping must never touch real answers. Both were fixed in F-3.

---

## 6. Checkpoint F-2: story and pitch (drafted, paused)

Four documents in `story/`, updated to the lead's revised requirements and agreed figures:

| File | Content |
|---|---|
| `01_User_Story.md` | Controller at ATL/DFW, status quo, cost, the tool's role, what we don't claim |
| `02_Why_3_to_12_Hours.md` | Two-sentence justification, spoken version, accuracy-per-lead-time placeholder table |
| `03_Pitch_Outline.md` | 6 sections timed to 2:45, script, demo click-script, both required charts placed, rehearsal checklist, judge Q&A |
| `04_Limitations_and_Next_Steps.md` | Slide and backup table, incl. no gust data and the harder summer test period |

**Agreed figures used:** severe = "> 45 min late or cancelled", **11.3% train / 17.8% test**, **69 thunderstorm + 107 shower** departures. 12 back-end placeholders remain. **Paused by the user** until the final stages.

---

## 7. Contract (1) alignment

| Clarification | Change |
|---|---|
| `triggered_by` always a string; GREEN = "no RED or AMBER condition met" | GREEN example updated |
| Request fields may be null on refused/error only | Schema loosened for those statuses; strict on `ok` |
| `aar_*` null or ≥ 0 | Already enforced |

A test was added for these rules.

---

## 8. Checkpoint F-3: integration-ready UI

| # | Item | How it's met |
|---|---|---|
| F3.1 | Check button not red | Theme accent set to dark blue (`.streamlit/config.toml`) |
| F3.2 | Real answers untouched | New `backend_adapter.py`; re-stamping lives only in the mock; a test proves a real answer is the same, unmodified object |
| F3.3 | Import failure → error card | Adapter returns a contract-shaped `BACKEND_UNAVAILABLE` / `BACKEND_EXCEPTION` error; verified live with no back end |
| F3.4 | Loading | Back end cached once with `@st.cache_resource`; spinner on each call; button disabled while busy |
| F3.5 | Demo presets | "Demo cases" picker from `reports/demo_cases.md`, plus 3 auto refusal presets (2 h, 13 h, unknown airport); one selection fills all fields |
| F3.6 | Tests | 48/48 pass |

---

## 9. Testing summary

| Suite | Tests | Covers |
|---|---|---|
| `test_mock_matches_schema.py` | 13 | Examples valid · flights SIMULATED and equal to the hour risk · driver times ≤ now · mock responses for 7 request types · determinism · contract (1) rules |
| `test_render.py` | 25 | Rounding (0.384 → 38%) · null → "—" · capacity text · safety → error card · severe row · SIMULATED tags · period banner · **13 daylight-saving checks** (2024-03-10, 2024-11-03, ATL and DFW) |
| `test_backend_adapter.py` | 5 | Pass-through untouched · import failure · exception · mode switch · mock still works |
| `test_demo_cases.py` | 5 | Parsing · tolerant columns · malformed rows skipped · missing file · presets give the expected states |
| **Total** | **48** | **All passing** |

**Screenshots** (`reports/figures/`), 14 in total:
- **F-1 (8):** `ui_mock_ok_red`, `ui_mock_ok_green`, `ui_mock_refused_short`, `ui_mock_refused_long`, `ui_mock_refused_airport`, `ui_mock_error`, `ui_mock_safety_broken_response`, `ui_mock_period_warning`
- **F-3 (6):** `ui_f3_preset_red`, `ui_f3_preset_green`, `ui_f3_preset_refused_2h`, `ui_f3_preset_refused_13h`, `ui_f3_preset_refused_airport`, `ui_f3_real_backend_missing`

---

## 10. Traps addressed (front-end owned or shared)

| Trap | Handling |
|---|---|
| T6: our own time-zone bug | `zoneinfo` from config; UTC line on screen; 13 DST tests |
| T7: missing shown as 0 | "—" for null, tested |
| T15: contradictory risks | Monotonic check → error card, tested with a broken fixture |
| T18 / T19: simulated data | SIMULATED tag on every row, note always shown, schema enforces the label |
| T22: demoing on training dates | Yellow banner; demo presets drawn from the test period |
| T23: replacing the controller | "suggestion, controller decides" on screen and in the story |
| T21 / T25 / T26 | Built into the pitch draft (failure case, measured vs estimated impact, timed script) |

---

## 11. All deviations from instructions (each logged in its checkpoint report)

1. The mock re-stamps sample times to the requested hour (mock only; never in real mode).
2. Test mode with typed airport and free hour; mock trigger codes `ERR` / `BAD`.
3. The mock assigns `data_period` from the config splits (to demo the banner).
4. Optional `DEMO_DATE` environment variable for the default date.
5. Shape icon on the risk badge; "suggestion, controller decides" on the DO line.
6. Auto-generated refusal presets; a labelled sample presets file in mock mode only.
7. "back end: mock|real" shown in the UTC line.

None of these moves decision logic into the front end.

---

## 12. Open items and risks

| Item | Owner | Action |
|---|---|---|
| Work is in the front-end copy, not the merged shared repo | Front end + lead | Merge via one joint pull request (doc 08 rule) |
| `demo_cases.md` format assumed (table: airport / now / target, UTC) | Back end | Confirm for B3.8 |
| Repeated WHY wording ("Thunderstorm reported: Thunderstorm (code 25)") | Back end | Check on real output at J-1 (J1.5b) |
| Button-disable while loading not yet visible (mock is instant) | Front end | Observe with the real model |
| F-2 placeholders (12) | Back end | Fill after B-2 / B-3 when pitch work resumes |

---

## 13. Next steps

**J-1, Integration and Submit v1** (when `backend/api.py` and `reports/demo_cases.md` exist):
1. Run with `BACKEND=real`; the picker fills automatically.
2. Run the 3 demo cases plus 2 h, 13 h and unknown-airport refusals.
3. Save `ui_real_*.png` screenshots.
4. Do the fresh-clone test on a second laptop.
5. Record a short backup screen recording.
6. Tick the trap register and check the WHY labels.
7. Submit v1, then freeze.

**Later:** resume F-2 (slides) · optional X1 Accept/Dismiss log · X2 reviewer details panel.

---

## 14. Repository layout

```
airport-risk-ui/
├── README.md · requirements.txt · .streamlit/config.toml
├── config/config.yaml
├── contract/schema.json · contract/examples/ (6)
├── frontend/
│   ├── app.py               single page
│   ├── render.py            pure formatting (tested)
│   ├── mock_backend.py      stand-in predict()
│   ├── backend_adapter.py   mock/real switch, safe import, pass-through
│   └── demo_cases.py        demo preset parser
├── tests/ (4 suites, 48 tests) · tests/fixtures/ (broken response, sample demo cases)
├── story/ (4 F-2 documents)
└── reports/
    ├── checkpoint_F1.md · F1_Checkpoint_Report.md · checkpoint_F2.md · checkpoint_F3.md
    ├── Frontend_Summary_Report.md (this document)
    └── figures/ (14 screenshots)
```

**Run:** `pip install -r requirements.txt` → `streamlit run frontend/app.py` (from the project root) → `python -m pytest -q`
