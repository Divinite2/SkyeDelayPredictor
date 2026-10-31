"""A1.1 Load the raw CSV with explicit dtypes, keeping only what the pipeline needs.

Kept: allowed (known-in-advance) schedule columns, label columns, and the raw weather columns.
The raw weather columns are BANNED as features (02 §A2); they are loaded only to build the
hourly weather timeline in weather_timeline.py and never reach the feature table.
"""
import pandas as pd

from backend.common import raw_csv

ALLOWED = {  # known before the flight
    "FL_DATE": "string", "OP_UNIQUE_CARRIER": "string", "OP_CARRIER_FL_NUM": "Int64",
    "ORIGIN": "string", "ORIGIN_STATE_ABR": "string", "DEST": "string", "DEST_STATE_ABR": "string",
    "CRS_DEP_TIME": "Int64", "CRS_ARR_TIME": "Int64", "CRS_ELAPSED_TIME": "Float64",
    "DISTANCE": "Float64",
}
LABELS = {  # known only after the event; used for labels and checks, never as features
    "DEP_DELAY": "Float64", "ARR_DELAY": "Float64", "CANCELLED": "Float64", "DIVERTED": "Float64",
}
WEATHER_VARS = ["temp", "prcp", "wspd", "wpgt", "pres", "snow", "coco"]
RAW_WEATHER = {f"{v}_{side}": "Float64" for side in ("ORIGIN", "DEST") for v in WEATHER_VARS}
DTYPES = {**ALLOWED, **LABELS, **RAW_WEATHER}

# 02 §A2 banned list (prefix match with '*' semantics handled in is_banned)
BANNED_EXACT = {
    "DEP_TIME", "DEP_DEL15", "DEP_DELAY_GROUP", "TAXI_OUT", "WHEELS_OFF", "WHEELS_ON", "TAXI_IN",
    "ARR_TIME", "ARR_DEL15", "ARR_DELAY_GROUP", "CANCELLED", "CANCELLATION_CODE", "DIVERTED",
    "ACTUAL_ELAPSED_TIME", "AIR_TIME", "CARRIER_DELAY", "WEATHER_DELAY", "NAS_DELAY",
    "SECURITY_DELAY", "LATE_AIRCRAFT_DELAY", "FIRST_DEP_TIME", "TOTAL_ADD_GTIME", "LONGEST_ADD_GTIME",
    # cleaned label columns produced by clean_flights.py
    "dep_delay_min", "arr_delay_min", "cancelled", "diverted", "delay_band", "delivered",
    "cancelled_with_delay",
}
BANNED_PREFIX = ("DEP_DELAY", "ARR_DELAY", "DIV")
BANNED_SUFFIX = ("_ORIGIN", "_DEST")


def is_banned(col: str) -> bool:
    return (col in BANNED_EXACT or col.startswith(BANNED_PREFIX)
            or (col.endswith(BANNED_SUFFIX) and col.split("_")[0] in WEATHER_VARS))


def load_raw() -> pd.DataFrame:
    return pd.read_csv(raw_csv(), usecols=list(DTYPES), dtype=DTYPES)


def raw_header() -> list[str]:
    return list(pd.read_csv(raw_csv(), nrows=0).columns)
