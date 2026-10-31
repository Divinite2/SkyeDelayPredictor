"""B2.3 Automated leakage test (02 §A2, trap T1/T16). Fails loudly.

1. For 500 random training/validation/test rows: delete every weather row with obs_time_utc > t
   and recompute -> features identical. Also the reverse: inject an extreme fake storm AFTER t
   -> features still identical.
2. No banned column in the feature list or in the trained models.
3. drivers[].observed_at_utc <= now_utc in API responses (enabled once backend/api.py exists, B-3).
4. Smell test: no ROC-AUC > 0.95.
"""
import copy
import json

import lightgbm as lgb
import numpy as np
import pandas as pd
import pytest

from backend.common import ROOT, path
from backend.features import FEATURES, Context
from backend.load import is_banned

PROC = path("processed_dir")
N_SAMPLE = 500


@pytest.fixture(scope="module")
def setup():
    fl = pd.read_parquet(PROC / "flights_clean.parquet")
    wx = pd.read_parquet(PROC / "weather_hourly.parquet")
    ctx = Context(fl, wx)
    rows = pd.concat([pd.read_parquet(p) for p in sorted(PROC.glob("features_*.parquet"))],
                     ignore_index=True)
    return ctx, rows.sample(N_SAMPLE, random_state=42).reset_index(drop=True)


def _recompute(ctx, row, wx_override):
    c = copy.copy(ctx)
    c.wx = dict(ctx.wx)
    c.wx[row["airport"]] = wx_override
    X = c.hour_features(pd.Series([row["airport"]]), pd.Series([row["target_hour_utc"]]),
                        pd.Series([int(row["lead"])]))
    return X[FEATURES].iloc[0].to_numpy(dtype=float)


def _assert_same(a, b, row, what):
    ok = np.allclose(a, b, rtol=1e-9, atol=1e-9, equal_nan=True)
    if not ok:
        bad = [f for f, x, y in zip(FEATURES, a, b) if not np.isclose(x, y, equal_nan=True)]
        pytest.fail(f"LEAKAGE ({what}) for {row['airport']} T={row['target_hour_utc']} "
                    f"lead={row['lead']}: features changed: {bad}")


def test_deleting_future_weather_changes_nothing(setup):
    ctx, sample = setup
    for _, row in sample.iterrows():
        t = pd.Timestamp(row["issue_time_utc"])
        wx = ctx.wx[row["airport"]]
        truncated = wx[wx["obs_time_utc"] <= t]
        _assert_same(row[FEATURES].to_numpy(dtype=float), _recompute(ctx, row, truncated), row,
                     "future weather deleted")


def test_injecting_future_storm_changes_nothing(setup):
    ctx, sample = setup
    for _, row in sample.head(100).iterrows():
        t = pd.Timestamp(row["issue_time_utc"])
        wx = ctx.wx[row["airport"]]
        fake = pd.DataFrame({"airport": row["airport"],
                             "obs_time_utc": [t + pd.Timedelta(hours=h) for h in range(1, 13)],
                             "temp_c": 35.0, "prcp_mm": 50.0, "wspd_kmh": 120.0, "pres_hpa": 950.0,
                             "coco": 27, "coco_label": "Storm", "coco_group": "convective",
                             "n_source_rows": 1, "conflict_flag": False})
        poisoned = pd.concat([wx[wx["obs_time_utc"] <= t], fake], ignore_index=True)
        poisoned["coco"] = poisoned["coco"].astype("Int64")
        _assert_same(row[FEATURES].to_numpy(dtype=float), _recompute(ctx, row, poisoned), row,
                     "future storm injected")


def test_no_banned_columns():
    assert not [c for c in FEATURES if is_banned(c)]
    for name in ["delayband", "capacity"]:
        names = lgb.Booster(model_file=str(path("models_dir") / f"{name}.txt")).feature_name()
        assert names == FEATURES, f"{name} model features differ from FEATURES"
        assert not [c for c in names if is_banned(c)]


def test_driver_times_not_after_now():
    api = ROOT / "backend/api.py"
    if not api.exists():
        pytest.skip("backend/api.py is built in checkpoint B-3; this check activates then")
    from backend.api import predict
    from tests.test_contract import REQUESTS  # noqa: F401  (defined in B-3)
    for req in REQUESTS:
        r = predict(**req)
        if r["status"] == "ok":
            for d in r["drivers"]:
                if d["observed_at_utc"] is not None:
                    assert d["observed_at_utc"] <= r["request"]["now_utc"]


def test_smell_no_auc_above_095():
    card = json.loads((path("models_dir") / "model_card.json").read_text())
    assert card["gate2"]["max_roc_auc"] <= 0.95, "ROC-AUC > 0.95: investigate as possible leakage"
