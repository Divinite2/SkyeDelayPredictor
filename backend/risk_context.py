"""Where this hour's severe-delay risk sits on the scale the colours come from (v1.2).

Explains the colour without changing it. The RED/AMBER cut-offs (config risk_rules, L-011) are
the 90th/70th percentiles of hour-level P(>45) on VALIDATION. config risk_scale.quantiles holds
the same distribution (0th–100th percentile), so:
  typical_p        : the median validation hour (a "typical hour")
  ratio_to_typical : P(>45) / typical_p
  percentile       : share of validation hours with lower risk (linear between stored
                     quantiles, capped at 99)
run_all.py checks that the stored quantiles still match the validation predictions.
Pure function, no model calls. Never decides the colour (backend.rules does).
"""
import numpy as np

from backend.common import config


def risk_context(p45: float) -> dict:
    cfg = config()
    rs, rr = cfg["risk_scale"], cfg["risk_rules"]
    q = {int(k): float(v) for k, v in rs["quantiles"].items()}
    pcts = sorted(q)
    vals = [q[k] for k in pcts]
    typical = q[50]
    pctile = float(np.interp(float(p45), vals, pcts))  # clamps to 0 / 100 outside the range
    return {
        "typical_p": round(typical, 3),
        "ratio_to_typical": round(float(p45) / typical, 1),
        "percentile": min(99, int(round(pctile))),  # never "riskier than 100%"
        "amber_min": rr["amber"]["p_gt45_min"],
        "red_min": rr["red"]["p_gt45_min"],
        "scale_max": float(rs["scale_max"]),
        "basis": rs["basis"],
    }
