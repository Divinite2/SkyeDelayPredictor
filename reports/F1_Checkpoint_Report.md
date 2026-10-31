# Checkpoint F-1 Report: "The screen works on fake data"

**Project:** Predictive Airport Capacity & Risk Model (Autonomous SG 2026, Airbus Track, Challenge #5)
**Track:** B, Front end (controller dashboard)
**Checkpoint:** F-1 (front-end share of Checkpoint 0 included)
**Status:** ✅ All 11 deliverables complete, submitted for lead review
**Stack:** Python 3.11 · Streamlit 1.66.1 · JSON Schema (draft 2020-12) · pytest

---

## 1. Summary

The single-screen controller dashboard is built and working on mock data that follows the data contract exactly. A controller can enter an airport and an hour and, in one click, see delay risk, arrival capacity, reasons, a suggested action, confidence and example flights. Every possible back-end answer (two risk levels, three refusal types, an error and two invalid-data cases) has been displayed and screenshotted. All 37 automated tests pass.

The front end calculates nothing except formatting. Risk colour, advice, confidence and refusals all come from the back end's response, as the contract requires.

---

## 2. Report (lead template)

```
CHECKPOINT: F-1
DONE: F1.1 F1.2 F1.3 F1.4 F1.5 F1.6 F1.7 F1.8 F1.9 F1.10 F1.11
EVIDENCE: see section 5
NUMBERS: 37/37 tests passed · 8 screenshots · 6/6 example files validate
DEVIATIONS: 7, all explained in section 7
TRAPS TICKED: T6, T15, T18, T19, T23
KNOWN PROBLEMS / QUESTIONS: see section 9
```

---

## 3. Approach

| Principle | How it was applied |
|---|---|
| Work feature by feature | Built in order: groundwork → input bar → result card → flight table → refused/error/safety states → warning banner → tests → single final run |
| Display, don't decide | No thresholds, advice text or colour logic in the front end. Colour is a fixed lookup from the back end's `risk_level` word. |
| Low cognitive load for controllers | One screen, no tabs or charts. Card order follows the instructions. The header is the only coloured element; bars are neutral grey. |
| Test once at the end | No incremental runs. One consolidated test and screenshot pass, then fixes and a re-run. |
| Don't wait for the model | Built against a mock with the same signature as the future `predict()`; switched with `BACKEND=mock|real`. |

---

## 4. Deliverables vs pass conditions

| # | Deliverable | Pass condition | Result |
|---|---|---|---|
| F1.1 | App runs on mock | `streamlit run frontend/app.py` opens with no errors | ✅ Launched headless, HTTP 200, all states rendered |
| F1.2 | Input bar | Airport (ICAO shown) · "now" date + hour defaulting to Apr–Jul 2025 · target hour · Check · whole hours · local time with zone · UTC in grey | ✅ Defaults to 14 Jun 2025 12:00 local. Target dropdown lists only +3 to +12 h. UTC line under the inputs. |
| F1.3 | OK card, RED | Colour **and** word · 4 bars, >45 marked "severe" · capacity with range · ≤3 WHY with local times · DO verbatim + rule ID · confidence + reasons | ✅ `ui_mock_ok_red.png` |
| F1.4 | OK card, GREEN | Same layout, green, no alarming wording | ✅ `ui_mock_ok_green.png` |
| F1.5 | Simulated flight table | Correct title · 5 rows tagged SIMULATED, italic grey · ⓘ note always shown | ✅ Visible in both OK screenshots |
| F1.6 | Refused cards | Grey, no numbers/bars/colour · correct title · message verbatim | ✅ `ui_mock_refused_short/long/airport.png` |
| F1.7 | Error card | No numbers · "Do not rely on this tool for this request." | ✅ `ui_mock_error.png` |
| F1.8 | Safety checks | Schema break **or** P(>30) < P(>45) → error card | ✅ `ui_mock_safety_broken_response.png` + 2 unit tests |
| F1.9 | Period warning | Yellow banner when `data_period` ≠ TEST | ✅ `ui_mock_period_warning.png` |
| F1.10 | Tests pass | Schema test + render tests incl. DST dates | ✅ 37 passed, 0 failed |
| F1.11 | Screenshots | `ui_mock_*.png` for all six states | ✅ 8 saved (six required + 2 extra) |

---

## 5. Files produced

```
airport-risk-ui/
├── README.md                          how to run, test mode guide
├── requirements.txt                   pinned Streamlit + dependencies
├── config/config.yaml                 shared settings, copied exactly from contract §2
├── contract/
│   ├── schema.json                    authoritative response contract (JSON Schema 2020-12)
│   └── examples/                      6 example responses
│       ├── example_ok_red.json        ATL, 14 Jun 2025, thunderstorm, 6 h ahead
│       ├── example_ok_green.json      DFW, 20 May 2025, clear, 4 h ahead
│       ├── example_refused_short.json
│       ├── example_refused_long.json
│       ├── example_refused_airport.json
│       └── example_error.json
├── frontend/
│   ├── app.py                         the single page
│   ├── render.py                      pure formatting functions (unit-tested)
│   └── mock_backend.py                stand-in for backend.api.predict
├── tests/
│   ├── test_mock_matches_schema.py    contract tests (12)
│   ├── test_render.py                 display tests (25)
│   └── fixtures/broken_monotonic.json deliberately invalid response
└── reports/
    ├── checkpoint_F1.md               short-form report
    ├── F1_Checkpoint_Report.md        this document
    └── figures/ui_mock_*.png          8 screenshots
```

**Schema choice:** JSON Schema rather than Pydantic, so both tracks can read and validate it without extra libraries. It enforces:
- the required fields for each status (ok / refused / error);
- probabilities in [0, 1];
- UTC timestamp format with `Z`;
- the allowed refusal codes;
- `source = "SIMULATED"` and the `SIM-{airport}-{YYYYMMDDHH}-{nn}` ID format on every flight row.

---

## 6. Feature detail

### 6.1 Input bar
- **Airport:** dropdown, "ATL (KATL)" / "DFW (KDFW)", read from config.
- **Now:** local date and whole hour. The default date is in the test period.
- **Target hour (option A, chosen by the user):** dropdown of now + 3 … now + 12 h, shown as "Sat 14 Jun 18:00 EDT · +6 h". The list is built in UTC, so a daylight-saving change can't skip or repeat an hour.
- **Test mode** (checkbox): free airport code and free target date/hour, to demonstrate refusals. The back end still enforces every rule.
- **UTC line:** exact `now_utc` and `target_hour_utc` sent to `predict()`, so judges can verify the conversion.
- **Check:** one click = one `predict()` call. Shows a "Calculating…" spinner, and the button is disabled while waiting.

### 6.2 Result card (status "ok")
| Section | Display rule applied |
|---|---|
| Header | Airport + ICAO, local hour range with zone, lead time. Risk badge shows colour + word + shape (● RED / ▲ AMBER / ■ GREEN), so it works for colour-blind users and in print. |
| Delay risk | Four bars; labels from `config.delay_thresholds_min`; whole % with half-up rounding; the >45 row (from `severe_threshold_min`) is bold, darker and tagged "◀ severe". |
| Capacity | "X% of scheduled arrivals on time (likely L–H%)". Arrivals/h only if `aar_est` isn't null. `aar_note` shown as a hover tooltip. Hidden entirely if the index is null. |
| WHY | Up to 3 drivers: label, value, and observation time in local time. No time shown for non-weather drivers. |
| DO | Recommendation text verbatim; rule ID and trigger in small grey text. Heading reads "suggestion, controller decides". |
| Confidence | Level in bold; reasons joined with " · ". |
| Flights | Title "Example flights in this hour (simulated)"; rows italic grey in the order received; SIMULATED tag on every row; ⓘ note always shown; table hidden if the list is empty. |
| Footer | Model version and generation time in small grey text. |

### 6.3 Other states
| State | Display |
|---|---|
| Refused | Neutral grey card. Title mapped from the code ("Too soon to forecast", "Too far ahead to forecast", "Airport not in data", "Cannot forecast this request"). Message verbatim. No numbers, bars or colour. |
| Error | Red-bordered box: "The forecast could not be produced. Do not rely on this tool for this request." plus the technical message in small text. No numbers. |
| Safety fallback | Any schema violation or non-monotonic risk → error card. Contradictory numbers are never displayed. |
| Period warning | Yellow banner: "This date is in the model's TRAIN/VALIDATION period, so it isn't a fair test. Use Apr–Jul 2025 for honest demos." |

### 6.4 Mock back end
Same signature as `backend.api.predict(airport, target_hour_utc, now_utc)`; never raises.

| Input | Returns |
|---|---|
| ATL/DFW (or KATL/KDFW), lead 3–12 h | RED (even UTC hour) or GREEN (odd UTC hour) |
| Lead < 3 h, including the past | `LEAD_TOO_SHORT` |
| Lead > 12 h | `LEAD_TOO_LONG` |
| Unknown code (e.g. ORD) | `UNKNOWN_AIRPORT` |
| `ERR` | error response |
| `BAD` | deliberately broken response (P>45 > P>30) |

It's deterministic: the same request always gives the same response.

---

## 7. Deviations from instructions

| # | Deviation | Reason |
|---|---|---|
| 1 | The mock re-stamps example timestamps, flight IDs, lead-time text and local-hour text to the requested hour | Otherwise the card would show a different hour from the one asked, which is confusing in demos. Probabilities and advice text are unchanged. |
| 2 | Test mode with typed airport and free target hour | The instructions require free entry to demonstrate refusals; a text field was also needed to demonstrate "unknown airport". |
| 3 | Mock-only trigger codes `ERR` and `BAD` | `ERR` is specified; `BAD` was added to demonstrate the F1.8 safety check on screen. |
| 4 | The mock assigns `data_period` from the config date splits | Needed to show the F1.9 banner. In the real system the back end owns this. |
| 5 | Optional `DEMO_DATE` environment variable | Sets the default "now" date for rehearsals and the automated screenshot. Default behaviour unchanged. |
| 6 | Shape icon added to the risk badge (●/▲/■) | Strengthens "colour is never the only signal". |
| 7 | DO heading includes "suggestion, controller decides" | Applies trap T23 wording directly on screen. |

None of these move any decision logic into the front end.

---

## 8. Testing

**Method:** one consolidated run at the end of the build (no incremental runs), then fixes and a full re-run.

### 8.1 Automated tests: 37 passed, 0 failed
| Area | Tests | Covers |
|---|---|---|
| Contract | 12 | All 6 examples present and valid · OK examples monotonic · 5 flights each · every flight SIMULATED with probabilities equal to the hour risk · driver times ≤ now · mock returns valid responses for 7 request types · mock is deterministic |
| Formatting | 4 | 0.384 → "38%" · 0.385 → "39%" · 0 → "0%" · null → "—" · capacity text · no arrivals/h when null |
| Safety | 3 | Monotonic violation → error · schema violation → error · refused/error cards contain no numbers |
| Card content | 3 | >45 is the only severe row · SIMULATED tag on all rows · period banner logic |
| Daylight saving | 13 | 2024-03-10 and 2024-11-03, ATL and DFW, local→UTC (8) and UTC→local including the repeated 01:00 and skipped 02:00 (4) · target list never skips an hour on a DST day (1) |

### 8.2 Visual verification: 8 screenshots
`ui_mock_ok_red` · `ui_mock_ok_green` · `ui_mock_refused_short` · `ui_mock_refused_long` · `ui_mock_refused_airport` · `ui_mock_error` · `ui_mock_safety_broken_response` · `ui_mock_period_warning`

### 8.3 Issues found and fixed during the final run
| Issue | Fix |
|---|---|
| Page title clipped under the Streamlit toolbar | Increased the top padding |
| Refusal for a past hour read "-11 h ahead" | Mock now says "is in the past" |
| Re-stamped flights could show "ATL→ATL" | Destination swapped when it equals the requested airport |
| Time-of-day driver and "Lead time N h" reason didn't match the requested hour | Mock updates both to the actual request |
| The automated browser couldn't type into Streamlit's date box (test tooling only) | "Too far ahead" captured with same-day hours (00:00 → 17:00, 17 h); banner captured using `DEMO_DATE` |

---

## 9. Traps addressed

| Trap | How it's handled on screen |
|---|---|
| T6: our own time-zone bug | All conversion via `zoneinfo` from config; UTC shown under the inputs; 13 DST tests |
| T15: contradictory risks | Monotonic check → error card; tested with a broken fixture |
| T18: simulated flights mistaken for predictions | SIMULATED tag on every row, italic grey styling, ⓘ note always shown, contract test asserts equality with the hour risk |
| T19: unlabelled synthetic data | Schema rejects any flight without `source = "SIMULATED"` |
| T23: claiming to replace the controller | "suggestion, controller decides" on the DO line |

Also supported: **T22** (the period-warning banner) and **T7** (null shown as "—", never 0).

---

## 10. Known limitations and open items

1. **Button disable while loading** is implemented but not observable with the instant mock. It will be visible with the real model.
2. **Capacity tooltip** uses the browser's native hover title, so it doesn't work on touch screens. Acceptable for a laptop demo.
3. **`BACKEND=real`** has not been run yet because `backend/api.py` doesn't exist. This is expected until checkpoint J-1.
4. **Mock content** is illustrative. The labels and reasons in the samples are placeholders until the real model supplies them.

---

## 11. Next steps

| Option | Content |
|---|---|
| **F-2: Story and pitch** (recommended next, no code) | One-page user story · why 3–12 h in two sentences · 6-part pitch outline with placeholders for the back end's numbers · limitations and next-steps slide |
| **J-1: Integration** (after back-end B-2) | `BACKEND=real` · five live Gate 3 requests · `ui_real_*.png` screenshots · fresh-laptop test · backup screen recording · submit v1 and freeze |
| **Optional, after v1 is submitted** | X1 Accept/Dismiss with decision log · X2 collapsed "Details for reviewers" panel |

---

## 12. How to run

```bash
pip install -r requirements.txt
streamlit run frontend/app.py          # opens http://localhost:8501 (mock back end)
python -m pytest -q                    # 37 tests
```
No internet connection required.
