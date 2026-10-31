# Demo cases (SAMPLE for mock mode / tests)

Placeholder in the format expected from the back end's `reports/demo_cases.md` (B3.8).
Not real model output.

| case | airport | now_utc | target_hour_utc | note |
|---|---|---|---|---|
| Storm hour flagged RED, 6 h ahead (mock) | ATL | 2025-06-14T16:00:00Z | 2025-06-14T22:00:00Z | mock returns RED on even UTC hours |
| Calm GREEN hour (mock) | DFW | 2025-05-20T11:00:00Z | 2025-05-20T15:00:00Z | mock returns GREEN on odd UTC hours |
| Failure case (mock) | ATL | 2025-07-02T13:00:00Z | 2025-07-02T21:00:00Z | real case to come from reports/failure_cases.md |
