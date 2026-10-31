# 14 · Instructions for the Integration & Testing Expert: T-0 → B3.10 → J-1

**Your role:** you're the **integration and testing expert**. You check other people's work independently, connect the back end to the front end, and prepare the submission. The back-end expert is now **on call only**.

**Order (updated):** **T-0 first** (check the back end exactly as delivered) → **B3.10** (one small demo-case change) → **F-3b** (two front-end fixes, reassigned to you; see §3b) → report → **J-1**.

**Start from the latest zip (tag `f3-merged`)**, which contains the front end's F-3 work. If you already started T-0 on `b3-api`, carry your work over (copy `scripts/` and your B3.10 change into the new folder) and re-run `pytest`.

> **Why T-0 comes before B3.10:** you're checking someone else's work. Do it **before** you change anything, so your checks are of the untouched code.

---

## 0. Permissions (read carefully)
| You MAY | You may NOT |
|---|---|
| Write glue: `scripts/`, README run steps, setup scripts | Change the model, features, thresholds, `predict()` logic or tests written by others |
| **B3.10 only:** edit the **calm-case selection** inside `build_demo_cases()` in `run_all.py` · **F-3b only:** edit `frontend/demo_cases.py`, the capacity block in `frontend/app.py`/`render.py`, and their tests | Edit `contract/` or `config/` (joint pull request plus lead only) |
| Log every change in `reports/decisions_log.md` (prefix **I-**, e.g. I-001) | Re-tune anything, or run anything on the test set to "improve" a number |
| Report bugs to their owner through the lead | Fix back-end or front-end bugs yourself, unless the lead says so in writing |

**Independence safeguard:** because you change the calm demo case and the front-end presets **and** test them, **the lead reviews B3.10 and F-3b personally**. Your own tests of the calm case don't count as independent.

---

## 1. Setup
1. Unzip `atc-weather-risk.zip` (tag `b3-api`) into a **fresh** folder named `AutonomousSGHack`. Don't reuse anyone else's folder or environment.
2. ```bash
   cd AutonomousSGHack
   git switch -c integration
   python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
   python --version                                       # 3.11.x
   pip install -r requirements.txt
   python run_all.py                                      # about 2 min; rebuilds data and models
   python -m pytest -q                                    # expect: 112 passed
   ```
3. Record your OS, Python version and the test count.

---

## 2. T-0: independent check of B-2 and B-3 (read-only)
| # | Check | Pass |
|---|---|---|
| T0.1 | Setup above runs clean | `run_all.py` exits 0 · **112 passed** |
| T0.2 | Compare your `reports/metrics.md` with the committed one (`git diff reports/metrics.md`) | No differences in numbers. The build is deterministic. |
| T0.3 | Read `tests/test_leakage.py` | It really (a) deletes weather after the forecast time and (b) injects a fake future storm, and features stay identical. The banned-column check covers **both** models. |
| T0.4 | `reports/decisions_log.md` D-023 and `run_all.py` flags | The test set is only scored in the final run. Development used `--no-test`. |
| T0.5 | Failure case ATL 2025-06-28 (target 12:00Z, 6 h ahead) in `data/processed/features_test.parquet` | Last observation about 7 h old, thunderstorm code about 23Z the day before, `storm_last_6h = 0` |
| T0.6 | Write `scripts/smoke_real.py` (code in `11_J1_Integration_Instructions.md` §3) and `scripts/setup_and_run.sh` / `.bat` | Files exist and run |
| T0.7 | Run `python scripts/smoke_real.py` | All schema checks pass · true_red → RED · calm → GREEN · miss → GREEN · refusals correct · 4 extra requests correct · every call after the first under 1 s. **At this point calm will still show LOW confidence. That's expected; B3.10 fixes it.** |
| T0.8 | Read `tests/test_contract.py` | Covers all 6 refusal codes, determinism, a forced error, and driver times ≤ now |
| T0.9 | **Recompute the RED/AMBER thresholds yourself** from the validation hour-level P(>45) (all leads), using the model in `models/` | 90th percentile ≈ **0.172**, 70th ≈ **0.117** |
| T0.10 | Spot-check 3 random `ok` answers by hand | Probabilities in order (>15 ≥ >30 ≥ >45 ≥ >60), 5 SIMULATED flights equal to the hour risk, no weather driver after "now" |

Anything that fails → **stop** and report it (owner: back end). Don't fix it.

---

## 3. B3.10: swap the calm demo case (decision L-015)
**Why:** the current calm case (ATL 5 Apr 2025 07:00 local) is a correct GREEN but shows **LOW** confidence, and so does the failure case. If both green examples say LOW, judges will think the tool always says LOW. **Choosing a demo hour is selection, not tuning**, so the model and thresholds stay untouched.

