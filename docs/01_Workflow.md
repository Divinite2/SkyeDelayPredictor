# 01 · Workflow: How We Run This Project

**Challenge:** Autonomous SG 2026, Airbus Track, **Challenge #5**
**Product:** a forecaster that gives an air traffic controller **delay risk and arrival capacity for one airport and one hour, 3 to 12 hours ahead**.
**Read with:** `00_Project_Flowchart.png` (the picture of this document), `02_Instructions_Backend.md`, `03_Instructions_Frontend.md`, `04_Data_Contract.md`, `05_Initial_Handover.md`

> **How to read these documents:** the normal text is written for everyone. Boxes marked **🔧 Technical note** are for developers. Non-technical team members can skip them.

---

## 1. The product in one paragraph

A traffic flow controller at a busy hub (Atlanta ATL or Dallas Fort Worth DFW) types in **an airport and an hour**. The tool answers with:
1. The chance that departures in that hour are delayed by **more than 15, 30, 45 and 60 minutes**.
2. The expected **arrival capacity** (share of arrival slots delivered on time).
3. **Why** (the top three weather or traffic reasons, each with its timestamp).
4. **What to consider doing** (a fixed rule, not AI).
5. **How confident** the tool is.
6. **A list of example flights in that hour.** These are **simulated (dummy) flights**, clearly labelled, and each shows the hour's risk.

If the hour is **less than 3 or more than 12 hours away**, the tool refuses and says why.

## 2. Why 3 to 12 hours (agreed design consideration)

| Lead time | Decision | Reason |
|---|---|---|
| Under 3 h | **Not forecast. The tool refuses.** | An experienced controller can already see the trend from radar, current observations and traffic. The model adds little and could distract. |
| **3–12 h** | **Our window** | Early enough to act calmly: reduce arrival rates in advance, hold aircraft on the ground at their origin instead of in the air, warn airlines, adjust staffing. Recent weather still carries useful information. |
| Over 12 h | **Not forecast. The tool refuses.** | Weather this far ahead, especially thunderstorms, is too unreliable. False alarms teach users to ignore the tool. |

We **prove** this with our own numbers by reporting accuracy separately at 3, 6, 9 and 12 hours. If the model doesn't beat the simple baseline at some lead time, we say so and mark that range as low confidence.

## 3. Team structure: three tracks working in parallel

| Track | Who | Owns | Document |
|---|---|---|---|
| **A: Back end** (critical path) | Data / ML developer(s) | Cleaning, features, models, evaluation, the `predict()` function | `02_Instructions_Backend.md` |
| **B: Front end** | Dashboard developer | Streamlit app, which only displays what the back end returns | `03_Instructions_Frontend.md` |
| **C: Story and evaluation** (no separate person) | Split: back end produces the evidence (C2–C3), front end owns the story and pitch (C1, C4) | User story, evidence, failure cases, 3-minute pitch | This document §7, and `06_First_Checkpoints.md` |
| **Shared** | A and B | The **data contract** (the agreed format of everything passed between back end and front end) | `04_Data_Contract.md` |

**Why parallel works:** the front end doesn't wait for the model. It starts on **fake predictions that follow the data contract exactly**. When the real model is ready, it's swapped in and nothing else changes.

## 4. Priorities (cut to fit the deadline)

> **Scope decision:** there's no P1 tier. We aren't modelling real individual flights. The project is **P0 only**, plus two optional extras if P0 is fully done.
> **Rule 1:** finish and submit all P0 items before touching anything optional.
> **Rule 2:** submit as soon as Gate 3 passes. Then **freeze the code**: only bug fixes and pitch work after that.
> **Rule 3:** if something is going badly, simplify it (see "fallbacks" below). Never drop a P0 item silently.

### P0: Must have (the complete, honest entry)
| ID | Item | Track |
|---|---|---|
| S0 | Repo, `config.yaml`, data contract agreed | Shared |
| A1 | Load the CSV, **repair the time-zone shift**, rebuild the hourly weather timeline, treat fake zeros as missing, validation report | A |
| A2 | **Leakage-safe** core features: weather known before the forecast time, time of day, traffic level, worst-case crosswind, storm × evening, storm × traffic | A |
| A3 | Baselines, **delay-band model** (> 15/30/45/60 min), **capacity index model**, scores at 3/6/9/12 h | A |
| A4 | `predict()` returning the contract format: refusal rule, WHY, DO, confidence, and **simulated flight list** | A |
| B1 | Streamlit skeleton on fake contract data | B |
| B2 | Input (airport, hour, "now"), result card, refusal and error screens, **simulated flight table** | B |
| C1–C4 | User story, evidence, evaluation pack with **at least one failure case**, 3-minute pitch | C |
| INT | Front end calls the real `predict()`. **One command** runs everything. | A + B |

### Optional (only after v1 is submitted and frozen)
| ID | Item |
|---|---|
| X1 | Accept/Dismiss buttons with a decision log (shows the human in control) |
| X2 | Collapsed "Details" panel for judges (metrics table, limitations) |

### Removed from scope (state these as "next steps" in the pitch)
Per-flight risk using real flights and flight features · probability calibration · ATL↔DFW transfer test · extra weather factors (pressure trend, storm duration, knock-on delay, temperature extremes) · 3-hour block scores · all 136 airports.

