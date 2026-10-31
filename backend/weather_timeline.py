"""A1.2 + A1.3 Build one cleaned hourly weather timeline per airport (keyed in UTC).

Sources: `_ORIGIN` weather (hour of CRS_DEP_TIME at ORIGIN) and `_DEST` weather (hour of
CRS_ARR_TIME at DEST). Overnight arrivals (CRS_ARR_TIME < CRS_DEP_TIME) are excluded from the
`_DEST` side because their weather date is ambiguous. Values are cleaned per source row first,
then combined per (airport, obs_time_utc): median for numeric columns, mode for `coco`.
"""
import numpy as np
import pandas as pd

from backend.timezone_fix import weather_obs_time_utc

NUMERIC = ["temp", "prcp", "wspd", "wpgt", "pres"]
OUT_NAMES = {"temp": "temp_c", "prcp": "prcp_mm", "wspd": "wspd_kmh", "wpgt": "wpgt_kmh",
             "pres": "pres_hpa"}
RANGES = {"temp": (-40, 55), "pres": (900, 1100), "wspd": (0, 200), "prcp": (0, 200),
          "wpgt": (0, 300)}  # wpgt bound not in 02; set generously so only nonsense is nulled

# 04 §7 (Meteostat convention)
COCO_LABEL = {1: "Clear", 2: "Fair", 3: "Cloudy", 4: "Overcast", 5: "Fog", 6: "Freezing fog",
              7: "Light rain", 8: "Rain", 9: "Heavy rain", 10: "Freezing rain",
              11: "Heavy freezing rain", 12: "Sleet", 13: "Heavy sleet", 14: "Light snow",
              15: "Snow", 16: "Heavy snow", 17: "Rain shower", 18: "Heavy rain shower",
              19: "Sleet shower", 20: "Heavy sleet shower", 21: "Snow shower",
              22: "Heavy snow shower", 23: "Lightning", 24: "Hail", 25: "Thunderstorm",
              26: "Heavy thunderstorm", 27: "Storm"}


def coco_group(code: float) -> str | None:
    if pd.isna(code):
        return None
    c = int(code)
    if 1 <= c <= 4: return "calm"
    if 5 <= c <= 6: return "low_visibility"
    if 7 <= c <= 9: return "rain"
    if 10 <= c <= 16: return "winter"
    if 17 <= c <= 22: return "showers"
    if 23 <= c <= 27: return "convective"
    return None


def stack_sources(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (source flight row, side) with raw weather + repaired UTC key."""
    parts = []
    for side, ap_col, t_col, keep in (
            ("ORIGIN", "ORIGIN", "CRS_DEP_TIME", pd.Series(True, index=df.index)),
            ("DEST", "DEST", "CRS_ARR_TIME", ~df["overnight_arrival"])):
        sub = df.loc[keep]
        p = pd.DataFrame({"airport": sub[ap_col].astype(str),
                          "obs_time_utc": weather_obs_time_utc(sub["FL_DATE"], sub[t_col]),
                          "side": side})
        for v in NUMERIC + ["snow", "coco"]:
            p[v] = sub[f"{v}_{side}"].astype("float64").to_numpy()
        parts.append(p)
    return pd.concat(parts, ignore_index=True)


def clean_values(src: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """A1.3 on source rows: fake zeros -> null, range violations -> null, invalid coco -> null."""
    src = src.copy()
    stats = {"rows": len(src)}
    stats["snow_nonzero"] = int((src["snow"].fillna(0) != 0).sum())
    src = src.drop(columns="snow")
    stats["wpgt_zero_to_null"] = int((src["wpgt"] == 0).sum())
    src.loc[src["wpgt"] == 0, "wpgt"] = np.nan
    stats["range_nulled"] = {}
    for v, (lo, hi) in RANGES.items():
        bad = src[v].notna() & ((src[v] < lo) | (src[v] > hi))
        stats["range_nulled"][v] = int(bad.sum())
        src.loc[bad, v] = np.nan
    valid = src["coco"].isin(list(COCO_LABEL))
    stats["coco_invalid_to_null"] = int((src["coco"].notna() & ~valid).sum())
    src.loc[~valid, "coco"] = np.nan
    return src, stats


def _mode(s: pd.Series):
    s = s.dropna()
    return np.nan if s.empty else s.value_counts().sort_index().idxmax()


def build_weather_hourly(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    src, stats = clean_values(stack_sources(df))
    g = src.groupby(["airport", "obs_time_utc"], sort=True)
    out = g[NUMERIC].median()
    out["coco"] = g["coco"].agg(_mode)
    out["n_source_rows"] = g.size()
    # conflict: any variable with >1 distinct non-null value among the source rows
    nun = g[NUMERIC + ["coco"]].nunique()
    out["conflict_flag"] = (nun > 1).any(axis=1)
    out = out.reset_index().rename(columns=OUT_NAMES)
    out["coco"] = out["coco"].astype("Int64")
    out["coco_label"] = out["coco"].map(COCO_LABEL).astype("string")
    out["coco_group"] = out["coco"].map(coco_group).astype("string")
    multi = out["n_source_rows"] > 1
    stats.update({
        "airport_hours": len(out),
        "airport_hours_multi_source": int(multi.sum()),
        "conflicts": int(out["conflict_flag"].sum()),
        "conflict_rate_all": float(out["conflict_flag"].mean()),
        "conflict_rate_multi": float(out.loc[multi, "conflict_flag"].mean()),
        "wpgt_nonnull_share": float(out["wpgt_kmh"].notna().mean()),
        "overnight_excluded_dest_rows": int(df["overnight_arrival"].sum()),
    })
    # A1.3: keep wpgt only if >10% non-null after zero->null
    stats["wpgt_kept"] = stats["wpgt_nonnull_share"] > 0.10
    if not stats["wpgt_kept"]:
        out = out.drop(columns="wpgt_kmh")
    return out, stats


def inspect_extremes(df: pd.DataFrame) -> pd.DataFrame:
    """Rows carrying the wpgt=216 / wspd=98.3 extremes noted by the lead (02 §A1.3)."""
    m = pd.Series(False, index=df.index)
    for side in ("ORIGIN", "DEST"):
        m |= df[f"wpgt_{side}"].astype("float64").ge(200) | df[f"wspd_{side}"].astype("float64").ge(90)
    cols = ["FL_DATE", "ORIGIN", "DEST", "CRS_DEP_TIME", "CRS_ARR_TIME"] + [
        f"{v}_{s}" for s in ("ORIGIN", "DEST") for v in ("temp", "wspd", "wpgt", "pres", "coco")]
    return df.loc[m, cols]
