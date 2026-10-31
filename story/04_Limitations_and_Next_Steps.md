# Limitations and Next Steps (slide content)

**Checkpoint:** F-2 · Item 4 of 4
**Use:** Slide 3 (right half) in the pitch + a full backup slide for Q&A

---

## Slide version (6 bullets, read in ≈ 18 s)

**What our data can't tell us**
- **Sampled data:** the file holds ~1% of flights (about 6 ATL arrivals per day vs ~1,000 in reality), so hourly results are noisy
- **Capacity index, not true AAR:** share of scheduled arrivals delivered on time; true AAR isn't in the data
- **No wind direction or gust data:** crosswind computed against runway headings (ATL 80°, DFW 180°) assuming the worst case; gusts present in only 2.4% of rows, so not used
- **Harder test period:** summer 2025 has 17.8% severe (> 45 min late or cancelled) vs 11.3% in training
- **Simulated flight list:** example rows, labelled SIMULATED, each showing the hour's risk, not per-flight predictions
- **Repaired time stamps:** the provided weather was shifted 5–6 h; we corrected it and show the proof

---

## Full backup slide

### Data limitations (and how the user is protected)
| Limitation | Effect | How we handle it |
|---|---|---|
| ~1% flight sample | No real hourly arrival counts; noisy per-hour results | Probabilities and shares only; counts reported with every rate |
| No true AAR | Can't report the brief's exact metric | Capacity index scored with RMSE; stated openly; FAA AAR is a drop-in replacement |
| No wind direction | Exact crosswind impossible | Worst-case crosswind assumption; runway-heading function built and tested |
| Missing values stored as 0 in the source (gusts, snow) | Missing would read as calm | Treated as missing; snow dropped |
| Gust data present in only 2.4% of rows | Gust strength can't be used | Gust dropped under the 10%-present rule; stated |
| Test period harder than training (17.8% vs 11.3% severe) | Scores may look worse than on training data | Stated in the pitch; seasonal comparison with Apr–Jul 2023/2024 `[BE]` |
| Weather only ~9–10 h/day at ATL/DFW | Readings can be hours old | Observation age shown; confidence lowered; refusal if no reading in 12 h |
| Few storm examples (69 thunderstorm + 107 shower departures at ATL/DFW) | Less certainty in storm conditions | Explicit storm × time and storm × traffic features; counts reported |
| Data ends July 2025 | Test period limited to Apr–Jul 2025 | Stated; summer storm season still covered |

### Removed from scope → next steps
| Next step | Why it matters |
|---|---|
| Per-flight risk using real flight features | Targets individual flights instead of the hour |
| Probability calibration | Makes "38%" mean 38% more reliably |
| ATL ↔ DFW transfer test | Proves the pipeline generalises across airports |
| Extra weather factors (pressure trend, storm duration, knock-on delay, temperature extremes) | Captures more of the delay signal |
| 3-hour block scores | Matches how some flow programmes are planned |
| All 136 airports in the file | Broader coverage |
| Full schedule data, wind direction, TAF forecasts, FAA AAR | What makes it production-ready |

### What stays true regardless
- The tool **suggests; the controller decides.**
- It **refuses** outside 3–12 h rather than guessing.
- Every reason on screen carries a **timestamp observed before the forecast time.**
