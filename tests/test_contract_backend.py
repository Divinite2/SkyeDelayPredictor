"""Checkpoint 0 pass condition: every contract example validates against contract/schema.json,
plus the cross-field rules JSON Schema cannot express (04_Data_Contract.md §3, §5, §8)."""
import json
from datetime import datetime
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "contract/schema.json").read_text())
CFG = yaml.safe_load((ROOT / "config/config.yaml").read_text())
EXAMPLES = sorted((ROOT / "contract/examples").glob("*.json"))
REQUIRED = {"example_ok_red", "example_ok_green", "example_refused_short",
            "example_refused_long", "example_refused_airport", "example_error"}
PKEYS = ["p_gt15", "p_gt30", "p_gt45", "p_gt60"]


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def test_schema_is_valid():
    Draft202012Validator.check_schema(SCHEMA)


def test_all_required_examples_present():
    assert REQUIRED <= {p.stem for p in EXAMPLES}


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_example(path):
    body = json.loads(path.read_text())
    errors = list(Draft202012Validator(SCHEMA).iter_errors(body))
    assert not errors, [e.message for e in errors]
    assert body["schema_version"] == CFG["schema_version"]
    if body["status"] != "ok":
        return
    req, risk = body["request"], body["hour_delay_risk"]
    # monotonicity
    vals = [risk[k] for k in PKEYS]
    assert vals == sorted(vals, reverse=True)
    assert all(round(v, 3) == v for v in vals)  # 3-decimal rounding rule
    # lead time consistent with timestamps and within config window
    lead = (ts(req["target_hour_utc"]) - ts(req["now_utc"])).total_seconds() / 3600
    assert lead == req["lead_time_h"]
    assert CFG["lead_time_hours"]["min"] <= lead <= CFG["lead_time_hours"]["max"]
    # leakage guarantee visible to user
    for d in body["drivers"]:
        if d["observed_at_utc"] is not None:
            assert ts(d["observed_at_utc"]) <= ts(req["now_utc"])
    assert ts(body["weather_basis"]["last_obs_utc"]) <= ts(req["now_utc"])
    # v1.1: no flight list; likely-delay range consistent with the hour risk
    assert "flights" not in body
    from backend.delay_estimate import delay_estimate
    assert body["delay_estimate"] == delay_estimate(risk)


def test_broken_examples_are_rejected():
    """Sanity: the schema actually catches violations (bad delay_estimate text, bad prob)."""
    body = json.loads((ROOT / "contract/examples/example_ok_red.json").read_text())
    body["delay_estimate"]["typical_text"] = "23 minutes"
    body["hour_delay_risk"]["p_gt15"] = 1.5
    assert list(Draft202012Validator(SCHEMA).iter_errors(body))
