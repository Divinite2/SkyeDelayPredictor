# User Story: Traffic Flow Controller at ATL / DFW

**Product:** Predictive Airport Capacity & Risk Model (Autonomous SG 2026, Airbus Track, Challenge #5)
**Checkpoint:** F-2 · Item 1 of 4

---

## The user
**A traffic flow controller (traffic management coordinator) at a major US hub: Atlanta (ATL) or Dallas Fort Worth (DFW).**

They plan how many aircraft the airport can accept each hour. They balance the published arrival rate against weather, runway use and demand. Their main lever is to slow traffic down *before* it arrives: reduce the arrival rate, or hold flights on the ground at their origin airports (a ground delay programme).

They work under time pressure and constant information load. They don't need another screen to explore. They need a quick, trustworthy answer to one question:

> *"Will this hour, several hours from now, be in trouble, and do I need to act now?"*

## What happens today (status quo)
1. Arrival rates are typically cut **when the weather arrives**, or shortly before, because longer-range weather is uncertain and the controller has no hour-by-hour risk estimate.
2. By then, many aircraft bound for the hub are **already airborne**.
3. Those aircraft are put into **airborne holding patterns**, burning fuel while circling.
4. Departing aircraft wait on **taxiways with engines running**.
5. Delays cascade: missed connections, crews running out of duty time, and **cancellations later in the day**.

## The cost
| Cost | Who pays |
|---|---|
| Fuel burned in holding and taxi queues | Airlines, environment |
| Delay minutes and missed connections | Passengers, airlines |
| Late-day cancellations | Passengers, airlines, airport |
| Workload spikes at the worst moment | Controllers |

*The brief states that severe weather accounts for over 70% of air traffic delays. In our own data, **11.3%** of ATL/DFW departures in the training period were severely delayed (**> 45 min late or cancelled**), rising to **17.8%** in the summer test period, and higher still in thunderstorms (`[BE: rate, n = 69]`, see `severe_by_weather.png`).*

## With our tool
1. The controller selects **an airport and an hour 3 to 12 hours ahead** and presses **Check**.
2. In about ten seconds of reading, they see:
   - **How risky that hour is:** RED / AMBER / GREEN, plus the chance of departure delays over 15, 30, 45 and 60 minutes, with >45 min highlighted as severe.
   - **Expected arrival capacity:** the share of scheduled arrivals likely to be delivered on time, with a range.
   - **Why:** the top three weather or traffic reasons, each with the time it was observed, so the controller can check it.
   - **What to consider:** a suggestion from a fixed, traceable rule (not AI).
   - **How confident the tool is,** and why.
3. If the warning is RED, the controller can **plan the reduction hours earlier**, while aircraft are still on the ground, where waiting is cheap and safe.
4. If the request is outside the 3–12 h window, the tool **refuses and says why**, rather than guessing.

## What we do NOT claim
- The tool **does not replace the controller's judgement.** It suggests; **the controller decides.**
- It doesn't predict individual flights. The flight list on screen is **SIMULATED** and shows the hour's risk.
- It doesn't produce a true FAA Arrival Acceptance Rate. It shows a transparent substitute (the capacity index) because AAR isn't in the provided data.

## One-line version
> *"A flow controller at ATL gets a RED warning for 18:00 at noon, with the reason ('thunderstorm reported at 11:00'), and can slow inbound traffic while those aircraft are still on the ground, instead of holding them in the air at 18:00."*
