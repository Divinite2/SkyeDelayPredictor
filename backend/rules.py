"""Fixed rule table: risk colour and the DO line (02 A4 step 5-6, lead decision L-011).

Colour is decided by delay risk only (L-011). Capacity conditions are kept in config as
`capacity_index_max: null` = disabled; if a number is ever configured again they apply.
No AI anywhere in this path (D8, T20).
"""
import numpy as np

from backend.common import config

TEXT = {
    "RED-1": "Consider a pre-emptive arrival-rate reduction or ground delay programme for this hour.",
    "AMBER-1": "Elevated risk: prepare contingency and re-check at the next forecast update.",
    "GREEN-1": "No action suggested by the model.",
}
GREEN_TRIGGER = "no RED or AMBER condition met"


def _cond(level: str, p45, cap):
    r = config()["risk_rules"][level]
    hit = np.asarray(p45, dtype=float) >= r["p_gt45_min"]
    if r.get("capacity_index_max") is not None and cap is not None:
        hit = hit | (np.asarray(cap, dtype=float) <= r["capacity_index_max"])
    return hit


def risk_level(p45, cap=None):
    """Vectorised colour. cap is ignored while capacity_index_max is null (L-011)."""
    red, amber = _cond("red", p45, cap), _cond("amber", p45, cap)
    return np.where(red, "RED", np.where(amber, "AMBER", "GREEN"))


def recommendation(p45: float, cap: float | None = None) -> tuple[str, dict]:
    level = str(risk_level(np.array([p45]), None if cap is None else np.array([cap]))[0])
    rr = config()["risk_rules"]
    if level == "GREEN":
        trig = GREEN_TRIGGER
    else:
        r = rr[level.lower()]
        parts = []
        if p45 >= r["p_gt45_min"]:
            parts.append(f"p_gt45 >= {r['p_gt45_min']:.3f} ({r.get('basis', 'configured threshold')})")
        if r.get("capacity_index_max") is not None and cap is not None and cap <= r["capacity_index_max"]:
            parts.append(f"capacity_index <= {r['capacity_index_max']}")
        trig = " and ".join(parts)
    rule_id = f"{level}-1"
    return level, {"rule_id": rule_id, "text": TEXT[rule_id], "triggered_by": trig}


def tune_thresholds(p45_hours: np.ndarray, red_q: float = 0.90, amber_q: float = 0.70) -> dict:
    """L-011: RED = validation 90th percentile of hour-level P(>45), AMBER = 70th."""
    return {"red": round(float(np.quantile(p45_hours, red_q)), 3),
            "amber": round(float(np.quantile(p45_hours, amber_q)), 3)}
