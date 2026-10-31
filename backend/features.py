"""A2 Leakage-safe, hour-level features (02 §A2, 08 B2.1/B2.2).

Each row asks: "standing at issue time t, what happens in target hour T = t + L?"  (L = 3..12).
Weather comes ONLY from the hourly timeline with obs_time_utc <= t. The same functions are used
for training, evaluation and (later) predict(), so the logic exists once.

Features are hour-level: every flight in the same (airport, T, L) gets the same feature vector.
The delay-band model and the capacity model share this feature set.
"""
import numpy as np
import pandas as pd

from backend.clean_flights import assign_split
from backend.common import config, path

HUBS = list(config()["airports"])
LEADS = list(range(config()["lead_time_hours"]["min"], config()["lead_time_hours"]["max"] + 1))
COCO_GROUPS = ["calm", "low_visibility", "rain", "winter", "showers", "convective"]
STORM_CAP_H = 168          # hours_since_storm is capped at one week
MAX_OBS_AGE_H = 12         # older than this -> predict() refuses (NO_RECENT_WEATHER); rows dropped

WEATHER_FEATURES = (["temp_c", "prcp_mm", "wspd_kmh", "pres_hpa", "obs_age_h"]
                    + [f"coco_{g}" for g in COCO_GROUPS]
                    + ["wspd_max_3h", "wspd_max_6h", "prcp_sum_3h", "prcp_sum_6h",
                       "storm_last_6h", "hours_since_storm", "crosswind_worst_kmh"])
FEATURES = WEATHER_FEATURES + [
    "hour_sin", "hour_cos", "evening_flag", "dow", "month",
    "sched_deps_in_hour", "sched_arrs_in_hour", "rel_volume",
    "storm_x_evening", "storm_x_rel_volume", "wspd_x_rel_volume",
    "lead_time_h", "airport_hist_severe_rate"]


# --------------------------------------------------------------------------- runway wind (B2.2)
def wind_components(wspd, wdir_deg, runway_heading_deg):
    """Split a wind into head/cross/tail components for one runway direction.

    wspd: wind speed (any unit); wdir_deg: direction the wind blows FROM (meteorological);
    runway_heading_deg: magnetic/true heading of the runway in use (e.g. 80 for ATL 08).
    Returns (headwind, crosswind, tailwind), all >= 0; headwind and tailwind are exclusive.
    NOTE: the provided data has no wind direction, so the model uses the worst case
    crosswind = wspd (see crosswind_worst_kmh). This function shows the method (trap T2)."""
    wspd = np.asarray(wspd, dtype=float)
    ang = np.deg2rad(np.asarray(wdir_deg, dtype=float) - runway_heading_deg)
    along = wspd * np.cos(ang)                       # + = headwind, - = tailwind
    cross = np.abs(wspd * np.sin(ang))
    head = np.clip(along, 0, None)
    tail = np.clip(-along, 0, None)
    return head, cross, tail


