"""The one interface the front end imports (04 §4):

    predict(airport, target_hour_utc, now_utc) -> dict   # never raises

Order of checks (02 A4 step 1): on the hour -> airport known -> in data range -> 3 <= lead <= 12
-> weather observed within 12 h before now -> otherwise refuse with the matching code.
Features are built AS OF now_utc with the SAME code as training (backend.features).
"""
import json
from datetime import datetime
from functools import lru_cache

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

from backend import drivers as D
from backend.clean_flights import assign_split
from backend.common import config, path
from backend.features import FEATURES, MAX_OBS_AGE_H
from backend.rules import recommendation
from backend.delay_estimate import delay_estimate

SCHEMA_VERSION = config()["schema_version"]
PKEYS = ["p_gt15", "p_gt30", "p_gt45", "p_gt60"]
AAR_NOTE = ("Range not shown: the sample has about one arrival per hour, too few for a "
            "meaningful interval.")  # L-008, verbatim


@lru_cache(maxsize=1)
def _load():
    m = path("models_dir")
    card = json.loads((m / "model_card.json").read_text())
    delay = lgb.Booster(model_file=str(m / "delayband.txt"))
    cap = lgb.Booster(model_file=str(m / "capacity.txt"))
    for b in (delay, cap):  # saved models contain only the best iterations
        assert b.feature_name() == FEATURES, "model features differ from backend.features.FEATURES"
    ctx = joblib.load(m / "context.joblib")
    return card, delay, cap, ctx


