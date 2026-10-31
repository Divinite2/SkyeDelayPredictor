# Version log (maintained by the project lead)

| Tag | Status | Contents | Lead approval |
|---|---|---|---|
| `cp0-draft` | Done | Lead's starter repo: skeleton, config, schema, examples, contract test, docs | Yes |
| `cp0-contract` | Done | **Merge of the back-end and front-end repos.** One contract (front end's schema and examples authoritative), `triggered_by` fix, relative CSV path, unified requirements. 54/54 tests pass. | Yes (L-001 to L-006) |
| `b1-data` | Done | Data stage: load, time-zone repair, weather timeline, clean flights, V1–V10 all pass | Yes |
| `f1-ui` | Done (2 fixes carried to F-3) | Single-screen dashboard on the mock, 6 states, safety checks, DST tests | Yes |
| `b2-model` | Done | Features, leakage tests, baselines, LightGBM delay-band and capacity models, metrics (one test run), failure cases. Lead re-ran: metrics identical; 69 passed, 1 skipped. | Yes (L-007 to L-013) |
| `t0-check` | Pending | Testing expert's independent check of B-2 | |
| `b3-api` | Done | `predict()`, risk rules (RED ≥ 0.172, AMBER ≥ 0.117, colour from P(>45) only), drivers, simulated flights, contract test on real output, demo cases. Lead re-ran: 112 passed; demo calls 0.13–0.22 s. | Yes (L-014 to L-017) |
| `b3-10` | Pending | Calm demo case swap, **reassigned to the integration & testing expert** (lead reviews personally) | |
| `f3-ready` | Pending | | |
| `v1-submitted` | Pending | Code freeze starts | |
| `f2-story` | Pending (last, during freeze) | Story and pitch | |
