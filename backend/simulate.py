"""SIMULATED example flights (02 A4 step 9, D10). Never real, never per-flight predictions.

Carrier, destination and scheduled minute are sampled together from TRAINING-period departures
at the same airport and local hour (the real file is used only to learn the pattern; falls back
to all training hours at that airport). Seed = crc32(airport + target hour): the list is
identical every time. Every row carries source=SIMULATED and the HOUR's risk.
"""
import zlib

import numpy as np
import pandas as pd

from backend.common import config


class FlightPattern:
    def __init__(self, flights: pd.DataFrame):
        tr = flights[(flights["split_dep"] == "train") & flights["airport_dep"].isin(config()["airports"])]
        rows = []
        for ap, part in tr.groupby("airport_dep"):
            loc = part["sched_dep_utc"].dt.tz_convert(config()["airports"][ap]["tz"])
            rows.append(pd.DataFrame({"airport": ap, "local_hour": loc.dt.hour.to_numpy(),
                                      "carrier": part["carrier"].astype(str).to_numpy(),
                                      "dest": part["airport_arr"].astype(str).to_numpy(),
                                      "minute": loc.dt.minute.to_numpy()}))
        self.pool = pd.concat(rows, ignore_index=True)

    def flights(self, airport: str, target_utc: pd.Timestamp, local_hour: int, risk: dict) -> list:
        n = config()["flight_list"]["rows_shown"]
        pool = self.pool[(self.pool["airport"] == airport) & (self.pool["local_hour"] == local_hour)]
        if len(pool) < n:
            pool = self.pool[self.pool["airport"] == airport]
        key = f"{airport}{target_utc:%Y%m%d%H}"
        rng = np.random.default_rng(zlib.crc32(key.encode()))
        pick = pool.iloc[rng.choice(len(pool), size=n, replace=len(pool) < n)]
        pick = pick.sort_values(["minute", "carrier", "dest"]).reset_index(drop=True)
        out = []
        for i, r in pick.iterrows():
            dep = target_utc + pd.Timedelta(minutes=int(r["minute"]))
            out.append({"flight_id": f"SIM-{airport}-{target_utc:%Y%m%d%H}-{i + 1:02d}",
                        "carrier": r["carrier"], "origin": airport, "dest": r["dest"],
                        "sched_dep_utc": dep.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "source": "SIMULATED", **risk})
        return out