**Selection rule (apply exactly, and write it into `demo_cases.md`):**
1. Test period, **6 h ahead**, ATL or DFW
2. **True GREEN:** `predict()` returns GREEN **and** every sampled departure in that hour was on time, with at least 2 flights
3. Calm, dry weather at the issue time (the same filters as now: `coco_calm == 1`, no precipitation)
4. **Confidence HIGH or MEDIUM** (as returned by `predict()`)
5. **Daytime:** target hour between 08:00 and 18:00 local
6. Among the candidates, pick the **lowest P(>45)**. If tied, take the earliest date.

**Where:** `run_all.py` → `build_demo_cases()`. The `calm = ...` lines (around line 206) currently filter on rules 1–3 and sort by P(>45). Change them to:
- add the local-hour filter (rule 5)
- walk the candidates in order, call `api.predict()` on each, and take the **first** whose `confidence.level` is HIGH or MEDIUM (rule 4)
- **fallback:** if there's no candidate, relax "at least 2 flights" to "at least 1", and record that in `demo_cases.md`. If there's still none, stop and tell the lead.

> **Lead's feasibility check:** before the weather filter (rule 3), 99 test hours already meet rules 1, 2, 4 and 5 (e.g. ATL 2 Apr 2025 11:00 local, P(>45) 0.065, HIGH). So a candidate should exist and the fallback shouldn't be needed.

Update the case label so it says what's true, e.g. *"True GREEN: calm daytime hour, all flights on time, confidence MEDIUM (DFW, 6 h ahead)"*.

**Don't touch** the `true_red`, `miss` or refusal cases, or anything outside `build_demo_cases()`.

**Then:**
```bash
python run_all.py
python -m pytest -q                   # still 112 passed
python scripts/smoke_real.py          # calm → GREEN with HIGH/MEDIUM confidence
git add -A && git commit -m "B3.10: calm demo case per L-015 (selection rule in demo_cases.md)"
```
Log it as **I-001** in `reports/decisions_log.md`: the rule used, the case chosen, and how many candidates there were.

---

## 3b. F-3b: two front-end fixes (reassigned to you; details in `docs/15_F3_Review_and_F3b_Fixes.md` §2)
| # | Fix | Pass |
|---|---|---|
| F3b.1 | `frontend/demo_cases.py` reads **`reports/demo_cases.json`** (`cases[]`: `id`, `label`, `airport`, `now_utc`, `target_hour_utc`) instead of `demo_cases.md` | Picker shows exactly the **5 labels from the JSON**, verbatim, in file order. **Remove the auto-generated refusal presets** (the JSON already has `too_soon` and `too_far`). No hard-coded ids. |
| F3b.2 | Fallback | JSON missing or invalid → picker hidden, grey note "Demo cases not available", manual inputs still work. A labelled sample JSON fixture is allowed in **mock** mode only. |
| F3b.3 | Capacity note visible (F3.7) | When `index_low`/`index_high` are null and `aar_note` exists, show `aar_note` as **grey text under the capacity line** (not only a tooltip). Text from the response. |
| F3b.4 | Tests | Rewrite `tests/test_demo_cases.py` for JSON (parse, missing, invalid, labels verbatim, no duplicates) plus one render test for F3b.3. All tests pass (≥ 123). |
| F3b.5 | Screenshots, `BACKEND=real` | `ui_f3b_picker.png` (5 labels) · `ui_f3b_true_red.png` (capacity note visible) |

**Do F-3b after B3.10**, so the picker shows the new calm case. Log the changes as I-002 onward. Don't touch `contract/`, `config/`, `backend/` or the display rules.

## 4. Report to the lead (T-0 + B3.10 + F-3b)
Upload **the report** and **a zip of your whole `AutonomousSGHack` folder** (you can leave out `.venv`, `data/processed` and `models/`).
```
CHECKPOINT: T-0 + B3.10 + F-3b
BASE: tag b3-api (commit id)
ENVIRONMENT: OS, Python, test count
T-0 RESULTS: T0.1–T0.10 ✅/❌ each, with numbers (thresholds you computed, smoke table)
F-3b: F3b.1–F3b.5 ✅/❌, screenshot names
B3.10: case chosen (airport, local time, P(>45), confidence, outcome), number of candidates, fallback used?
GLUE FILES: scripts/... 
ISSUES FOR OWNERS: ...
DEVIATIONS: ...
```
The lead reviews B3.10 and F-3b personally, then tags `t0-check`, `b3-10` and `f3-ready`.

---

## 5. Then J-1 (only after the lead approves T-0, B3.10 and F-3b)
Follow `11_J1_Integration_Instructions.md` in full, with these expected results:
- true_red → **RED** · calm → **GREEN, HIGH/MEDIUM** · miss → **GREEN, LOW** · too_soon / too_far → **refused**
- capacity line: **no range**, grey note visible (F3.7)
- footer: **"Back end: real"** plus response time
- demo picker lists the cases from `reports/demo_cases.json`, with no "placeholder" note

At the end of J-1: the lead tags `v1-submitted`, you **submit**, and the freeze starts.
