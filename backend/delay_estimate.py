"""Likely-delay range for one airport-hour (v1.1, docs/16 §2). Pure function, no model calls.

Input: the four exceedance probabilities P(>15), P(>30), P(>45), P(>60) from the delay-band model.
Output (contract field `delay_estimate`):
  typical_text  : MIDDLE ESTIMATE (median band). First k with P(>k) < typical_prob -> band just
                  below k. Half of departures in this hour are expected to be shorter than its top.
  bad_case_text : BAD CASE (1-in-4). Largest k with P(>k) >= bad_case_prob -> "more than k min";
                  if even P(>15) < bad_case_prob -> "15 min or less".
  bad_case_prob : P(>k) for that k (or P(>15) when no threshold reaches the level).
Cut-offs come from config.yaml -> delay_estimate. Ranges, never a single number of minutes,
because the model predicts bands and the top band (>60, includes cancellations) is open-ended.
"""
from backend.common import config

KEYS = [(15, "p_gt15"), (30, "p_gt30"), (45, "p_gt45"), (60, "p_gt60")]
BAND_BELOW = {15: "under 15 min", 30: "15–30 min", 45: "30–45 min", 60: "45–60 min"}


def delay_estimate(risk: dict) -> dict:
    cfg = config()["delay_estimate"]
    q_typ, q_bad = float(cfg["typical_prob"]), float(cfg["bad_case_prob"])
    typical = "over 60 min"
    for k, key in KEYS:
        if risk[key] < q_typ:
            typical = BAND_BELOW[k]
            break
    bad, bad_p = "15 min or less", risk["p_gt15"]
    for k, key in reversed(KEYS):
        if risk[key] >= q_bad:
            bad, bad_p = f"more than {k} min", risk[key]
            break
    return {
        "typical_text": typical,
        "bad_case_text": bad,
        "bad_case_prob": round(float(bad_p), 3),
        "bad_case_level": q_bad,
        "method": (f"Middle estimate = median delay band (half of departures shorter). "
                   f"Bad case = largest delay with at least a {q_bad:.0%} chance."),
    }
