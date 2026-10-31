# Failure cases (B2.10)

Severe = **> 45 min late or cancelled**. Every rate shows its count. Picked automatically by rule (miss = GREEN hour with the highest observed severe share; false alarm = RED hour with all flights on time and the highest P(>45)); the reasons were then checked by hand.

## Validation set (6 h ahead)

Candidate hours: 1145 airport-hours. Risk from the STARTING config rules (RED: P(>45) ≥ 0.3 or capacity ≤ 0.6; AMBER: P(>45) ≥ 0.15 or capacity ≤ 0.8). Rule tuning is B3.2.

Risk-level distribution: GREEN 617, AMBER 493, RED 35

### Miss (GREEN predicted, severe delays happened): ATL, target hour 2025-02-13 22:00Z (Thu 17:00 local), forecast issued 2025-02-13 16:00Z (6 h ahead)

**Prediction:** risk **GREEN** · P(>45) = 0.081 · P(>15) = 0.159 · capacity index 0.84

**What happened (n = 2 sampled departures):** 2 severe (> 45 min late or cancelled), 0 on time (≤ 15 min). Delays: DL → LAS: +963 min, DL → LEX: +174 min

**Inputs the model saw (weather as of the issue time):**

- last observation 2025-02-13 16:00Z (age 0 h): temp 11.7 °C, wind 16.6 km/h, precip 0.0 mm, pressure 1021.4 hPa, group calm
- storm in last 6 h: 0 · hours since storm: 168 · max wind 6 h: 16.6 km/h · precip 6 h: 0.0 mm
- evening flag 1 · relative traffic 1.91 · scheduled deps/arrs in hour (sample) 2/0

**Weather observed after the forecast was issued (not available to the model):**

| obs_time_utc      |   temp_c |   prcp_mm |   wspd_kmh |   coco | coco_label   |
|:------------------|---------:|----------:|-----------:|-------:|:-------------|
| 2025-02-13 17:00Z |     13.3 |         0 |       22.3 |      3 | Cloudy       |
| 2025-02-13 18:00Z |     15   |         0 |       24.1 |      3 | Cloudy       |
| 2025-02-13 21:00Z |     15.6 |         0 |       27.7 |      3 | Cloudy       |
| 2025-02-13 22:00Z |     14.4 |         0 |       22.3 |      3 | Cloudy       |

**Reason (analysis):** weather at and after the issue time was benign, so the delay most likely had a non-weather cause (late inbound aircraft, carrier or NAS delay) that is outside the model's inputs; with ~1 sampled flight per hour, one flight decides the hour.

**What would fix it:** forecast weather (TAF / convective outlooks) instead of only past observations; a full flight schedule (real hourly volume and inbound delays); more frequent observations (METAR every hour instead of ~9-10 per day).

### False alarm (RED predicted, all flights on time): DFW, target hour 2025-03-28 23:00Z (Fri 18:00 local), forecast issued 2025-03-28 17:00Z (6 h ahead)

**Prediction:** risk **RED** · P(>45) = 0.355 · P(>15) = 0.527 · capacity index 0.53

**What happened (n = 1 sampled departures):** 0 severe (> 45 min late or cancelled), 1 on time (≤ 15 min). Delays: AA → TUS: -3 min

**Inputs the model saw (weather as of the issue time):**

- last observation 2025-03-28 17:00Z (age 0 h): temp 20.0 °C, wind 16.6 km/h, precip 0.0 mm, pressure 1013.8 hPa, group rain
- storm in last 6 h: 0 · hours since storm: 168 · max wind 6 h: 25.9 km/h · precip 6 h: 5.4 mm
- evening flag 1 · relative traffic 1.22 · scheduled deps/arrs in hour (sample) 1/0

**Weather observed after the forecast was issued (not available to the model):**

| obs_time_utc      |   temp_c |   prcp_mm |   wspd_kmh |   coco | coco_label   |
|:------------------|---------:|----------:|-----------:|-------:|:-------------|
| 2025-03-28 18:00Z |     21.1 |         0 |       18.4 |      4 | Overcast     |
| 2025-03-28 19:00Z |     21.7 |         0 |       20.5 |      4 | Overcast     |
| 2025-03-28 21:00Z |     21.7 |         0 |       20.5 |      4 | Overcast     |
| 2025-03-28 22:00Z |     21.1 |         0 |       22.3 |      4 | Overcast     |

**Reason (analysis):** the observations after the issue time show the weather had cleared.

