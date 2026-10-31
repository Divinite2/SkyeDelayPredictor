"""A3 Baselines (built first; every model is compared against them).

B0 Climatology: training-period rate for airport x local hour x month of the target hour.
   Cells are sparse (~20 flights each), so each cell is shrunk toward airport x local hour, which
   is shrunk toward the airport rate (prior weight M flights each level; D-015).
B1 Logistic regression: same P0 features, one model per threshold, monotonic fix after prediction.
"""
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from backend.common import config
from backend.features import FEATURES

M = 20
BAND_ORDER = ["le15", "15_30", "30_45", "45_60", "gt60"]
THRESH = config()["delay_thresholds_min"]           # [15, 30, 45, 60]
# P(delay > k) == P(band index >= i) with i = 1..4
K_IDX = {k: i + 1 for i, k in enumerate(THRESH)}


def band_index(band: pd.Series) -> np.ndarray:
    return band.map({b: i for i, b in enumerate(BAND_ORDER)}).to_numpy(dtype=int)


def exceed_targets(band: pd.Series) -> dict:
    bi = band_index(band)
    return {k: (bi >= i).astype(int) for k, i in K_IDX.items()}


def enforce_monotone(P: np.ndarray) -> np.ndarray:
    """P columns = P(>15), P(>30), P(>45), P(>60): make non-increasing left to right."""
    return np.minimum.accumulate(P, axis=1)


# ------------------------------------------------------------------- B0 climatology
class Climatology:
    def __init__(self, m: int = M):
        self.m = m

    def fit(self, rows: pd.DataFrame, targets: dict):
        """rows: ONE row per flight (training period); targets: name -> 0/1 array."""
        d = rows[["airport", "local_hour", "month"]].copy()
        self.tables = {}
        for name, y in targets.items():
            d["y"] = np.asarray(y, dtype=float)
            a = d.groupby("airport")["y"].mean()
            ah = d.groupby(["airport", "local_hour"])["y"].agg(["sum", "count"])
            ah["p"] = (ah["sum"] + self.m * a.reindex(ah.index.get_level_values(0)).to_numpy()) / (ah["count"] + self.m)
            ahm = d.groupby(["airport", "local_hour", "month"])["y"].agg(["sum", "count"])
            prior = ah["p"].reindex(ahm.index.droplevel(2)).to_numpy()
            ahm["p"] = (ahm["sum"] + self.m * prior) / (ahm["count"] + self.m)
            self.tables[name] = (a, ah["p"], ahm["p"])
        return self

    def predict(self, rows: pd.DataFrame, name) -> np.ndarray:
        a, ah, ahm = self.tables[name]
        k3 = pd.MultiIndex.from_arrays([rows["airport"], rows["local_hour"].astype(int), rows["month"].astype(int)])
        k2 = pd.MultiIndex.from_arrays([rows["airport"], rows["local_hour"].astype(int)])
        p = ahm.reindex(k3).to_numpy()
        p = np.where(np.isnan(p), ah.reindex(k2).to_numpy(), p)
        p = np.where(np.isnan(p), rows["airport"].map(a).to_numpy(dtype=float), p)
        return p

    def predict_exceed(self, rows) -> np.ndarray:
        return enforce_monotone(np.column_stack([self.predict(rows, k) for k in THRESH]))


# ------------------------------------------------------------------- B1 logistic
class LogisticBaseline:
    def fit(self, X: pd.DataFrame, band: pd.Series):
        ys = exceed_targets(band)
        self.models = {}
        for k in THRESH:
            pipe = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                 LogisticRegression(max_iter=2000, C=1.0, random_state=42))
            self.models[k] = pipe.fit(X[FEATURES], ys[k])
        return self

    def predict_exceed(self, X) -> np.ndarray:
        P = np.column_stack([self.models[k].predict_proba(X[FEATURES])[:, 1] for k in THRESH])
        return enforce_monotone(P)
