"""Front-end contract test: every example file validates against contract/schema.json,
and the mock returns valid responses for every situation it covers."""
import json
from pathlib import Path

import pytest

from frontend import mock_backend
from frontend.render import is_monotonic, validate_response

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = sorted((ROOT / "contract" / "examples").glob("*.json"))
REQUIRED = {"ok_red", "ok_green", "refused_short", "refused_long", "refused_airport", "error"}


def test_all_six_examples_present():
    assert {p.stem.removeprefix("example_") for p in EXAMPLES} >= REQUIRED


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_validates(path):
    resp = json.loads(path.read_text())
    assert validate_response(resp) is None
    if resp["status"] == "ok":
        assert is_monotonic(resp["hour_delay_risk"])
        assert len(resp["flights"]) == 5
        for f in resp["flights"]:
            assert f["source"] == "SIMULATED"
            for k in ("p_gt15", "p_gt30", "p_gt45", "p_gt60"):
                assert f[k] == resp["hour_delay_risk"][k]
        for d in resp["drivers"]:
            if d["observed_at_utc"]:
                assert d["observed_at_utc"] <= resp["request"]["now_utc"]


NOW = "2025-06-14T16:00:00Z"


@pytest.mark.parametrize("airport,target,expect", [
    ("ATL", "2025-06-14T22:00:00Z", "ok"),
    ("DFW", "2025-06-14T21:00:00Z", "ok"),
    ("KATL", "2025-06-14T19:00:00Z", "ok"),
    ("ATL", "2025-06-14T18:00:00Z", "LEAD_TOO_SHORT"),
    ("ATL", "2025-06-15T05:00:00Z", "LEAD_TOO_LONG"),
    ("ORD", "2025-06-14T22:00:00Z", "UNKNOWN_AIRPORT"),
    ("ERR", "2025-06-14T22:00:00Z", "error"),
])
def test_mock_responses_valid(airport, target, expect):
    resp = mock_backend.predict(airport, target, NOW)
    assert validate_response(resp) is None
    got = resp["refusal"]["code"] if resp["status"] == "refused" else resp["status"]
    assert got == expect
    if resp["status"] == "ok":
        assert resp["request"]["target_hour_utc"] == target
        assert all(f["flight_id"].startswith(f"SIM-{resp['request']['airport']}-2025061") for f in resp["flights"])


def test_mock_is_deterministic():
    a = mock_backend.predict("ATL", "2025-06-14T22:00:00Z", NOW)
    b = mock_backend.predict("ATL", "2025-06-14T22:00:00Z", NOW)
    assert a == b