**What would fix it:** forecast weather (TAF) to tell when a storm will end; calibrated RED thresholds tuned on validation to a stated false-alarm rate (B3.2); a full sample of flights per hour.

## Test set (6 h ahead)

Candidate hours: 1658 airport-hours. Risk from the STARTING config rules (RED: P(>45) ≥ 0.3 or capacity ≤ 0.6; AMBER: P(>45) ≥ 0.15 or capacity ≤ 0.8). Rule tuning is B3.2.

Risk-level distribution: AMBER 854, GREEN 643, RED 161

### Miss (GREEN predicted, severe delays happened): ATL, target hour 2025-06-28 12:00Z (Sat 08:00 local), forecast issued 2025-06-28 06:00Z (6 h ahead)

**Prediction:** risk **GREEN** · P(>45) = 0.099 · P(>15) = 0.233 · capacity index 0.82

**What happened (n = 2 sampled departures):** 2 severe (> 45 min late or cancelled), 0 on time (≤ 15 min). Delays: DL → DEN: +248 min, F9 → CLE: +83 min

**Inputs the model saw (weather as of the issue time):**

- last observation 2025-06-27 23:00Z (age 7 h): temp 30.6 °C, wind 16.6 km/h, precip 0.0 mm, pressure 1016.9 hPa, group convective
- storm in last 6 h: 0 · hours since storm: 7 · max wind 6 h: nan km/h · precip 6 h: nan mm
- evening flag 0 · relative traffic 1.56 · scheduled deps/arrs in hour (sample) 2/0

**Weather observed after the forecast was issued (not available to the model):**

| obs_time_utc      |   temp_c |   prcp_mm |   wspd_kmh |   coco | coco_label   |
|:------------------|---------:|----------:|-----------:|-------:|:-------------|
| 2025-06-28 07:00Z |     22.2 |       0   |       18.4 |      3 | Cloudy       |
| 2025-06-28 08:00Z |     21.7 |       0.3 |        0   |      3 | Cloudy       |
| 2025-06-28 09:00Z |     21.7 |       0   |        9.4 |      2 | Fair         |
| 2025-06-28 10:00Z |     21.7 |       0   |        5.4 |      2 | Fair         |
| 2025-06-28 11:00Z |     21.7 |       0   |        5.4 |      3 | Cloudy       |
| 2025-06-28 12:00Z |     22.8 |       0   |        7.6 |      3 | Cloudy       |

**Reason (analysis):** the latest reading was already 7 h old.

**What would fix it:** forecast weather (TAF / convective outlooks) instead of only past observations; a full flight schedule (real hourly volume and inbound delays); more frequent observations (METAR every hour instead of ~9-10 per day).

### False alarm (RED predicted, all flights on time): DFW, target hour 2025-04-02 22:00Z (Wed 17:00 local), forecast issued 2025-04-02 16:00Z (6 h ahead)

**Prediction:** risk **RED** · P(>45) = 0.423 · P(>15) = 0.566 · capacity index 0.46

**What happened (n = 1 sampled departures):** 0 severe (> 45 min late or cancelled), 1 on time (≤ 15 min). Delays: DL → DTW: -9 min

**Inputs the model saw (weather as of the issue time):**

- last observation 2025-04-02 16:00Z (age 0 h): temp 18.3 °C, wind 18.4 km/h, precip 3.3 mm, pressure 1001.5 hPa, group rain
- storm in last 6 h: 0 · hours since storm: 168 · max wind 6 h: 37.1 km/h · precip 6 h: 3.8 mm
- evening flag 1 · relative traffic 1.08 · scheduled deps/arrs in hour (sample) 1/0

**Weather observed after the forecast was issued (not available to the model):**

| obs_time_utc      |   temp_c |   prcp_mm |   wspd_kmh |   coco | coco_label   |
|:------------------|---------:|----------:|-----------:|-------:|:-------------|
| 2025-04-02 17:00Z |     20.6 |         0 |       13   |      7 | Light rain   |
| 2025-04-02 18:00Z |     22.8 |         0 |        9.4 |      3 | Cloudy       |
| 2025-04-02 19:00Z |     24.4 |         0 |        5.4 |      4 | Overcast     |
| 2025-04-02 21:00Z |     25   |         0 |        9.4 |      4 | Overcast     |

**Reason (analysis):** the observations after the issue time show the weather had cleared.

**What would fix it:** forecast weather (TAF) to tell when a storm will end; calibrated RED thresholds tuned on validation to a stated false-alarm rate (B3.2); a full sample of flights per hour.

