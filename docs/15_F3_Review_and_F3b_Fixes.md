# 15 · Lead Review of F-3, Fixes Needed (F-3b), and the Path to Submission

## 1. Verdict: F-3 ⚠ PASS WITH 2 REQUIRED FIXES (merged, tagged `f3-merged`; `f3-ready` after F-3b)

**What the lead did:**
- Merged the front end's work (`airport-risk-ui-3.zip`) into the shared repo on top of `b3-api`.
- Ran the **full suite: 123 passed** (112 back end/contract + new front-end tests).
- Fed the **real** back-end files into the front end's preset reader.

**What works well:**
- blue button
- safe real/mock adapter (the import-failure test passes)
- answers passed through untouched
- caching and spinner
- 48 front-end tests, 14 screenshots
- F-2 drafts already prepared in `story/`

**Process note (third time):** the front end again worked in its **own copy** (`airport-risk-ui`, no git history), not the shared repo. That's why it never saw `docs/12` and `docs/13`, and it explains both problems below. The lead merged it. **For F-3b, start from the zip attached to this message (tag `f3-merged`).**

### Problem 1, demo-critical: presets read the wrong file and lose the honest labels
The picker reads `reports/demo_cases.md` (a human-readable table) instead of **`reports/demo_cases.json`** (F3.5, L-017). Against the real files it shows:
```
Case 1 · Case 2 · Case 3 · Case 4 · Case 5 · Refused: 2 h ahead · Refused: 13 h ahead · Refused: unknown airport (ORD)
```
- The **honest labels are lost** (e.g. "True RED: highest-risk test hour where severe delays happened…", "Known failure case: morning after a storm…"). In the pitch the presenter would be clicking "Case 3" with no idea it's the failure case.
- **The refusals appear twice:** Cases 4 and 5 *are* the back end's refusal cases, plus three auto-generated ones.

### Problem 2: F3.7 missing (capacity note only on hover)
Since L-008, the back end sends **no capacity range** (`index_low`/`index_high` = null) and explains why in `aar_note`. The screen only shows that note as a **hover tooltip** (ⓘ). Judges and controllers won't see it. F3.7 requires it as **visible grey text**.

### Accepted change (logged as L-018)
The front end loosened `schema.json` so **request fields may be null on refused/error responses** (strict on `ok`). That's a contract change made on a private copy, which breaks the rule. **But** it implements the agreed v1.0 clarification exactly, and **all back-end contract tests still pass** against it. Accepted. Next time, raise it with the lead first.

---

## 2. F-3b: front end (two small fixes, then the front end is done until F-2)

| # | Fix | Pass condition |
|---|---|---|
| F3b.1 | `frontend/demo_cases.py` reads **`reports/demo_cases.json`** (`cases[]` with `id`, `label`, `airport`, `now_utc`, `target_hour_utc`) | Picker shows exactly the **5 labels from the JSON**, in file order, with the text verbatim. **No auto-generated refusal presets** (the back end already supplies `too_soon` and `too_far`). No hard-coded ids (L-017). |
| F3b.2 | Fallback | If the JSON is missing or invalid, the picker is hidden and a grey note says "Demo cases not available". The manual inputs still work. In **mock** mode only, a labelled sample JSON fixture may be used. |
| F3b.3 | F3.7: capacity note visible | When `index_low`/`index_high` are null and `aar_note` is present, show `aar_note` as **grey text under the capacity line**. Text from the response, not hard-coded. |
| F3b.4 | Tests | Update `tests/test_demo_cases.py` for JSON (parsing, missing file, invalid file, labels verbatim, no duplicates). One render test for F3.7. **All tests pass on the merged repo** (≥ 123). |
| F3b.5 | Real-mode screenshots | `BACKEND=real` (the real back end now exists in this repo; run `python run_all.py` first, about 2 min): `ui_f3b_picker.png` (5 labels visible), `ui_f3b_true_red.png` (capacity note visible). |

**Don't touch:** `contract/`, `config/`, `backend/`, `run_all.py`.
**Report:** `CHECKPOINT: F-3b`, plus a zip of **this repo folder** (not `airport-risk-ui`).

---

## 3. Status and remaining path

| Item | Owner | Status |
|---|---|---|
| T-0 + B3.10 (calm case swap) | Integration and testing expert | ⏳ In progress (`docs/14`) |
| **F-3b** | Front end | ⏳ **New**, can run alongside T-0 |
| **J-1** integrate, test, **submit v1** | Integration and testing expert | Starts when `t0-check`, `b3-10` **and** `f3-ready` exist |
| F-2 pitch (last, during freeze) | Front end | Drafts exist in `story/`. Fill in the real numbers from `docs/13` §3. |

**J-1 start condition S2 is now tag `f3-ready`** (after F-3b), not `f3-merged`.

**Expected J-1 demo picker (after F-3b and B3.10):** 5 entries with honest labels: true RED → RED · calm → GREEN, HIGH/MEDIUM · failure case → GREEN, LOW · too soon → refused · too far → refused. Plus manual entry for the unknown-airport refusal (test mode).

## 4. Files to send
| To | Files |
|---|---|
| Front end | `atc-weather-risk.zip` (latest, tag `f3-merged`) · this file · `10_F3_Instructions.md` · `12_B2_Review_and_Next_Steps.md` (F3.7) · `13_B3_Review_and_Next_Steps.md` (L-017) |
| Integration and testing expert | No change if they've started T-0 on `b3-api`; the F-3 merge doesn't affect T-0 or B3.10. For J-1 they'll get the final merged zip from the lead. |
| GitHub | Push the latest bundle |
