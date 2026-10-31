"""B2.5 / Gate 2(c): P(>15) >= P(>30) >= P(>45) >= P(>60) on every row of every split."""
import lightgbm as lgb
import numpy as np
import pandas as pd

from backend.common import path
from backend.features import FEATURES
from backend.train import bands_to_exceed


def test_delay_model_monotonic_every_row():
    m = lgb.Booster(model_file=str(path("models_dir") / "delayband.txt"))
    for p in sorted(path("processed_dir").glob("features_*.parquet")):
        X = pd.read_parquet(p)[FEATURES]
        P = m.predict(X)
        assert np.allclose(P.sum(axis=1), 1)
        E = bands_to_exceed(P)
        assert np.all(np.diff(E, axis=1) <= 1e-12), p.name
        assert np.all((E >= 0) & (E <= 1))
