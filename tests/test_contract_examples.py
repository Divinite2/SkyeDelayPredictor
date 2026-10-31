"""Checkpoint 0 contract test: every example response must follow docs/04_Data_Contract.md.
Run: pytest -q tests/test_contract_examples.py"""
import json, pathlib, pytest, jsonschema

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "contract/schema.json").read_text())
EXAMPLES = sorted((ROOT / "contract/examples").glob("*.json"))
KEYS = ["p_gt15", "p_gt30", "p_gt45", "p_gt60"]

def test_six_examples_exist():
    assert len(EXAMPLES) == 6

@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_example_valid(path):
    r = json.loads(path.read_text())
    jsonschema.validate(r, SCHEMA)
    if r["status"] != "ok":
        return
    risk = [r["hour_delay_risk"][k] for k in KEYS]
    assert risk == sorted(risk, reverse=True), "risks must be monotonic"
    for d in r["drivers"]:
        if d["observed_at_utc"] is not None:
            assert d["observed_at_utc"] <= r["request"]["now_utc"], "driver observed after forecast time (leakage)"
    assert 3 <= r["request"]["lead_time_h"] <= 12
    for f in r["flights"]:
        assert f["source"] == "SIMULATED"
        assert [f[k] for k in KEYS] == [r["hour_delay_risk"][k] for k in KEYS], "simulated flights must equal hour risk"

def test_broken_monotonic_is_detectable():
    r = json.loads((ROOT / "contract/examples/example_ok_red.json").read_text())
    r["hour_delay_risk"]["p_gt45"] = 0.9
    risk = [r["hour_delay_risk"][k] for k in KEYS]
    assert risk != sorted(risk, reverse=True)
