# 3-Minute Pitch Outline (draft)

**Checkpoint:** F-2 · Item 3 of 4
**Target length:** 2:45 spoken (15 s buffer) · ≈ 400 words · 6 sections
**Agreed figures (lead, doc 08):** severe = **"> 45 min late or cancelled"** · **11.3% train / 17.8% test** · **69 thunderstorm + 107 shower** departures at ATL/DFW
**Placeholders:** `[BE: …]` = number to be supplied by the back end (metrics, failure case). Don't fill these with estimates.

---

## Timing plan

| # | Section | Time | Cumulative | Slide / screen |
|---|---|---|---|---|
| 1 | Problem | 0:30 | 0:30 | Slide 1: user + status quo |
| 2 | Demo | 0:50 | 1:20 | Live dashboard (backup: screenshots / recording) |
| 3 | Evidence | 0:30 | 1:50 | Slide 2: scores vs baseline per lead time |
| 4 | Honesty | 0:25 | 2:15 | Slide 3: failure case + limitations |
| 5 | Impact | 0:20 | 2:35 | Slide 4: hit rate / false alarms vs baseline |
| 6 | Close | 0:10 | 2:45 | Slide 5: next steps |

---

## 1 · Problem (0:30)
**Slide 1:** photo or icon of a flow controller · three-step status quo strip: *weather arrives → rate cut → aircraft hold / cancellations* · inset: **`severe_by_weather.png`** (severe-delay rate by weather type, with counts)

**Script:**
> "This is for a traffic flow controller at Atlanta or Dallas. Today, arrival rates are cut **when the storm arrives**. By then, the aircraft are already in the air, so they circle in holding patterns, others wait on taxiways with engines running, and the evening ends in cancellations.
> In our data, about **one departure in nine** is severely delayed (more than 45 minutes late or cancelled). In thunderstorms it's `[BE: rate]`, across **69 storm departures**. The problem isn't that controllers don't react. It's that they react too late to do it cheaply."

---

## 2 · Demo (0:50)
**Screen:** live dashboard on the laptop (`BACKEND=real`). The date is a test-period storm day the model has never seen: `[BE: chosen date, hour]`.

**Script and actions:**
| Action | Say |
|---|---|
| Airport ATL, now = `[BE: hh:00]`, target = +6 h, press **Check** | "It's noon. I ask about 18:00, six hours ahead." |
| Point at the RED badge and >45 bar | "RED. A `[BE: x]`% chance of departures delayed more than 45 minutes." |
| Point at WHY | "And why: a thunderstorm reported at 11:00, strong wind, evening peak. Every reason has a timestamp the controller can check." |
| Point at DO + rule ID | "The suggestion comes from a fixed rule, not AI. The controller decides." |
| Point at confidence | "Medium confidence, and it says why." |
| Tick test mode, set target +2 h, press **Check** | "Ask two hours ahead and it **refuses**. The controller already knows more than we do." |
| (Back to the slide) | "And what actually happened that evening: `[BE: actual >45 share / outcome]`." |

**Backup:** `reports/figures/ui_real_*.png` + screen recording (made at J-1).

---

## 3 · Evidence (0:30)
**Slide 2:** main chart: Brier score at >45 min, model vs climatology baseline, at 3 / 6 / 9 / 12 h. Capacity RMSE in a corner. Small inset: **`timezone_fix.png`** (the temperature peak moved into 13:00–18:00 after the repair), as proof the data was fixed before modelling.

**Script:**
> "First, we fixed the data: the weather in the file was shifted five to six hours, and this chart shows the repair.
> We tested on April to July 2025: data the model **never saw**. It's a harder period: **17.8%** severe against **11.3%** in training, `[BE: seasonal comparison, Apr–Jul 2023/2024 — 'which is normal for summer' or 'a real shift']`. We split by date, not randomly, so no storm leaks into training.
> Against a climatology baseline, the model is better at `[BE: lead times]` hours, with a Brier score of `[BE: x]` vs `[BE: y]` at 6 hours. Capacity index RMSE is `[BE: x]` vs `[BE: y]` for the baseline.
> `[BE: if it fails at 12 h: 'At 12 hours it no longer beats the baseline, which is exactly why we stop there.']`"

---

## 4 · Honesty (0:25)
**Slide 3:** left: one failure case (date, prediction, what happened, why, fix). Right: 4 limitation bullets.

**Script:**
> "Here's where it fails. On `[BE: date]` we predicted `[BE: GREEN/RED]`, and `[BE: what happened]`, because `[BE: reason, e.g. a storm formed with no earlier weather signal]`. Forecast data (TAFs) would fix that.
> Our limits: the file is a **1% sample** of flights; we show a **capacity index**, not true AAR; there's **no wind direction or usable gust data**, so we assume worst-case crosswind; and the flight list is **simulated**, clearly labelled."

---

## 5 · Impact (0:20)
**Slide 4:** two numbers side by side, model vs baseline: **hit rate** (severe-delay flights flagged ≥ 3 h ahead) and **false-alarm rate**.

**Script:**
> "Measured on the test period: we flag `[BE: x]`% of severe-delay flights at least three hours ahead, against `[BE: y]`% for the baseline, with a false-alarm rate of `[BE: z]`%.
> That's measured. The fuel and delay savings that follow are estimates, and we keep them separate."

---

## 6 · Close (0:10)
**Slide 5:** "Production-ready needs:" full schedule data · wind direction · TAF forecasts · FAA AAR.

**Script:**
> "With full schedules, wind direction and TAF forecasts, this becomes a production tool. Today, it's an honest one. Thank you."

---

## Rehearsal checklist
- [ ] All `[BE: …]` placeholders filled with measured numbers (no estimates)
- [ ] Every severe rate quoted with its definition ("> 45 min late or cancelled") and its count (n = …)
- [ ] `timezone_fix.png` and `severe_by_weather.png` placed on slides 2 and 1
- [ ] Demo date is in the test period (Apr–Jul 2025), so no yellow banner appears
- [ ] Spoken run-through under 2:50, three times in a row
- [ ] Backup screenshots and recording on the laptop *and* a USB stick
- [ ] Failure case included (never cut, rubric requirement)
- [ ] The words "suggests" / "controller decides" are spoken at least once

## Likely judge questions (prepared answers)
| Question | Answer |
|---|---|
| "Where does this fail, and how would the user know?" | Failure case slide; on screen: confidence level with reasons, the refusal outside 3–12 h, and timestamps on every reason |
| "Why not true AAR?" | It isn't in the provided data; the file is a 1% sample. The capacity index is our transparent substitute; FAA AAR would plug in directly. |
| "How do you handle runway direction?" | Crosswind/tailwind function using ATL 80° and DFW 180°; no wind direction in the file, so worst case is assumed and stated |
| "Is there leakage?" | Only weather observed before the forecast time is used; automated leakage test; date-based split with a buffer |
| "Does it work for other airports?" | Airport-agnostic features and config-driven airports; transfer testing is a stated next step |
| "Are those flights real?" | No, they're simulated, labelled on every row, and each shows the hour's risk |