# --------------------------------------------------------------------------- weather @ t
def weather_features(wx_ap: pd.DataFrame, issue_times: pd.Series) -> pd.DataFrame:
    """Weather features for ONE airport at each issue time t, using only obs_time_utc <= t.

    wx_ap: rows of weather_hourly for one airport. issue_times: tz-aware UTC hourly timestamps.
    Pure function of (timeline, t): used by training, predict() and the leakage test."""
    idx = issue_times.index
    t = pd.DatetimeIndex(pd.to_datetime(issue_times, utc=True)).as_unit("ns")
    out = pd.DataFrame(index=idx)
    wx_ap = wx_ap.sort_values("obs_time_utc")
    if wx_ap.empty:
        for c in WEATHER_FEATURES:
            out[c] = np.nan
        return out
    obs_t = pd.DatetimeIndex(wx_ap["obs_time_utc"]).tz_convert("UTC").as_unit("ns")

    # latest observation at or before t (merge_asof backward, as specified)
    q = pd.DataFrame({"t": t, "_i": np.arange(len(t))}).sort_values("t")
    latest = pd.merge_asof(q, wx_ap.assign(obs_time_utc=obs_t), left_on="t",
                           right_on="obs_time_utc", direction="backward").sort_values("_i")
    for c in ["temp_c", "prcp_mm", "wspd_kmh", "pres_hpa"]:
        out[c] = latest[c].to_numpy(dtype=float)
    out["obs_age_h"] = ((latest["t"] - latest["obs_time_utc"]).dt.total_seconds() / 3600).to_numpy()
    grp = latest["coco_group"].astype("object").fillna("").to_numpy()
    for g in COCO_GROUPS:
        out[f"coco_{g}"] = (grp == g).astype(float)

    # rolling windows on a full hourly grid ending at t: (t-w, t]
    start = min(obs_t.min(), t.min()) - pd.Timedelta(hours=STORM_CAP_H)
    grid = pd.date_range(start.floor("h"), t.max(), freq="h").as_unit("ns")
    pos_obs = grid.get_indexer(obs_t)
    keep = pos_obs >= 0  # obs after max(t) are outside the grid -> cannot be used anyway
    n = len(grid)
    wspd = np.full(n, np.nan); prcp = np.full(n, np.nan); storm = np.zeros(n)
    wspd[pos_obs[keep]] = wx_ap["wspd_kmh"].to_numpy(dtype=float)[keep]
    prcp[pos_obs[keep]] = wx_ap["prcp_mm"].to_numpy(dtype=float)[keep]
    storm[pos_obs[keep]] = (wx_ap["coco_group"].astype("object").fillna("").to_numpy()[keep] == "convective")
    ws, pr = pd.Series(wspd), pd.Series(prcp)
    roll = {"wspd_max_3h": ws.rolling(3, min_periods=1).max(),
            "wspd_max_6h": ws.rolling(6, min_periods=1).max(),
            "prcp_sum_3h": pr.rolling(3, min_periods=1).sum(),
            "prcp_sum_6h": pr.rolling(6, min_periods=1).sum(),
            "storm_last_6h": pd.Series(storm).rolling(6, min_periods=1).max()}
    # hours since last convective obs (<= t), capped
    last_storm = pd.Series(np.where(storm > 0, np.arange(n), np.nan)).ffill().to_numpy()
    since = np.minimum(np.arange(n) - last_storm, STORM_CAP_H)
    since = np.where(np.isnan(since), STORM_CAP_H, since)
    pos_t = grid.get_indexer(t)
    for k, s in roll.items():
        out[k] = s.to_numpy()[pos_t]
    out["hours_since_storm"] = since[pos_t]
    out["crosswind_worst_kmh"] = out["wspd_kmh"]  # worst case: all wind is crosswind (D6)
    return out


# --------------------------------------------------------------------------- schedule-based
class Context:
    """Everything known in advance that features need: weather timeline, schedule counts,
    training-period-only statistics. Built once; reused by training and predict()."""

    def __init__(self, flights: pd.DataFrame, wx: pd.DataFrame):
        self.wx = {ap: wx[wx["airport"] == ap].reset_index(drop=True) for ap in HUBS}
        hub_dep = flights[flights["airport_dep"].isin(HUBS)]
        hub_arr = flights[flights["airport_arr"].isin(HUBS)]
        deps = hub_dep.groupby(["airport_dep", hub_dep["sched_dep_utc"].dt.floor("h")]).size()
        arrs = hub_arr.groupby(["airport_arr", hub_arr["sched_arr_utc"].dt.floor("h")]).size()
        deps.index.names = arrs.index.names = ["airport", "hour"]
        self.deps, self.arrs = deps, arrs
        tr = config()["splits"]["train"]
        lo, hi = pd.Timestamp(tr["start"], tz="UTC"), pd.Timestamp(tr["end"], tz="UTC") + pd.Timedelta(days=1)
        # training-period hour-of-week mean of scheduled movements (deps + arrs), per airport
        self.how_mean = {}
        for ap in HUBS:
            hours = pd.date_range(lo, hi, freq="h", inclusive="left")
            mv = (deps.get(ap, pd.Series(dtype=float)).reindex(hours, fill_value=0)
                  + arrs.get(ap, pd.Series(dtype=float)).reindex(hours, fill_value=0))
            loc = hours.tz_convert(config()["airports"][ap]["tz"])
            self.how_mean[ap] = mv.groupby([loc.dayofweek, loc.hour]).mean()
        # training-period severe rate per airport (T13: no validation/test information)
        trn = hub_dep[hub_dep["split_dep"] == "train"]
        self.airport_rate = trn.groupby("airport_dep")["severe"].mean().to_dict()

    def hour_features(self, airport: pd.Series, target: pd.Series, lead: pd.Series) -> pd.DataFrame:
        """Feature matrix for (airport, target hour T, lead L); issue time t = T - L."""
        target = pd.to_datetime(target, utc=True)
        issue = target - pd.to_timedelta(lead.to_numpy(), unit="h")
        out = pd.DataFrame(index=target.index)
        parts = []
        for ap in airport.unique():
            m = (airport == ap).to_numpy()
            parts.append(weather_features(self.wx[ap], pd.Series(issue[m], index=target.index[m])))
        out = out.join(pd.concat(parts))
        out["airport"] = airport.to_numpy()
        # time of target hour, local
        hr = np.empty(len(out)); dow = np.empty(len(out)); mon = np.empty(len(out))
        for ap in airport.unique():
            m = (airport == ap).to_numpy()
            loc = pd.DatetimeIndex(target[m]).tz_convert(config()["airports"][ap]["tz"])
            hr[m], dow[m], mon[m] = loc.hour, loc.dayofweek, loc.month
        out["hour_sin"], out["hour_cos"] = np.sin(2 * np.pi * hr / 24), np.cos(2 * np.pi * hr / 24)
        out["evening_flag"] = ((hr >= 17) & (hr <= 23)).astype(float)
        out["dow"], out["month"] = dow, mon
        out["local_hour"] = hr  # not a model feature; used by climatology B0
        # traffic (scheduled = known in advance), normalised by the airport's own norm (T4)
        key = pd.MultiIndex.from_arrays([airport.to_numpy(), pd.DatetimeIndex(target)])
        out["sched_deps_in_hour"] = self.deps.reindex(key, fill_value=0).to_numpy(dtype=float)
        out["sched_arrs_in_hour"] = self.arrs.reindex(key, fill_value=0).to_numpy(dtype=float)
        norm = np.array([self.how_mean[a].get((int(d), int(h)), 0.0)
                         for a, d, h in zip(airport, dow, hr)])
        out["rel_volume"] = (out["sched_deps_in_hour"] + out["sched_arrs_in_hour"] + 0.5) / (norm + 0.5)
        # explicit interactions (D11)
        out["storm_x_evening"] = out["storm_last_6h"] * out["evening_flag"]
        out["storm_x_rel_volume"] = out["storm_last_6h"] * out["rel_volume"]
        out["wspd_x_rel_volume"] = out["wspd_kmh"] * out["rel_volume"]
        out["lead_time_h"] = lead.to_numpy(dtype=float)
        out["airport_hist_severe_rate"] = airport.map(self.airport_rate).to_numpy(dtype=float)
        out["issue_time_utc"], out["target_hour_utc"] = issue, target
        return out


