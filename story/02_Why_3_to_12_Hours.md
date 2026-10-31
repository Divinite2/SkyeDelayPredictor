# Why 3 to 12 Hours

**Checkpoint:** F-2 · Item 2 of 4

## Two-sentence version (for the pitch and the slide)
> **Under 3 hours, an experienced controller can already see the trend from radar, current observations and traffic, so a model adds little and could distract. Over 12 hours, weather, especially thunderstorms, is too unreliable, and false alarms would teach users to ignore the tool.**

## Shorter spoken version (≈ 8 seconds)
> *"Below three hours the controller already knows; beyond twelve the weather is guesswork. We forecast only the window in between, and refuse everything else."*

## Supporting table (backup slide or Q&A)
| Lead time | Decision | Reason |
|---|---|---|
| Under 3 h | **Refused** | Controller already sees the trend; the model adds little and could distract |
| **3–12 h** | **Forecast** | Early enough to act calmly (reduce arrival rates, hold aircraft at origin, warn airlines, adjust staffing); recent weather still carries signal |
| Over 12 h | **Refused** | Weather too unreliable; false alarms erode trust |

## How we prove it (placeholder for back-end numbers)
Accuracy is reported separately at **3, 6, 9 and 12 hours** against a simple baseline (climatology).

| Lead time | Model Brier (>45 min) | Baseline Brier | Better? |
|---|---|---|---|
| 3 h | `[BE: value]` | `[BE: value]` | `[✅/❌]` |
| 6 h | `[BE: value]` | `[BE: value]` | `[✅/❌]` |
| 9 h | `[BE: value]` | `[BE: value]` | `[✅/❌]` |
| 12 h | `[BE: value]` | `[BE: value]` | `[✅/❌]` |

*If the model doesn't beat the baseline at a lead time, we say so and mark that range as low confidence. That supports the 12 h limit rather than undermining it.*
