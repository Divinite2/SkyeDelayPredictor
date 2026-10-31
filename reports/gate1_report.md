# Gate 1 report: Checkpoint B-1, "The data can be trusted"

```
CHECKPOINT: B-1 (Gate 1)
DONE: A1.1-A1.5 · B1.1-B1.11 · V1-V10 all ✅ (plus the added check V3b ✅)
EVIDENCE: reports/validation_report.md · reports/figures/timezone_fix.png ·
          reports/figures/weather_coverage.png · reports/figures/severe_by_weather.png ·
          data/processed/weather_hourly.parquet · data/processed/flights_clean.parquet ·
          reports/decisions_log.md (D-007 to D-012)
NUMBERS:
  Rows 148,273 · 2023-01-01 → 2025-07-31 · ATL 8,415 dep / 5,429 arr · DFW 7,736 / 4,032  (all match B1.2)
  Time-zone repair, hottest hour (local), before → after:
    ATL summer 20 → 16 · ATL winter 21 → 16 · DFW summer 21 → 17 · DFW winter 20 → 14  (all within 13-18)
  Weather conflicts 0.071% of airport-hours with more than one reading (lead measured ~0.07%); 0.010% of all airport-hours
  Coverage: ATL 9.7 h/day, DFW 8.7 h/day with a reading; no day without any reading
  wpgt non-missing after zeros removed: 2.4% → dropped. snow: 0 non-zero values → dropped
  Cancelled 1,901 · diverted 377 · cancelled-with-delay 73 flagged · duplicates 0
  Severe (>45 min or cancelled), ATL+DFW: train 11.3% · validation 12.1% · test 17.8%
TRAPS TICKED: T5 · T6 · T7 · T9 · T10
KNOWN PROBLEMS / QUESTIONS: see below
```

## Points for the lead
1. **B1.8, weather-code check (partly matches).** Thunderstorm codes are the worst group with a usable sample:
   **convective 50.7% severe** (n = 69; 40.6% counting only flights that left > 45 min late),
   showers 35.5% (n = 107), rain 23.3%, clear/cloudy 10.5%. The lead's 45% falls between these two definitions.
   "Winter" shows 66.7%, but n = 21 and almost all of those are cancellations. Per T17 I'm treating it as too small to draw conclusions.
   **The mapping is confirmed, so I'm proceeding.** Flagged here because B1.8 says to tell the lead if the result differs.
2. **The test period is harder than training:** severe rate 17.8% vs 11.3% (summer storm season). This is expected
   and makes the test honest, but climatology (B0) will under-predict there. Expect worse absolute scores on test than on validation.
3. **Overall severe rate:** 9.7% in the documents. I get 10.1% counting only flights that left > 45 min late, and
   11.3% for 45_60 + gt60 including cancellations. That's because cancellations count as gt60, as the rules require.
4. **Deviations needing a look:** D-007 adds a time-zone table for all 350 airport codes, checked against the file at 100.00%.