# --------------------------------------------------------------------------- training rows
def build_rows(ctx: Context, flights: pd.DataFrame, kind: str) -> tuple[pd.DataFrame, dict]:
    """kind='dep': hub departures, label = delay_band.  kind='arr': hub arrivals, label = delivered.
    One row per (flight, lead). Split by TARGET hour; purge rows whose issue time is in an
    earlier split (12 h buffer); drop rows with no weather obs in the 12 h before t."""
    if kind == "dep":
        f = flights[flights["airport_dep"].isin(HUBS)]
        ap, T, label = f["airport_dep"], f["sched_dep_utc"].dt.floor("h"), f["delay_band"]
        extra = {"severe": f["severe"]}
    else:
        f = flights[flights["airport_arr"].isin(HUBS) & flights["delivered"].notna()]
        ap, T, label = f["airport_arr"], f["sched_arr_utc"].dt.floor("h"), f["delivered"].astype(float)
        extra = {}
    base = pd.DataFrame({"flight_id": f["flight_id"], "airport": ap, "T": T, "label": label, **extra})
    rows = base.loc[base.index.repeat(len(LEADS))].reset_index(drop=True)
    rows["lead"] = np.tile(LEADS, len(base))
    X = ctx.hour_features(rows["airport"], rows["T"], rows["lead"])
    rows = pd.concat([rows.drop(columns=["airport"]), X], axis=1)
    rows["split"] = assign_split(rows["target_hour_utc"])
    stats = {"rows_before": len(rows)}
    purge = assign_split(rows["issue_time_utc"]) != rows["split"]
    stale = rows["obs_age_h"].isna() | (rows["obs_age_h"] > MAX_OBS_AGE_H)
    stats["purged_boundary"] = int(purge.sum())
    stats["dropped_no_recent_weather"] = int((stale & ~purge).sum())
    rows = rows[~purge & ~stale].reset_index(drop=True)
    stats["rows_per_split"] = rows["split"].value_counts().to_dict()
    stats["flights_per_split"] = rows.groupby("split")["flight_id"].nunique().to_dict()
    return rows, stats


def save_rows(rows: pd.DataFrame, prefix: str):
    for s, part in rows.groupby("split"):
        part.to_parquet(path("processed_dir") / f"{prefix}_{s}.parquet", index=False)
