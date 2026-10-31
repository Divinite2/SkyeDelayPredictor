"""B2.2 Runway wind components (trap T2). ATL runway heading 80°, DFW 180° (config)."""
import numpy as np
import pytest

from backend.common import config
from backend.features import wind_components

RWY = {ap: v["runway_heading_deg"] for ap, v in config()["airports"].items()}


@pytest.mark.parametrize("ap", ["ATL", "DFW"])
def test_wind_straight_down_runway_is_pure_headwind(ap):
    h, c, t = wind_components(30, RWY[ap], RWY[ap])
    assert np.isclose(h, 30) and np.isclose(c, 0, atol=1e-9) and np.isclose(t, 0)


@pytest.mark.parametrize("ap", ["ATL", "DFW"])
@pytest.mark.parametrize("offset", [90, -90])
def test_wind_at_90_degrees_is_full_crosswind(ap, offset):
    h, c, t = wind_components(30, (RWY[ap] + offset) % 360, RWY[ap])
    assert np.isclose(c, 30) and np.isclose(h, 0, atol=1e-9) and np.isclose(t, 0, atol=1e-9)


@pytest.mark.parametrize("ap", ["ATL", "DFW"])
def test_tailwind_detected(ap):
    h, c, t = wind_components(20, (RWY[ap] + 180) % 360, RWY[ap])
    assert np.isclose(t, 20) and np.isclose(h, 0) and np.isclose(c, 0, atol=1e-9)


def test_45_degree_split_and_vectorised():
    h, c, t = wind_components(np.array([20.0, 20.0]), np.array([125.0, 35.0]), 80)
    assert np.allclose(h, 20 / np.sqrt(2)) and np.allclose(c, 20 / np.sqrt(2)) and np.allclose(t, 0)


def test_worst_case_bounds_any_direction():
    """The model's crosswind_worst_kmh = wspd is an upper bound for every direction."""
    d = np.arange(0, 360, 5)
    for ap in RWY:
        _, c, _ = wind_components(np.full(d.shape, 25.0), d, RWY[ap])
        assert c.max() <= 25 + 1e-9
