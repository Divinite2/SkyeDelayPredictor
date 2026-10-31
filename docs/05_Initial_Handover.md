# 05 · Initial Handover: Read This First

**From:** Team lead · **To:** the whole team (back end, front end, story/pitch)
**Purpose:** everything you need to start work without repeating the lead's research: the problem, the decisions already made and why, what's wrong with the data, the traps, and your first tasks.

**Document set**
| File | For | What it is |
|---|---|---|
| `00_Project_Flowchart.png` | Everyone | Picture of the plan, priorities and gates |
| `01_Workflow.md` | Everyone | Tracks, scope (P0 only plus optional extras), fallbacks, gates, reporting format, pitch plan |
| `02_Instructions_Backend.md` | Data / ML | Step-by-step build of data, model, evaluation and `predict()` |
| `03_Instructions_Frontend.md` | Dashboard | Step-by-step build of the single-screen dashboard |
| `04_Data_Contract.md` | Back end **and** front end | Binding rules for everything exchanged: times, units, missing values, response format |
| `05_Initial_Handover.md` | Everyone | This file |
| `06_First_Checkpoints.md` | Both paths | Checkpoints with pass conditions for back end and front end |

---

## 1. The challenge in plain words
Bad weather causes most air traffic delays. Today, controllers at big hubs reduce how many planes can land each hour **only once the weather arrives**. By then, aircraft are already in the air and end up circling or stuck on taxiways, burning fuel, and later flights get cancelled.

