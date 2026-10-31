"""WHY drivers (02 A4 step 7, 12 B3.3): LightGBM pred_contrib for the severe bands.

Contributions (raw-score space) for bands 45_60 and gt60 are summed per feature, then summed per
plain-language GROUP (e.g. hour_sin + hour_cos + evening_flag = "time of day") so one idea never
appears twice. Labelled "approximate influence" in the docs.

RED/AMBER: the top 3 groups that INCREASE severe-delay risk.
GREEN: the top 3 groups that DECREASE it (explains why the hour is calm; D-026).
Weather drivers carry the observation time (always <= now); others carry null.
"""
import calendar

import numpy as np
import pandas as pd

GROUPS = {
    "season": ["month"],
    "time_of_day": ["hour_sin", "hour_cos", "evening_flag"],
    "day_of_week": ["dow"],
    "traffic": ["rel_volume", "sched_deps_in_hour", "sched_arrs_in_hour"],
    "airport": ["airport_hist_severe_rate"],
    "pressure": ["pres_hpa"],
    "temperature": ["temp_c"],
    "wind": ["wspd_kmh", "crosswind_worst_kmh", "wspd_max_3h", "wspd_max_6h", "wspd_x_rel_volume"],
    "precip": ["prcp_mm", "prcp_sum_3h", "prcp_sum_6h"],
    "weather_type": ["coco_calm", "coco_low_visibility", "coco_rain", "coco_winter", "coco_showers"],
    "storm": ["coco_convective", "storm_last_6h", "hours_since_storm", "storm_x_evening",
              "storm_x_rel_volume"],
    "obs_age": ["obs_age_h"],
    "lead": ["lead_time_h"],
}
WEATHER_GROUPS = {"pressure", "temperature", "wind", "precip", "weather_type", "storm", "obs_age"}
SEASON = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring",
          6: "Summer", 7: "Summer", 8: "Summer", 9: "Autumn", 10: "Autumn", 11: "Autumn"}
COCO_NAMES = {"coco_calm": "Dry, no significant weather", "coco_low_visibility": "Fog / low visibility",
              "coco_rain": "Rain", "coco_winter": "Snow / freezing precipitation",
              "coco_showers": "Showers"}


def _fmt_ts(ts) -> str:
    return pd.Timestamp(ts).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def describe(group: str, x: pd.Series, ctx: dict, effect: str) -> dict:
    """Plain words for one driver group. x = the feature row; ctx = local time info etc."""
    up = effect == "increases"
    obs = ctx["last_obs_utc"]
    if group == "season":
        m = int(x["month"])
        s = SEASON[m]
        label = f"{s} {'peak ' if up and s == 'Summer' else ''}month"
        return {"label": label, "value": calendar.month_name[m], "observed_at_utc": None}
    if group == "time_of_day":
        h = ctx["local_hour"]
        part = ("Night" if h < 6 else "Morning" if h < 12 else "Afternoon" if h < 17
                else "Evening" if h <= 23 else "Night")
        return {"label": f"{part} hour", "value": f"{h:02d}:00 local", "observed_at_utc": None}
    if group == "day_of_week":
        return {"label": "Day of the week", "value": calendar.day_name[int(x["dow"])],
                "observed_at_utc": None}
    if group == "traffic":
        r = float(x["rel_volume"])
        label = "Busier than usual for this hour" if r > 1.05 else (
            "Quieter than usual for this hour" if r < 0.95 else "Normal traffic for this hour")
        return {"label": label, "value": f"{r:.1f}× the usual scheduled flights (sampled)",
                "observed_at_utc": None}
    if group == "airport":
        return {"label": "This airport's usual delay level",
                "value": f"{x['airport_hist_severe_rate']:.0%} of departures severely delayed (2023–24)",
                "observed_at_utc": None}
    if group == "pressure":
        p = float(x["pres_hpa"])
        label = "Low air pressure" if p < 1010 else "High air pressure" if p > 1020 else "Air pressure"
        return {"label": label, "value": f"{p:.0f} hPa", "observed_at_utc": obs}
    if group == "temperature":
        t = float(x["temp_c"])
        label = "Hot conditions" if t >= 30 else "Cold conditions" if t <= 0 else "Temperature"
        return {"label": label, "value": f"{t:.0f} °C", "observed_at_utc": obs}
    if group == "wind":
        w = np.nanmax([x["wspd_kmh"], x["wspd_max_6h"]])
        label = ("Strong wind (all treated as crosswind)" if w >= 25
                 else "Wind (all treated as crosswind)")
        return {"label": label, "value": f"up to {w:.0f} km/h in the last 6 h", "observed_at_utc": obs}
    if group == "precip":
        p = x["prcp_sum_6h"] if pd.notna(x["prcp_sum_6h"]) else x["prcp_mm"]
        label = "Recent rain" if (p or 0) > 0 else "No recent rain"
        return {"label": label, "value": f"{(p or 0):.1f} mm in the last 6 h", "observed_at_utc": obs}
    if group == "weather_type":
        k = next((c for c in COCO_NAMES if x.get(c, 0) == 1), None)
        return {"label": "Latest reported weather", "value": COCO_NAMES.get(k, ctx["coco_label"] or "unknown"),
                "observed_at_utc": obs}
    if group == "storm":
        hs = float(x["hours_since_storm"])
        if hs >= 168:
            return {"label": "No thunderstorm in the past week", "value": None, "observed_at_utc": obs}
        when = ctx["issue_time"] - pd.Timedelta(hours=hs)
        label = "Thunderstorm reported recently" if hs <= 6 else "Thunderstorm earlier"  # C4a (v1.1)
        return {"label": label, "value": f"{hs:.0f} h before the forecast",
                "observed_at_utc": _fmt_ts(when)}
    if group == "obs_age":
        return {"label": "Age of the latest weather reading", "value": f"{x['obs_age_h']:.0f} h",
                "observed_at_utc": obs}
    if group == "lead":
        return {"label": "Forecast lead time", "value": f"{x['lead_time_h']:.0f} h",
                "observed_at_utc": None}
    raise KeyError(group)


def drivers(model, X: pd.DataFrame, features: list, level: str, ctx: dict, k: int = 3) -> list:
    """X: one feature row (DataFrame). Returns 0-3 contract driver dicts, ordered by influence."""
    n_feat, n_cls = len(features), 5
    c = model.predict(X[features], pred_contrib=True)
    c = np.asarray(c).reshape(n_cls, n_feat + 1)  # per class: features..., bias
    severe = c[3, :n_feat] + c[4, :n_feat]       # bands 45_60 + gt60
    contrib = pd.Series(severe, index=features)
    g = pd.Series({name: contrib[cols].sum() for name, cols in GROUPS.items()})
    up = level in ("RED", "AMBER")
    g = g[g > 0].sort_values(ascending=False) if up else g[g < 0].sort_values()
    effect = "increases" if up else "decreases"
    out = []
    for name in g.index[:k]:
        d = describe(name, X.iloc[0], ctx, effect)
        out.append({"label": d["label"], "value": d["value"],
                    "observed_at_utc": d["observed_at_utc"], "effect": effect})
    return out