### Fallbacks if a P0 item is stuck (simplify, don't drop)
| If this is stuck… | …do this instead, and log it |
|---|---|
| Capacity model | Use climatology (B0) as the capacity forecast and report its RMSE honestly |
| WHY drivers (`pred_contrib`) | Show the 3 most extreme weather inputs vs their training averages, labelled "notable conditions" |
| Delay-band model underperforms | Ship it anyway with honest scores. The baseline comparison *is* the evaluation. |
| Front-end polish | Plain Streamlit text and `st.progress` bars are fine. Correct beats pretty. |

**Never cut:** the leakage test, the baselines, the failure case, the refusal rule, the SIMULATED labels.

## 5. Phases and quality gates

The picture is in `00_Project_Flowchart.png`. A **gate** is a stop-and-check point. Work doesn't move past a gate until it passes, or until the lead (me) signs off a documented exception.

| Phase | What happens | Gate at the end | Pass condition |
|---|---|---|---|
| **0. Setup** | Repo, config, contract agreed and signed by A and B | — | `04_Data_Contract.md` marked "Agreed v1.0" by both |
| **1. Data** | A1. B builds on fake data. C writes the user story. | **Gate 1: Data checks** | Every check in the back-end validation report is ✅, or ❌ with a written reason the lead accepts |
| **2. Model** | A2–A4. B finishes the result card. C collects evidence. | **Gate 2: Model honesty** | (a) automated leakage test passes; (b) the model beats the climatology baseline on the >45 min Brier score at 3 h and 6 h ahead; (c) the risk numbers never contradict each other (P(>15) ≥ P(>30) ≥ P(>45) ≥ P(>60)). If (b) fails after a reasonable effort, **report it honestly and continue**. Don't hide it. |
| **3. Integrate** | Front end connected to the real back end, one-command run | **Gate 3: End to end** | On a test-period day the model has **never seen**, a fresh clone runs `python run_all.py`, then `streamlit run frontend/app.py`, and returns valid results for: a normal hour, a storm hour, a refused hour (2 h ahead), a refused hour (13 h ahead), and an unknown airport |
| **4. Submit v1** | **Submit early** | — | All P0 items done |
| **5. Freeze** | Bug fixes, X1/X2 if everything else is done, pitch rehearsal | Re-run Gate 3 after any change | Resubmit **only** if the new version still passes every gate |
| **6. Present** | 3-minute pitch | — | Rehearsed to under 3 minutes, failure case included |

## 6. How work is reported back to the lead (for critique)

At each gate, the worker sends a short report in this format:

```
GATE: <1 / 2 / 3>
DONE: <list of item IDs completed>
EVIDENCE: <file paths: validation report, metrics table, screenshots>
NUMBERS: <key metrics vs baseline, per lead time>
DEVIATIONS: <anything done differently from the instructions, and why>
KNOWN PROBLEMS: <what is broken or uncertain>
QUESTIONS: <decisions needed from the lead>
```
I'll check each report against the brief, the rubric and these instructions, and reply with specific fixes.

## 7. Track C: story, evidence and pitch (non-technical)

**C1, user story.** Fill this in:
- **User:** traffic flow controller / traffic management coordinator at a major hub (ATL or DFW).
- **Today:** arrival rates are cut **when the weather arrives**. Aircraft then circle in holding patterns or wait on taxiways with engines running, and later flights are cancelled.
- **With our tool:** a warning 3–12 hours ahead, with reasons, so the reduction can be planned while aircraft are still on the ground.
- **Not our claim:** the tool doesn't replace the controller's judgement. It suggests and the controller decides.

**C2, collect evidence as it is produced:**
- The before/after time-zone repair chart (the back end produces it)
- The validation report
- The evidence chart: severe-delay rate by weather type (9.7% overall → 45% in thunderstorms in our file)
- Screenshots of the result card in normal, storm and refused states

**C3, evaluation pack (one slide or page):**
- What we tested on: Apr–Jul 2025, never seen by the model
- Scores vs baseline at 3, 6, 9 and 12 hours
- **One failure case**, with the reason and what would fix it
- Data limitations: sampled flights, capacity index instead of true AAR, no wind direction, time-zone repair

**C4, 3-minute pitch structure:**
| Section | Content |
|---|---|
| Problem | The user, the status quo and the cost |
| Demo | Live: storm day, 6 h ahead → red card → what actually happened |
| Evidence | Scores vs baseline per lead time, one chart |
| Honesty | The failure case and the limitations |
| Impact | Measured: share of severe-delay flights flagged at least 3 h ahead, and the false-alarm rate, vs baseline |
| Close | What would make it production-ready (full schedule data, wind direction, TAF forecasts) |

## 8. Definition of done (whole project)
- [ ] `python run_all.py` rebuilds everything from the raw CSV with no manual steps
- [ ] Validation report, metrics report and failure-case report exist in `reports/`
- [ ] Dashboard answers any valid airport + hour within 3–12 h, refuses everything else with a clear message
- [ ] Every simulated item is labelled `SIMULATED`
- [ ] All traps in `05_Initial_Handover.md` section 5 are checked off
- [ ] Pitch rehearsed under 3 minutes