**The brief (Challenge #5) asks for:** a model that uses weather records and flight records to predict, **3–12 hours ahead**, (a) hourly **arrival capacity** (Arrival Acceptance Rate, measured by RMSE) and (b) which flights face **severe delay (> 45 min)**, plus a **dashboard with recommendations** for controllers and **automatic data processing**.

**The brief's four named traps:** data leakage across time, ignoring runway direction, over-fitting to one airport, and comparing raw delay minutes between big and small airports.

**Judging (rubric weights):** Problem realism 20% · Technical soundness 25% · Honest evaluation 20% · Trust and traceability 20% · Impact 10% · Time discipline 5%. Judges reward **sound restraint over polish** and will ask: *"Where does this fail, and how would your user know?"*

## 2. Our product
**User:** a traffic flow controller at ATL or DFW.
**Interaction:** enter an airport and an hour → one result card: delay risk at > 15/30/45/60 min, arrival capacity, WHY, DO, confidence, and the flight list. It refuses anything under 3 h or over 12 h ahead.

## 3. Decisions already made (and why). Don't reopen these without the lead.

| # | Decision | Why |
|---|---|---|
| D1 | **Only the provided CSV.** No external data. | Team decision. Missing pieces (true AAR, wind direction) are handled as stated limitations. |
| D2 | **Lead time 3–12 h only; refuse otherwise** | Under 3 h, an experienced controller already sees the trend. Over 12 h, weather (especially storms) is too unreliable. We prove this by reporting accuracy per lead time. |
| D3 | **LightGBM** (gradient-boosted trees) | Best fit for table data. Handles tipping points (low cloud, high wind), interactions and missing values. Fast. Explainable per prediction. Deep learning and time-series models were rejected: more data needed, harder to explain, no rubric benefit. |
| D4 | **One delay-band model** (≤15, 15–30, 30–45, 45–60, > 60 or cancelled) → P(> 15/30/45/60) | Controllers asked for the risk across intervals, not one threshold. Building from bands means the numbers can never contradict each other. 45 min stays highlighted because the brief requires it. |
| D5 | **Capacity index instead of true AAR**: share of scheduled arrivals delivered on time (≤ 15 min, not cancelled or diverted), scored by RMSE | True AAR isn't in the file, and the file is a ~1% sample, so hourly counts are meaningless. We say this openly. |
| D6 | **Worst-case crosswind** (all wind treated as crosswind), plus a proper crosswind/tailwind function using ATL 80° and DFW 180° from the brief | The file has **no wind direction**. We show the method and the safe assumption rather than skipping the requirement. |
| D7 | **Split by date:** train 2023–2024, validate Jan–Mar 2025, test Apr–Jul 2025 | Random splits leak neighbouring hours of the same storm. Test covers the summer thunderstorm season. |
| D8 | **Recommendations from fixed rules, not AI** | The rubric marks down LLMs making operational decisions. The controller decides (human in control). |
| D9 | **One simple screen** | Controllers are busy. Evidence and metrics go in the pitch, not the controller's view. |
| D10 | **Flight list = simulated example flights only, always labelled, each showing the hour's risk** | Shows the controller what the list would look like. Real per-flight modelling was cut to fit the deadline. Labelling is required by the rubric. |
| D11 | **Time-of-day and traffic interactions are explicit features** | Checked in the file: storms hit evenings 3–4× harder than mornings, and busy days harder than quiet ones. |
| D12 | **P0 only, then freeze; optional extras only after submission** | The deadline is close. A complete honest version beats an ambitious unfinished one. Cut items become "next steps" in the pitch. |

## 4. The data: what's in the file and what's wrong with it

**File:** `Flight_Data_With_Weather_Final.csv` · 148,273 flights · 123 columns · **2023-01-01 to 2025-07-31** · 136 airports
**Format:** US DOT on-time performance records plus hourly weather (Meteostat-style: `temp, prcp, wspd, wpgt, pres, snow, coco`) for origin and destination.

| # | Finding (verified) | Consequence | Handled in |
|---|---|---|---|
| F1 | **~1% sample:** about 6 ATL arrivals/day in the file (reality: about 1,000) | No real hourly arrival rate. Hourly results are noisy. | D5, stated limitation |
| F2 | **Time-zone shift of about 5–6 h:** local flight times were matched to UTC weather. ATL summer temperature by local hour is coolest around 10:00 (22.7 °C) and hottest around 20:00 (31.5 °C). | Every weather value sits on the wrong hour unless repaired | Back end A1.2 |
| F3 | **No wind direction** | Exact crosswind is impossible | D6 |
| F4 | **Fake zeros:** `snow` = 0 in all rows. `wpgt` = 0 in 98%. | Missing would be read as calm | Back end A1.3, contract §3 |
| F5 | **Weather attached to each flight's own time** (`_ORIGIN` at departure hour, `_DEST` at arrival hour) | Direct use = leakage | Back end A2 |
| F6 | Weather coverage only about **9–10 h/day** at ATL/DFW (only hours with a sampled flight) | Readings can be hours old | `obs_age_h` feature, confidence rule, refusal if > 12 h |
| F7 | 73 cancelled flights still carry a delay value | Label conflict | Cancellation wins |
| F8 | Outliers: delay up to 2,884 min, gust 216 km/h | Distorts averages | Bands cap the effect. Range checks. |
| F9 | Data ends **July 2025** (the brief says "2023 to 2025") | Test period is Apr–Jul 2025 | D7 |
| F10 | 3.7% of flights arrive after midnight (next day) | Date errors | Arrival time = departure (UTC) + scheduled duration |

**Signal check (it's worth modelling):** among ATL/DFW departures, **> 45 min delays: 9.7% in clear weather vs 45% in thunderstorms (coco 25–27)**, and 8.9% in light wind vs 16.6% in strong wind.
**Time of day × storm** (coco ≥ 17, i.e. showers or storms, all airports): evening 34% and late 37%, against morning 10%.
**Traffic × storm:** busiest quarter of days 35%, quietest 23%.
*(Caveat: these are simple counts. Busy days are mostly big airports, so the model uses traffic relative to each airport's own normal.)*

## 5. Trap register: tick every box before each submission

### From the brief
| # | Trap | How we avoid it | Owner | ☐ |
|---|---|---|---|---|
| T1 | **Data leakage across time** | Features only from weather observed ≤ forecast time. Banned-column list. Automated leakage test. `observed_at_utc ≤ now` shown to the user. | Back end | ☐ |
| T2 | **Ignoring runway directionality** | Crosswind/tailwind function with runway headings 80°/180°, unit-tested. Worst case used because there's no wind direction. Limitation stated. | Back end | ☐ |
| T3 | **Over-fitting to one airport** | Airport-agnostic features (no airport ID; traffic relative to each airport's own norm), config-driven airports. Transfer test is out of scope: say so as a limitation. | Back end | ☐ |
| T4 | **Un-normalised delays** | All outputs are probabilities or shares. Traffic is relative to the airport's own norm. No raw-minute comparisons between airports. | Both | ☐ |

### From the data
| # | Trap | How we avoid it | ☐ |
|---|---|---|---|
| T5 | Time-zone shift in the provided weather | Repair plus the temperature-peak proof chart | ☐ |
| T6 | A second time-zone bug on our side | Everything UTC internally. Local time only on screen. Daylight-saving test dates. | ☐ |
| T7 | Missing stored as 0 | `null` everywhere. `snow` dropped. `wpgt` zeros → null. | ☐ |
| T8 | Treating the sample as full traffic | Never call our counts "AAR". Wording fixed in contract and pitch. | ☐ |
| T9 | Cancelled flights counted as "on time" or dropped | Cancelled → worst band (> 60) and "not delivered" | ☐ |
| T10 | Overnight-arrival date errors | Arrival = departure (UTC) + scheduled duration | ☐ |

### From modelling
| # | Trap | How we avoid it | ☐ |
|---|---|---|---|
| T11 | Random train/test split | Date split with a 12 h purge buffer | ☐ |
| T12 | Tuning on the test set | Tune on validation only. Test once per version. Logged. | ☐ |
| T13 | Target leakage through historical rates (airline or airport rates computed with test data) | Rates from the **training period only** | ☐ |
| T14 | Accuracy as the metric on imbalanced data (~10% severe) | Brier, RPS, PR-AUC with the base rate | ☐ |
| T15 | Contradictory risks (P(> 45) > P(> 30)) | Band model plus a monotonic assert. The front end refuses to show violations. | ☐ |
| T16 | Too-good-to-be-true scores | ROC-AUC > 0.95 → stop and investigate | ☐ |
| T17 | Small-sample conclusions (e.g. only 17 night-storm flights) | Report counts with every rate. No claims from tiny groups. | ☐ |
| T18 | Simulated flights mistaken for real predictions | All rows tagged SIMULATED, ⓘ note always shown, contract test asserts they equal the hour risk | ☐ |

### From the product and judging
| # | Trap | How we avoid it | ☐ |
|---|---|---|---|
| T19 | Unlabelled synthetic data | `source: SIMULATED` on every generated row, visually tagged | ☐ |
| T20 | An LLM making decisions or doing maths | No LLM in the decision path. Rules and statistics only. | ☐ |
| T21 | Only success stories | At least one miss and one false alarm, with reasons | ☐ |
| T22 | Demoing on dates the model trained on | Demo dates from Apr–Jul 2025. The UI warns otherwise. | ☐ |
| T23 | Claiming to replace the controller | "Suggests; controller decides" wording | ☐ |
| T24 | Scope creep | P0 only. Freeze after submission. Fallbacks in `01_Workflow.md` §4. | ☐ |
| T25 | Over-claiming impact | Report measured hit and false-alarm rates vs baseline separately from estimated benefits | ☐ |
| T26 | Overrunning 3 minutes | Scripted, rehearsed pitch | ☐ |

## 6. First tasks for each person
| Person | First task | Done when |
|---|---|---|
| **Back-end lead** | Read `04_Data_Contract.md` and agree it with the front end. Set up the repo and `config.yaml`. Start A1. | Contract marked "Agreed v1.0". `validation_report.md` exists. |
| **Front-end lead** | Agree the contract. Write `contract/examples/*.json` **together with the back end**. Build B1 on the mock. | Mock dashboard shows the ok, refused and error states |
| **Everyone** | Read the trap register (§5). Follow `06_First_Checkpoints.md`. **Two paths:** the back end also produces the evidence (story items C2–C3), and the front end also owns the user story and pitch (C1, C4). | — |

## 7. Open questions and risks (the lead is tracking these)
| # | Item | Plan if it goes wrong |
|---|---|---|
| R1 | The time-zone repair might not hold for some airports or seasons | Exclude those airports. ATL and DFW must pass V3 or we escalate. |
| R2 | The model may not beat climatology at longer lead times | Report it honestly and use it to support the 12 h limit |
| R3 | Few storm examples: only about **164** shower or thunderstorm departures at ATL/DFW combined (about 1,700 across all 136 airports) | Explicit interaction features. Report counts. State as a limitation. |
| R4 | The capacity index is noisy per hour (about 1 arrival per hour sampled) | State it as a limitation. Report RMSE together with the number of arrivals behind it. |
| R5 | Judges may expect true AAR | Pitch line: "AAR isn't in the provided data. Here's our transparent substitute, and here's what we'd plug in with FAA data." |

## 8. How we work with the lead
- Report at every gate using the template in `01_Workflow.md` §6.
- **Any deviation** from these documents goes in `reports/decisions_log.md` and the next gate report.
- The lead reviews every report against the brief, the rubric and these documents, and replies with specific fixes.
