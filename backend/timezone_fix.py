"""A1.2 Time handling.

1. Flight times: local schedule -> UTC with zoneinfo (DST-aware).
   sched_dep_utc = localize(FL_DATE + CRS_DEP_TIME, tz(ORIGIN)) -> UTC
   sched_arr_utc = sched_dep_utc + CRS_ELAPSED_TIME minutes   (never CRS_ARR_TIME + date guess)
2. Weather keys: the provider matched LOCAL scheduled time as if it were UTC. So the weather on a
   row with local date D and local hour H is really the observation at UTC D H:00.
"""
import numpy as np
import pandas as pd

from backend.common import airport_tz


def hhmm_to_minutes(t: pd.Series) -> pd.Series:
    """HHMM integer -> minutes after local midnight. 2400 -> 1440 (next day 00:00)."""
    t = t.astype("Int64")
    h, m = t // 100, t % 100
    if ((m >= 60) | (h > 24)).fillna(False).any():
        raise ValueError("invalid HHMM value")
    return h * 60 + m


def local_to_utc(date: pd.Series, hhmm: pd.Series, airport: pd.Series) -> tuple[pd.Series, dict]:
    """Vectorised, DST-aware local->UTC per airport time zone.

    Nonexistent local times (spring-forward gap) are shifted forward; ambiguous ones (fall-back)
    are taken as the first occurrence (DST). Counts are returned for the validation report."""
    tzmap = airport_tz()
    missing = sorted(set(airport.dropna().unique()) - set(tzmap))
    if missing:
        raise KeyError(f"no time zone configured for airports: {missing}")
    naive = pd.to_datetime(date) + pd.to_timedelta(hhmm_to_minutes(hhmm).astype("float64"), unit="m")
    out = pd.Series(pd.NaT, index=date.index, dtype="datetime64[ns, UTC]")
    stats = {"nonexistent_shifted": 0, "ambiguous_resolved": 0}
    tz_of_row = airport.map(tzmap)
    for tz, idx in tz_of_row.groupby(tz_of_row).groups.items():
        s = naive.loc[idx]
        strict = s.dt.tz_localize(tz, ambiguous="NaT", nonexistent="NaT")
        loc = s.dt.tz_localize(tz, ambiguous=np.ones(len(s), dtype=bool), nonexistent="shift_forward")
        bad = strict.isna()
        if bad.any():
            # distinguish the two cases for reporting
            fwd = s[bad].dt.tz_localize(tz, ambiguous="NaT", nonexistent="shift_forward")
            stats["nonexistent_shifted"] += int(fwd.notna().sum())
            stats["ambiguous_resolved"] += int(fwd.isna().sum())
        out.loc[idx] = loc.dt.tz_convert("UTC")
    return out, stats


def add_utc_times(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    df["sched_dep_utc"], stats = local_to_utc(df["FL_DATE"], df["CRS_DEP_TIME"], df["ORIGIN"])
    df["sched_arr_utc"] = df["sched_dep_utc"] + pd.to_timedelta(
        df["CRS_ELAPSED_TIME"].astype("float64"), unit="m")
    df["overnight_arrival"] = (df["CRS_ARR_TIME"] < df["CRS_DEP_TIME"]).fillna(False)
    return df, stats


def verify_timezones(df: pd.DataFrame) -> dict:
    """Data-driven check of the tz table: the local arrival time implied by
    sched_arr_utc in tz(DEST) must equal CRS_ARR_TIME (mod 24 h). Mismatches point to a wrong
    time zone (or a data error) and are reported per airport."""
    tzmap = airport_tz()
    ok = df["sched_arr_utc"].notna()
    implied = pd.Series(np.nan, index=df.index)
    for tz, idx in df.loc[ok, "DEST"].map(tzmap).groupby(df.loc[ok, "DEST"].map(tzmap)).groups.items():
        loc = df.loc[idx, "sched_arr_utc"].dt.tz_convert(tz)
        implied.loc[idx] = loc.dt.hour * 60 + loc.dt.minute
    stated = hhmm_to_minutes(df["CRS_ARR_TIME"]).astype("float64") % 1440
    diff = ((implied - stated) % 1440).where(ok)
    match = (diff == 0)
    by_ap = (pd.DataFrame({"ap": df["ORIGIN"], "m": match})[ok]
             .groupby("ap")["m"].mean())
    by_dest = (pd.DataFrame({"ap": df["DEST"], "m": match})[ok]
               .groupby("ap")["m"].mean())
    return {"n_checked": int(ok.sum()), "match_rate": float(match[ok].mean()),
            "worst_origins": by_ap.sort_values().head(5).round(3).to_dict(),
            "worst_dests": by_dest.sort_values().head(5).round(3).to_dict(),
            "atl_dfw_match_rate": float(match[ok & (df["ORIGIN"].isin(["ATL", "DFW"])
                                                    | df["DEST"].isin(["ATL", "DFW"]))].mean())}


def weather_obs_time_utc(date: pd.Series, hhmm: pd.Series) -> pd.Series:
    """Repaired weather key: local date D + local hour H, re-read as UTC D H:00."""
    h = (hhmm.astype("Int64") // 100).astype("float64")
    return (pd.to_datetime(date) + pd.to_timedelta(h, unit="h")).dt.tz_localize("UTC")
