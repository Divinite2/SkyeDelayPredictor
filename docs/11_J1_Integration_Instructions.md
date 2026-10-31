# 11 · J-1 Integration Instructions (for the Integration Agent)

**Yes: J-1 is the integration step.** It's where the real back end (`backend/api.py: predict()`) is connected to the real dashboard, checked end to end, and **submitted as v1**.

**Your role, in plain words:** you **connect, check and report**. You **don't redesign or re-tune** anything. If the back end gives wrong numbers or the screen shows something wrong, you **record it precisely and send it back** to the owner (back end or front end) through the lead. The only code you may write is **glue** (scripts, a smoke test, README run steps), always logged.

**Read first:** `docs/04_Data_Contract.md` (the agreed format) · `docs/08_Next_Checkpoints.md` (J-1 section) · `docs/05_Initial_Handover.md` §5 (trap register).

---

## 0. Start conditions (don't begin until all four are true)
| # | Condition | How to check |
|---|---|---|
| S1 | Back end **B-3 approved** by the lead | Tag `b3-api` exists (`git tag`), or the lead says so in writing |
| S2 | Front end **F-3 approved** by the lead | Tag `f3-ready` exists |
| S3 | `reports/demo_cases.json` has `version` ≠ `"placeholder"` | Open the file |
| S4 | You have the lead's **latest merged repo** (zip/bundle, or `main` from GitHub `AutonomousSGHack`) | `git log --oneline -1` matches what the lead announced |

If any of these is false, **stop and tell the lead**. Don't integrate half-finished work.

---

## 1. Set up a clean environment
Use a **fresh folder and a fresh virtual environment**. Never reuse a developer's environment, because it hides missing dependencies.

```bash
# from the lead's bundle (or: git clone https://github.com/<owner>/AutonomousSGHack.git)
git clone atc-weather-risk.bundle AutonomousSGHack
cd AutonomousSGHack
git switch main
git switch -c integration                 # your working branch

python -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
python --version                          # must be 3.11.x
pip install -r requirements.txt
```
Check that the data file is present: `data/raw/Flight_Data_With_Weather_Final.csv` (about 64 MB, 148,274 lines including the header).

**Record in your report:** OS, Python version, and `pip freeze | head -20`.

---

## 2. Build and test everything from scratch
```bash
python run_all.py            # data → features → baselines → models → reports → model card
python -m pytest -q          # all tests: contract, leakage, render, passthrough, adapter
```
**Pass:**
- `run_all.py` exits with code 0, and V1–V10 all PASS in the output
- `models/` contains the model files **and** `model_card.json`
- `reports/metrics.md`, `reports/failure_cases.md` and `reports/demo_cases.json` exist and are newly written (check the timestamps)
- **All** tests pass. Write the exact count, e.g. "71 passed".

If something fails, stop at this step and report it (see §7 for who fixes what).

---

## 3. Smoke-test the real back end without the dashboard
Create `scripts/smoke_real.py`. This is glue code and you're allowed to write it. It calls the **real** `predict()` directly and checks every answer against the contract:

```python
"""J-1 smoke test: real predict() vs the contract. Run: python scripts/smoke_real.py"""
import json, time, pathlib, jsonschema
from backend.api import predict

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "contract/schema.json").read_text())
CASES = json.loads((ROOT / "reports/demo_cases.json").read_text())["cases"]
EXTRA = [  # must be refused or errored, never crash
    {"id": "bad_airport", "airport": "XYZ", "now_utc": "2025-06-14T16:00:00Z", "target_hour_utc": "2025-06-14T22:00:00Z"},
    {"id": "not_on_hour", "airport": "ATL", "now_utc": "2025-06-14T16:00:00Z", "target_hour_utc": "2025-06-14T22:30:00Z"},
    {"id": "out_of_range", "airport": "ATL", "now_utc": "2026-01-01T00:00:00Z", "target_hour_utc": "2026-01-01T06:00:00Z"},
    {"id": "icao_code", "airport": "KDFW", "now_utc": "2025-05-06T11:00:00Z", "target_hour_utc": "2025-05-06T17:00:00Z"},
]
K = ["p_gt15", "p_gt30", "p_gt45", "p_gt60"]
rows = []
for c in CASES + EXTRA:
    t0 = time.perf_counter()
    r = predict(c["airport"], c["target_hour_utc"], c["now_utc"])
    dt = time.perf_counter() - t0
    jsonschema.validate(r, SCHEMA)
    note = r["status"]
    if r["status"] == "ok":
        p = [r["hour_delay_risk"][k] for k in K]
        assert p == sorted(p, reverse=True), f"{c['id']}: risks not monotonic"
        for d in r["drivers"]:
            assert d["observed_at_utc"] is None or d["observed_at_utc"] <= r["request"]["now_utc"], f"{c['id']}: future driver"
        for f in r["flights"]:
            assert f["source"] == "SIMULATED" and [f[k] for k in K] == p, f"{c['id']}: flight rows"
        assert r["data_period"] == "TEST", f"{c['id']}: demo case not in test period"
        note = f'{r["risk_level"]} p>45={r["hour_delay_risk"]["p_gt45"]:.2f} cap={r["capacity"]["index"]:.2f} conf={r["confidence"]["level"]}'
    elif r["status"] == "refused":
        note = f'refused {r["refusal"]["code"]}'
    assert r == predict(c["airport"], c["target_hour_utc"], c["now_utc"]), f"{c['id']}: not deterministic"
    rows.append((c["id"], note, f"{dt:.2f}s"))
for row in rows:
    print(" | ".join(row))
```
**Pass:**
- no assertion errors
- every demo case gives the status its label says (storm → `ok`, ideally RED · calm → `ok` GREEN · too soon / too far → `refused`)
- `bad_airport` → `UNKNOWN_AIRPORT` · `not_on_hour` → `NOT_ON_THE_HOUR` · `out_of_range` → `OUT_OF_DATA_RANGE` · `icao_code` → `ok`, with the airport returned as `DFW`
- **every call after the first takes under 1 s**. The first call may be slower because it loads the model; note how long it took.