def _ts(s: str) -> pd.Timestamp:
    if not isinstance(s, str) or not s.endswith("Z"):
        raise ValueError(f"expected UTC ISO-8601 string ending in 'Z', got {s!r}")
    return pd.Timestamp(datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ"), tz="UTC")


def _fmt(ts) -> str:
    return pd.Timestamp(ts).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalise_airport(code) -> str | None:
    if not isinstance(code, str):
        return None
    c = code.strip().upper()
    if c in config()["airports"]:
        return c
    for iata, a in config()["airports"].items():
        if a["icao"] == c:
            return iata
    return None


def _refuse(req, code, message):
    return {"schema_version": SCHEMA_VERSION, "status": "refused", "request": req,
            "refusal": {"code": code, "message": message}, "error": None}


def _error(req, message):
    return {"schema_version": SCHEMA_VERSION, "status": "error", "request": req, "refusal": None,
            "error": {"code": "INTERNAL", "message": message}}


def predict(airport: str, target_hour_utc: str, now_utc: str) -> dict:
    """Never raises. Always returns a dict that validates against contract/schema.json."""
    req = {"airport": airport if isinstance(airport, str) else str(airport),
           "target_hour_utc": target_hour_utc if isinstance(target_hour_utc, str) else str(target_hour_utc),
           "now_utc": now_utc if isinstance(now_utc, str) else str(now_utc), "lead_time_h": None}
    try:
        return _predict(req, airport, target_hour_utc, now_utc)
    except Exception as e:  # noqa: BLE001 - contract: never raise
        return _error(req, f"{type(e).__name__}: {e}")


def _predict(req, airport, target_hour_utc, now_utc):
    cfg = config()
    try:
        T, now = _ts(target_hour_utc), _ts(now_utc)
    except ValueError as e:
        return _error(req, f"Invalid time format: {e}")
    lead_exact = (T - now) / pd.Timedelta(hours=1)
    if float(lead_exact).is_integer():
        req["lead_time_h"] = int(lead_exact)

    # 1. on the hour
    for name, t in (("Target hour", T), ("Current time", now)):
        if t.minute or t.second:
            return _refuse(req, "NOT_ON_THE_HOUR",
                           f"{name} {_fmt(t)[11:16]} UTC is not on the hour. Forecasts are for whole "
                           "hours only (e.g. 18:00).")
    # 2. airport
    ap = _normalise_airport(airport)
    if ap is None:
        known = ", ".join(f"{k} ({v['icao']})" for k, v in cfg["airports"].items())
        return _refuse(req, "UNKNOWN_AIRPORT", f"Airport '{airport}' is not supported. This tool covers {known}.")
    req["airport"] = ap
    # 3. data range
    lo, hi = pd.Timestamp(cfg["data_range_utc"]["start"]), pd.Timestamp(cfg["data_range_utc"]["end"])
    for name, t in (("Target hour", T), ("Current time", now)):
        if not (lo <= t <= hi):
            return _refuse(req, "OUT_OF_DATA_RANGE",
                           f"{name} {_fmt(t)} is outside the data available to this tool "
                           f"({_fmt(lo)[:10]} to {_fmt(hi)[:10]}).")
    # 4. lead time
    L = int(lead_exact)
    lmin, lmax = cfg["lead_time_hours"]["min"], cfg["lead_time_hours"]["max"]
    if L < lmin:
        when = "in the past" if L <= 0 else f"only {L} h ahead"
        return _refuse(req, "LEAD_TOO_SHORT",
                       f"{_fmt(T)[11:16]} UTC is {when}. Below {lmin} h, current observations and "
                       f"controller judgement are more reliable. This tool forecasts {lmin} to {lmax} h ahead.")
    if L > lmax:
        return _refuse(req, "LEAD_TOO_LONG",
                       f"{_fmt(T)[11:16]} UTC is {L} h ahead. Beyond {lmax} h, weather (especially "
                       f"thunderstorms) is too unreliable to forecast delays usefully. This tool "
                       f"forecasts {lmin} to {lmax} h ahead.")
    # 5. recent weather
    card, m_delay, m_cap, ctx = _load()
    wx = ctx.wx[ap]
    past = wx.loc[wx["obs_time_utc"] <= now, "obs_time_utc"]
    if past.empty or (now - past.max()) > pd.Timedelta(hours=MAX_OBS_AGE_H):
        last = "none" if past.empty else _fmt(past.max())
        return _refuse(req, "NO_RECENT_WEATHER",
                       f"No weather observation for {ap} in the {MAX_OBS_AGE_H} h before {_fmt(now)} "
                       f"(last: {last}). The tool refuses rather than guess.")

    # ---- features as of now (same code as training)
    X = ctx.hour_features(pd.Series([ap]), pd.Series([T]), pd.Series([L]))
    x = X.iloc[0]
    # ---- delay bands -> exceedance, rounded, monotone
    P = m_delay.predict(X[FEATURES])
    E = np.column_stack([P[:, i:].sum(axis=1) for i in range(1, 5)])[0]
    E = np.round(np.clip(E, 0, 1), 3)
    assert all(E[i] >= E[i + 1] for i in range(3)), "monotonicity violated"
    risk = {k: float(v) for k, v in zip(PKEYS, E)}
    # ---- capacity (L-008: no range)
    cap_index = round(float(m_cap.predict(X[FEATURES])[0]), 3)
    capacity = {"index": cap_index, "index_low": None, "index_high": None,
                "aar_est": None, "aar_low": None, "aar_high": None, "aar_note": AAR_NOTE}
    # ---- colour + DO (L-011: delay risk only)
    level, rec = recommendation(risk["p_gt45"], cap_index)
    # ---- WHY
    last_obs = now - pd.Timedelta(hours=float(x["obs_age_h"]))
    local = T.tz_convert(cfg["airports"][ap]["tz"])
    coco_label = wx.loc[wx["obs_time_utc"] == last_obs, "coco_label"]
    dctx = {"last_obs_utc": _fmt(last_obs), "issue_time": now, "local_hour": local.hour,
            "coco_label": None if coco_label.empty or pd.isna(coco_label.iloc[0]) else str(coco_label.iloc[0])}
    why = D.drivers(m_delay, X, FEATURES, level, dctx)
    # ---- confidence (config rules + L-010)
    cr, age = cfg["confidence_rules"], int(round(float(x["obs_age_h"])))
    reasons = [f"Lead time {L} h", f"Last weather reading {age} h before forecast"]
    no_flights = float(x["sched_deps_in_hour"]) == 0
    if L >= cr["low"]["min_lead_h"] or age >= cr["low"]["min_obs_age_h"] or no_flights:
        conf = "LOW"
        if no_flights:
            reasons.append("No scheduled flights in the sample for this hour")
    elif L <= cr["high"]["max_lead_h"] and age <= cr["high"]["max_obs_age_h"]:
        conf = "HIGH"
    else:
        conf = "MEDIUM"
    # ---- likely-delay range (v1.1) + period
    estimate = delay_estimate(risk)
    period = str(assign_split(pd.Series([T])).iloc[0]).upper()
    return {
        "schema_version": SCHEMA_VERSION, "status": "ok", "request": req,
        "risk_level": level, "hour_delay_risk": risk, "capacity": capacity, "drivers": why,
        "recommendation": rec, "confidence": {"level": conf, "reasons": reasons},
        "weather_basis": {"last_obs_utc": _fmt(last_obs), "obs_age_h": age},
        "delay_estimate": estimate, "data_period": period, "model_version": card["model_version"],
        "generated_at_utc": _fmt(now),  # = forecast issue time; keeps responses deterministic (D-027)
        "refusal": None, "error": None,
    }
