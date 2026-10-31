"""A1.4 Clean the flights: labels, cancellations, diversions, duplicates, splits."""
import numpy as np
import pandas as pd

from backend.common import config

BANDS = ["le15", "15_30", "30_45", "45_60", "gt60"]
KEY = ["FL_DATE", "OP_UNIQUE_CARRIER", "OP_CARRIER_FL_NUM", "ORIGIN", "DEST"]


def delay_band(delay: pd.Series, cancelled: pd.Series) -> pd.Series:
    """Ordered bands with strict '>' comparison (45 exactly is NOT > 45). Cancelled -> gt60."""
    d = delay.astype("float64")
    band = pd.Series(pd.NA, index=d.index, dtype="string")
    band[d.notna()] = "le15"
    for lo, name in zip(config()["delay_bands_min"], BANDS[1:]):
        band[d > lo] = name
    band[cancelled] = "gt60"
    return band


def assign_split(t: pd.Series) -> pd.Series:
    """Split by TARGET hour (UTC), per config.splits (end dates inclusive)."""
    s = pd.Series(pd.NA, index=t.index, dtype="string")
    for name, rng in config()["splits"].items():
        lo = pd.Timestamp(rng["start"], tz="UTC")
        hi = pd.Timestamp(rng["end"], tz="UTC") + pd.Timedelta(days=1)
        s[(t >= lo) & (t < hi)] = name
    return s


def clean_flights(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    stats = {}
    dups = int(df.duplicated(KEY).sum())
    stats["duplicates"] = dups
    if dups:
        raise AssertionError(f"{dups} duplicate flights on {KEY}")

    cancelled = df["CANCELLED"].astype("float64").eq(1)
    diverted = df["DIVERTED"].astype("float64").eq(1)
    dep_delay = df["DEP_DELAY"].astype("float64")
    arr_delay = df["ARR_DELAY"].astype("float64")
    cwd = cancelled & dep_delay.notna()
    stats.update({"cancelled": int(cancelled.sum()), "diverted": int(diverted.sum()),
                  "cancelled_with_delay": int(cwd.sum()),
                  "raw_cancelled": int(df["CANCELLED"].astype("float64").eq(1).sum()),
                  "raw_diverted": int(df["DIVERTED"].astype("float64").eq(1).sum()),
                  "missing_delay_not_cancelled": int((dep_delay.isna() & ~cancelled).sum())})

    out = pd.DataFrame({
        "flight_id": (df["FL_DATE"].astype(str).str.replace("-", "") + "-" + df["OP_UNIQUE_CARRIER"]
                      + df["OP_CARRIER_FL_NUM"].astype(str) + "-" + df["ORIGIN"] + "-" + df["DEST"]),
        "airport_dep": df["ORIGIN"], "airport_arr": df["DEST"],
        "sched_dep_utc": df["sched_dep_utc"], "sched_arr_utc": df["sched_arr_utc"],
        "carrier": df["OP_UNIQUE_CARRIER"],
        "dep_delay_min": dep_delay.where(~cancelled),   # cancellation wins
        "arr_delay_min": arr_delay.where(~cancelled & ~diverted),
        "cancelled": cancelled, "diverted": diverted, "cancelled_with_delay": cwd,
        # known-in-advance schedule fields (allowed features)
        "fl_date_local": df["FL_DATE"], "crs_dep_time": df["CRS_DEP_TIME"],
        "crs_arr_time": df["CRS_ARR_TIME"], "crs_elapsed_min": df["CRS_ELAPSED_TIME"],
        "distance_mi": df["DISTANCE"], "overnight_arrival": df["overnight_arrival"],
    })
    out["delay_band"] = delay_band(dep_delay, cancelled)
    # arrival capacity label: delivered = not cancelled, not diverted, ARR_DELAY <= 15
    out["delivered"] = (~cancelled & ~diverted & arr_delay.le(15)).astype("int8")
    out.loc[~cancelled & ~diverted & arr_delay.isna(), "delivered"] = -1  # unknown
    out["delivered"] = out["delivered"].replace(-1, np.nan).astype("Float64")
    out["split_dep"] = assign_split(out["sched_dep_utc"])
    out["split_arr"] = assign_split(out["sched_arr_utc"])
    out["severe"] = out["delay_band"].isin(["45_60", "gt60"])
    stats["band_missing"] = int(out["delay_band"].isna().sum())
    return out, stats
