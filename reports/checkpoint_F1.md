```
CHECKPOINT: F-1  "The screen works on fake data"
DONE: F1.1 F1.2 F1.3 F1.4 F1.5 F1.6 F1.7 F1.8 F1.9 F1.10 F1.11  (+ Checkpoint 0 front-end files)
EVIDENCE:
  config/config.yaml, contract/schema.json (JSON Schema 2020-12, authoritative), contract/examples/*.json (6)
  frontend/app.py, frontend/render.py, frontend/mock_backend.py
  tests/test_mock_matches_schema.py, tests/test_render.py, tests/fixtures/broken_monotonic.json
  reports/figures/ui_mock_{ok_red, ok_green, refused_short, refused_long, refused_airport, error,
                           safety_broken_response, period_warning}.png
NUMBERS:
  pytest: 37 passed, 0 failed
  0.384 -> "38%"; 0.385 -> "39%"; null -> "—" (never 0)
  DST: 2024-03-10 and 2024-11-03, ATL and DFW, both directions, all correct
  Monotonic violation (P>30 0.301 < P>45 0.384) -> error card, no numbers shown
DEVIATIONS:
  1. Mock re-stamps example timestamps to the requested hour (otherwise the card shows a
     different hour from the one asked). Probabilities/text unchanged.
  2. Test mode (checkbox) allows a typed airport code and free target hour, so the
     "unknown airport" and 2 h / 13 h refusals can be demonstrated. Mock-only codes:
     ERR -> error, BAD -> broken response.
  3. Mock labels data_period from config splits so the TRAIN/VALIDATION banner can be shown.
  4. Optional DEMO_DATE env var sets the default "now" date (demo rehearsal convenience).
  5. Risk level shows colour + word + shape (● RED, ▲ AMBER, ■ GREEN).
  6. DO heading reads "suggestion, controller decides" (trap T23 wording).
  7. Risk bars are one neutral grey (severe row darker); the header is the only colour signal.
TRAPS TICKED: T6, T15, T18, T19, T23
KNOWN PROBLEMS / QUESTIONS:
  - The "Check" button is disabled while a request runs; with the instant mock this is not visible.
  - Capacity tooltip (aar_note) is a native browser hover title.
  - BACKEND=real not yet exercised (no backend/api.py), which is expected until J-1.
```
