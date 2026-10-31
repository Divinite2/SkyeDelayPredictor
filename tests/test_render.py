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


def test_simulated_tag_always_present():
    v = R.view_model(RED)
    assert len(v["flights"]) == 5
    assert all(f["tag"] == "SIMULATED" for f in v["flights"])


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
