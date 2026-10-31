"""Pure display-function tests (03_Instructions_Frontend.md, Front-end tests)."""
import copy
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from frontend import render as R

ROOT = Path(__file__).resolve().parent.parent
RED = json.loads((ROOT / "contract/examples/example_ok_red.json").read_text())
BROKEN = json.loads((ROOT / "tests/fixtures/broken_monotonic.json").read_text())


def utc(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def test_pct_rounding():
    assert R.pct(0.384) == "38%"
    assert R.pct(0.385) == "39%"      # half-up
    assert R.pct(0.0) == "0%"
    assert R.pct(None) == "—"         # never 0 for missing


def test_null_capacity_hidden():
    assert R.capacity_line({"index": None, "index_low": None, "index_high": None,
                            "aar_est": None, "aar_low": None, "aar_high": None, "aar_note": None}) is None
    assert R.capacity_line(None) is None


def test_capacity_text_and_no_aar_when_null():
    c = R.capacity_line(RED["capacity"])
    assert c["text"] == "70% of scheduled arrivals on time (likely 60–80%)"
    assert c["aar"] is None


def test_capacity_note_visible_when_range_null():
    """F3b.3 / F3.7: no range + aar_note -> note shown as visible text, taken from the response."""
    resp = copy.deepcopy(RED)
    resp["capacity"].update(index_low=None, index_high=None, aar_note="Range not shown: test note.")
    c = R.view_model(resp)["capacity"]
    assert c["text"] == "70% of scheduled arrivals on time"          # no range in the line
    assert c["visible_note"] == "Range not shown: test note."         # verbatim from response
    with_range = R.capacity_line(RED["capacity"])                     # range present -> no grey note
    assert with_range["visible_note"] is None


def test_monotonic_violation_gives_error_card():
    assert R.view_model(BROKEN)["kind"] == "error"


def test_schema_violation_gives_error_card():
    bad = copy.deepcopy(RED)
    del bad["risk_level"]
    assert R.view_model(bad)["kind"] == "error"


def test_ok_card_marks_severe_45():
    rows = R.view_model(RED)["risk_rows"]
    assert [r["label"] for r in rows] == ["> 15 min", "> 30 min", "> 45 min", "> 60 min"]
    assert [r["severe"] for r in rows] == [False, False, True, False]


def test_level_style_follows_backend_level_only():
    """UI v1.2: colour/headline come from the back end's risk_level; no thresholds in the front end."""
    for lvl in ("RED", "AMBER", "GREEN"):
        v = R.view_model({**RED, "risk_level": lvl})
        assert v["level_style"] is R.LEVEL_STYLE[lvl]
    icons = {s["icon"] for s in R.LEVEL_STYLE.values()}
    assert len(icons) == 3                       # shape differs, not colour alone
    v = R.view_model(RED)
    assert v["confidence_style"] is R.CONFIDENCE_STYLE["MEDIUM"]
    assert v["severe_label"] == "> 45 min" and v["severe_text"] == "38%"
    assert v["airport"] == "ATL (KATL)"


def test_driver_arrows():
    lines = R.driver_lines("ATL", RED["drivers"], RED["request"]["target_hour_utc"])
    assert [d["arrow"] for d in lines] == ["▲", "▲", "▲"]
    down = R.driver_lines("ATL", [{**RED["drivers"][0], "effect": "decreases"}])
    assert down[0]["arrow"] == "▼"


def test_delay_estimate_shown_verbatim():
    v = R.view_model(RED)
    e = v["delay_estimate"]
    assert e["typical"] == RED["delay_estimate"]["typical_text"]
    assert e["bad"] == RED["delay_estimate"]["bad_case_text"]
    assert e["bad_label"] == "Bad case (1-in-4 chance)"
    assert "flights" not in v


def test_driver_time_shows_date_when_not_target_day():
    drivers = [{"label": "Thunderstorm earlier", "value": "22 h before the forecast",
                "observed_at_utc": "2025-05-18T21:00:00Z", "effect": "increases"},
               {"label": "Latest reported weather", "value": "Rain",
                "observed_at_utc": "2025-05-19T18:00:00Z", "effect": "increases"}]
    lines = R.driver_lines("DFW", drivers, "2025-05-20T01:00:00Z")   # target = Mon 19 May 20:00 CDT
    assert lines[0]["time"].startswith("Sun 18 May")                  # previous local day -> dated
    assert lines[1]["time"] == "13:00 CDT"                            # same local day -> time only


def test_refused_and_error_cards_have_no_numbers():
    for name in ("refused_short", "refused_long", "refused_airport", "error"):
        v = R.view_model(json.loads((ROOT / f"contract/examples/example_{name}.json").read_text()))
        assert "risk_rows" not in v and "capacity" not in v


def test_period_banner():
    assert R.period_banner(RED) is None
    assert "TRAIN" in R.period_banner({**RED, "data_period": "TRAIN"})


# ---- Daylight-saving dates (2024-03-10 spring forward, 2024-11-03 fall back) ----
@pytest.mark.parametrize("apt,day,hour,expect_utc", [
    ("ATL", date(2024, 3, 10), 1, "2024-03-10T06:00"),   # EST (UTC-5)
    ("ATL", date(2024, 3, 10), 3, "2024-03-10T07:00"),   # EDT (UTC-4)
    ("DFW", date(2024, 3, 10), 1, "2024-03-10T07:00"),   # CST (UTC-6)
    ("DFW", date(2024, 3, 10), 3, "2024-03-10T08:00"),   # CDT (UTC-5)
    ("ATL", date(2024, 11, 3), 0, "2024-11-03T04:00"),   # EDT
    ("ATL", date(2024, 11, 3), 3, "2024-11-03T08:00"),   # EST
    ("DFW", date(2024, 11, 3), 0, "2024-11-03T05:00"),   # CDT
    ("DFW", date(2024, 11, 3), 3, "2024-11-03T09:00"),   # CST
])
def test_local_to_utc_dst(apt, day, hour, expect_utc):
    assert R.local_to_utc(apt, day, hour) == utc(expect_utc)


@pytest.mark.parametrize("apt,ts,expect", [
    ("ATL", "2024-11-03T05:00", "01:00 EDT"),   # repeated 01:00, first pass
    ("ATL", "2024-11-03T06:00", "01:00 EST"),   # repeated 01:00, second pass
    ("DFW", "2024-03-10T08:00", "03:00 CDT"),   # 02:00 skipped
    ("DFW", "2024-03-10T07:00", "01:00 CST"),
])
def test_utc_to_local_dst(apt, ts, expect):
    assert R.fmt_local(apt, utc(ts)) == expect


def test_target_options_never_skip_an_hour_on_dst():
    now = R.local_to_utc("ATL", date(2024, 3, 10), 0)
    opts = R.target_options(now)
    assert [h for h, _ in opts] == list(range(3, 13))
    assert all((t - now).total_seconds() == h * 3600 for h, t in opts)


def test_risk_scale_positions_and_text_from_backend():
    """v1.2: marker scale uses only risk_context numbers; text explains, never re-decides."""
    sc = R.view_model(RED)["risk_scale"]
    ctx = RED["risk_context"]
    assert sc["amber"] == round(ctx["amber_min"] / ctx["scale_max"] * 100, 1)
    assert sc["red"] == round(ctx["red_min"] / ctx["scale_max"] * 100, 1)
    assert sc["marker"] == 100.0 and sc["beyond"]            # 38% is past the 30% scale end
    assert sc["justification"] == f"Riskier than {ctx['percentile']}% of hours · " \
                                  f"{ctx['ratio_to_typical']:.1f}× a typical hour (9%)"
    assert "RED starts at 17%" in sc["why_colour"]
    assert R.risk_scale_view(None, 0.2, "RED") is None
