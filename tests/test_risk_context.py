"""v1.2 risk_context: the explanation scale agrees with the colour cut-offs (L-027)."""
import pytest

from backend.common import config
from backend.risk_context import risk_context
from backend.rules import risk_level


def test_cutoffs_sit_at_their_percentiles():
    rr = config()["risk_rules"]
    assert risk_context(rr["red"]["p_gt45_min"])["percentile"] == 90
    assert risk_context(rr["amber"]["p_gt45_min"])["percentile"] == 70
    assert risk_context(config()["risk_scale"]["quantiles"][50])["ratio_to_typical"] == 1.0


@pytest.mark.parametrize("p", [0.0, 0.05, 0.09, 0.116, 0.117, 0.15, 0.171, 0.172, 0.25, 0.4, 0.99])
def test_percentile_agrees_with_colour(p):
    c, lvl = risk_context(p), str(risk_level([p])[0])
    assert 0 <= c["percentile"] <= 99
    assert (c["percentile"] >= 90) == (lvl == "RED") or abs(p - c["red_min"]) < 0.002
    assert c["ratio_to_typical"] == round(p / c["typical_p"], 1)


def test_monotonic_in_p():
    ps = [i / 200 for i in range(0, 120)]
    pc = [risk_context(p)["percentile"] for p in ps]
    assert pc == sorted(pc)