Paste the printed table into your report.

---

## 4. Run the dashboard on the real back end
```bash
BACKEND=real streamlit run frontend/app.py           # Windows PowerShell: $env:BACKEND="real"; streamlit run frontend/app.py
```
Open `http://localhost:8501`.

| # | Check | Pass |
|---|---|---|
| 4.1 | Footer | Shows **"Back end: real"** and a response time |
| 4.2 | Each **demo preset** (storm, calm, failure case, too soon, too far) | Correct card. Values on screen **match** the smoke-test table for the same case. |
| 4.3 | Manual: airport ATL, a test-period date, target +6 h | OK card appears. Times are local with a zone label, and UTC is shown in grey. |
| 4.4 | A **training-period** date (e.g. 2024-06-14) | Yellow "not a fair test" banner appears |
| 4.5 | WHY lines (note F-c) | Read naturally, with no repeated wording (e.g. not "Thunderstorm reported: Thunderstorm (code 25)"). Observation times are earlier than "now". |
| 4.6 | Flight table | 5 rows, all tagged SIMULATED, the ⓘ note visible, numbers equal to the hour risk |
| 4.7 | Check button and colours | Button is blue. The risk badge shows colour **and** word **and** shape. |
| 4.8 | Kill test: rename `models/` temporarily and restart | The error card appears with no numbers and no Python crash. **Rename it back afterwards.** |

Save screenshots in `reports/figures/`:
- `ui_real_storm.png`
- `ui_real_calm.png`
- `ui_real_failure.png`
- `ui_real_refused_short.png`
- `ui_real_refused_long.png`
- `ui_real_unknown_airport.png`
- `ui_real_training_banner.png`
- `ui_real_error.png`

---

## 5. Second-laptop test (fresh clone)
On a **different computer**, with nothing pre-installed except Python 3.11 and git:
1. Repeat §1 and §2 exactly, using only the README's instructions.
2. Run `BACKEND=real streamlit run frontend/app.py` and the storm preset.

**Pass:** it works **using only the README**. Anything you had to work out yourself is a README bug. Fix the README (glue, allowed) and log it.

Write `scripts/setup_and_run.sh` (and `.bat` for Windows) with those exact steps. This is glue, so it's allowed.

---

## 6. Backup screen recording
Record the demo path the pitch will use, **storm → calm → failure case → one refusal**, with no narration needed. Save it as `pitch/demo_backup.mp4` (or `.mov`). **Keep it out of git if it's over 50 MB**, and give it to the lead separately.

---

## 7. When something fails: who fixes it
| Symptom | Owner | Your action |
|---|---|---|
| `run_all.py` fails, a metric is missing, the smoke test fails on contents (monotonicity, future drivers, wrong refusal code, slow) | **Back end** | Report: request, response JSON, expected vs actual |
| Schema validation fails on a real response | **Back end** (the contract is fixed) | Report the field and value. **Don't edit `schema.json`.** |
| Screen shows wrong formatting, crashes on a valid response, or the banner, button or footer is wrong | **Front end** | Report with a screenshot and the response JSON |
| Values on screen differ from the smoke test | **Front end**, unless the response itself differs | Report both |
| Missing package, README step wrong, setup script | **You** (glue) | Fix it, log it, re-run |
| Anything that needs a change in `config/` or `contract/` | **Lead** | Stop and ask. It needs a joint pull request. |

**Never:** change thresholds, model settings, the contract or display rules to make a check pass. **Never** re-run the model on the test set to "improve" a number. Test-set runs are logged and owned by the back end.

---

## 8. Trap sweep (final)
Go through `docs/05_Initial_Handover.md` §5. For each of T1–T26, mark ✅ (with evidence: a file, test or screenshot), ⚠ (partly, with an explanation), or ❌. The lead decides whether any ⚠ or ❌ blocks submission.

---

## 9. Report and hand-off to the lead
Send this, plus a zip of branch `integration`:
```
CHECKPOINT: J-1
START CONDITIONS: S1 S2 S3 S4 (each ✅/❌)
ENVIRONMENT: OS, Python version, test count
SMOKE TABLE: <paste>
UI CHECKS 4.1–4.8: ✅/❌ each, screenshot names
SECOND LAPTOP: ✅/❌, README fixes made
RECORDING: file name and size
TRAP SWEEP: ✅ count, ⚠ list, ❌ list
ISSUES SENT TO OWNERS: <list with owner>
GLUE CHANGES: <files added or edited>
RECOMMENDATION: SUBMIT / DON'T SUBMIT YET (why)
```

## 10. After the lead approves
1. The lead tags **`v1-submitted`**. The repo operator pushes it (`git push origin v1-submitted`).
2. **Submit** following the hackathon's submission instructions (repo link `AutonomousSGHack`, and/or zip, as required).
3. **Freeze:** after this, only bug fixes the lead approves, each re-running §2–§4. The front end then moves to **F-2 (story and pitch)**.
