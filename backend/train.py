"""A3 Models: LightGBM 5-band delay model + LightGBM capacity (delivered-on-time) model.

Delay: multiclass over ordered bands; P(delay > k) = sum of bands above k -> monotone by
construction (asserted). Small random search (<= 20 configs) scored on VALIDATION multi-logloss,
early stopping on validation. No oversampling (honest probabilities).
"""
import itertools
import json
import random

import lightgbm as lgb
import numpy as np
import pandas as pd

from backend.baselines import BAND_ORDER, band_index
from backend.features import FEATURES

BASE = dict(num_leaves=31, learning_rate=0.05, min_data_in_leaf=100, feature_fraction=0.8,
            bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0, seed=42, verbose=-1,
            deterministic=True, force_row_wise=True, num_threads=4)
GRID = dict(num_leaves=[15, 31, 63], min_data_in_leaf=[50, 100, 200, 400],
            learning_rate=[0.03, 0.05], feature_fraction=[0.6, 0.8], lambda_l2=[1.0, 5.0])
N_CONFIGS = 20


def bands_to_exceed(P: np.ndarray) -> np.ndarray:
    """(n,5) band probabilities -> (n,4) P(>15), P(>30), P(>45), P(>60)."""
    E = np.column_stack([P[:, i:].sum(axis=1) for i in range(1, 5)])
    assert np.all(np.diff(E, axis=1) <= 1e-12), "monotonicity violated"
    return E


def _configs():
    rnd = random.Random(42)
    allc = [dict(zip(GRID, v)) for v in itertools.product(*GRID.values())]
    first = {k: BASE[k] for k in GRID}
    picks = [first] + [c for c in rnd.sample(allc, N_CONFIGS + 5) if c != first]
    return picks[:N_CONFIGS]


def train_delay_model(tr: pd.DataFrame, va: pd.DataFrame):
    ytr, yva = band_index(tr["label"]), band_index(va["label"])
    search = []
    best = None
    for cfg in _configs():
        params = {**BASE, **cfg, "objective": "multiclass", "num_class": len(BAND_ORDER),
                  "metric": "multi_logloss"}
        dtr = lgb.Dataset(tr[FEATURES], ytr, params={"feature_pre_filter": False})
        dva = lgb.Dataset(va[FEATURES], yva, reference=dtr)
        m = lgb.train(params, dtr, num_boost_round=3000, valid_sets=[dva],
                      callbacks=[lgb.early_stopping(100, verbose=False)])
        score = m.best_score["valid_0"]["multi_logloss"]
        search.append({**cfg, "best_iter": m.best_iteration, "val_multi_logloss": round(score, 5)})
        if best is None or score < best[0]:
            best = (score, m, params)
    return best[1], best[2], pd.DataFrame(search).sort_values("val_multi_logloss")


def train_capacity_model(tr: pd.DataFrame, va: pd.DataFrame):
    params = {**BASE, "objective": "binary", "metric": "binary_logloss"}
    dtr = lgb.Dataset(tr[FEATURES], tr["label"])
    dva = lgb.Dataset(va[FEATURES], va["label"], reference=dtr)
    m = lgb.train(params, dtr, num_boost_round=3000, valid_sets=[dva],
                  callbacks=[lgb.early_stopping(100, verbose=False)])
    return m, params


def predict_delay(model, X) -> np.ndarray:
    return bands_to_exceed(model.predict(X[FEATURES], num_iteration=model.best_iteration))


def predict_capacity(model, X) -> np.ndarray:
    return model.predict(X[FEATURES], num_iteration=model.best_iteration)
