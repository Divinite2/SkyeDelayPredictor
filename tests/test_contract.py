"""B3.6 / B3.7 Contract test on REAL predict() output (04 §8, 08 B3.6, 12 B3.3-B3.7).

20 fixed requests: normal, storm, no-sampled-flights, ICAO input, every refusal code, and errors.
Each response must validate against contract/schema.json and satisfy the cross-field rules.
"""
import json
import time
from datetime import datetime

import pytest
from jsonschema import Draft202012Validator

from backend.api import AAR_NOTE, predict
from backend.common import ROOT, config

SCHEMA = json.loads((ROOT / "contract/schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)
PKEYS = ["p_gt15", "p_gt30", "p_gt45", "p_gt60"]

# (id, airport, target_hour_utc, now_utc, expected status, expected refusal code or None)
CASES = [
    ("normal_atl_val", "ATL", "2025-02-13T22:00:00Z", "2025-02-13T16:00:00Z", "ok", None),
    ("normal_dfw_val_rain", "DFW", "2025-03-28T23:00:00Z", "2025-03-28T17:00:00Z", "ok", None),
    ("storm_dfw_val", "DFW", "2025-01-30T17:00:00Z", "2025-01-30T11:00:00Z", "ok", None),
    ("storm_dfw_test", "DFW", "2025-04-23T21:00:00Z", "2025-04-23T18:00:00Z", "ok", None),
    ("storm_atl_test", "ATL", "2025-04-24T01:00:00Z", "2025-04-23T22:00:00Z", "ok", None),
    ("lead_12_low_conf", "ATL", "2025-06-14T22:00:00Z", "2025-06-14T10:00:00Z", "ok", None),
    ("no_sampled_flights", "ATL", "2025-02-10T08:00:00Z", "2025-02-10T02:00:00Z", "ok", None),
    ("icao_input", "KDFW", "2025-05-06T17:00:00Z", "2025-05-06T11:00:00Z", "ok", None),
    ("lowercase_input", "atl", "2024-06-14T22:00:00Z", "2024-06-14T16:00:00Z", "ok", None),
    ("lead_2", "ATL", "2025-06-14T18:00:00Z", "2025-06-14T16:00:00Z", "refused", "LEAD_TOO_SHORT"),
    ("target_in_past", "ATL", "2025-06-14T10:00:00Z", "2025-06-14T16:00:00Z", "refused", "LEAD_TOO_SHORT"),
    ("lead_13", "ATL", "2025-06-15T05:00:00Z", "2025-06-14T16:00:00Z", "refused", "LEAD_TOO_LONG"),
    ("not_on_hour_target", "ATL", "2025-06-14T22:30:00Z", "2025-06-14T16:00:00Z", "refused", "NOT_ON_THE_HOUR"),
    ("not_on_hour_now", "ATL", "2025-06-14T22:00:00Z", "2025-06-14T16:15:00Z", "refused", "NOT_ON_THE_HOUR"),
    ("unknown_airport", "XYZ", "2025-06-14T22:00:00Z", "2025-06-14T16:00:00Z", "refused", "UNKNOWN_AIRPORT"),
    ("non_hub_airport", "LAX", "2025-06-14T22:00:00Z", "2025-06-14T16:00:00Z", "refused", "UNKNOWN_AIRPORT"),
    ("out_of_range", "ATL", "2026-01-01T06:00:00Z", "2026-01-01T00:00:00Z", "refused", "OUT_OF_DATA_RANGE"),
    ("no_recent_weather", "ATL", "2023-01-01T06:00:00Z", "2023-01-01T00:00:00Z", "refused", "NO_RECENT_WEATHER"),
    ("bad_time_format", "ATL", "2025-06-14 22:00", "2025-06-14T16:00:00Z", "error", None),
    ("not_a_string", None, "2025-06-14T22:00:00Z", "2025-06-14T16:00:00Z", "refused", "UNKNOWN_AIRPORT"),
]
REQUESTS = [{"airport": a, "target_hour_utc": t, "now_utc": n} for _, a, t, n, _, _ in CASES]


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture(scope="module")
def responses():
    predict(*[REQUESTS[0][k] for k in ("airport", "target_hour_utc", "now_utc")])  # warm-up load
    out = {}
    for c, req in zip(CASES, REQUESTS):
        t0 = time.perf_counter()
        r = predict(**req)
        out[c[0]] = (r, time.perf_counter() - t0)
    return out


def test_twenty_requests():
    assert len(CASES) == 20


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_response(case, responses):
    cid, _, _, _, status, code = case
    r, dt = responses[cid]
    errs = [e.message for e in VALIDATOR.iter_errors(r)]
    assert not errs, errs
    assert r["status"] == status, r
    assert dt < 1.0, f"{cid} took {dt:.2f}s (limit 1 s after first load)"
    if status == "refused":
        assert r["refusal"]["code"] == code
        assert "hour_delay_risk" not in r
        return
    if status == "error":
        assert r["error"]["code"] and "hour_delay_risk" not in r
        return
    req, risk = r["request"], r["hour_delay_risk"]
    assert req["airport"] in config()["airports"]  # IATA in responses
    vals = [risk[k] for k in PKEYS]
    assert vals == sorted(vals, reverse=True) and all(round(v, 3) == v for v in vals)
    # risk colour + DO line from rules (L-011), triggered_by always a string
    rr = config()["risk_rules"]
    exp = ("RED" if risk["p_gt45"] >= rr["red"]["p_gt45_min"] else
           "AMBER" if risk["p_gt45"] >= rr["amber"]["p_gt45_min"] else "GREEN")
    assert r["risk_level"] == exp and r["recommendation"]["rule_id"] == f"{exp}-1"
    assert isinstance(r["recommendation"]["triggered_by"], str) and r["recommendation"]["triggered_by"]
    # capacity per L-008
    cap = r["capacity"]
    assert cap["index_low"] is None and cap["index_high"] is None and cap["aar_note"] == AAR_NOTE
    # drivers: <= 3, observed <= now, no repeated wording (note F-c)
    assert len(r["drivers"]) <= 3
    labels = [d["label"] for d in r["drivers"]]
    assert len(set(labels)) == len(labels)
    for d in r["drivers"]:
        if d["observed_at_utc"] is not None:
            assert ts(d["observed_at_utc"]) <= ts(req["now_utc"])
        if d["value"]:
            assert d["label"].lower() not in d["value"].lower()
    assert ts(r["weather_basis"]["last_obs_utc"]) <= ts(req["now_utc"])
    assert r["weather_basis"]["obs_age_h"] <= 12
    # confidence (config + L-010)
    assert r["confidence"]["reasons"]
    if cid == "no_sampled_flights":
        assert r["confidence"]["level"] == "LOW"
        assert "No scheduled flights in the sample for this hour" in r["confidence"]["reasons"]
    if req["lead_time_h"] >= config()["confidence_rules"]["low"]["min_lead_h"]:
        assert r["confidence"]["level"] == "LOW"
    # likely-delay range (v1.1): recomputed from the hour risk with the documented rule
    from backend.delay_estimate import delay_estimate as _de
    assert r["delay_estimate"] == _de(risk)
    assert "flights" not in r
    # risk context (v1.2): explains the colour on the same validation scale, never contradicts it
    from backend.risk_context import risk_context as _rc
    ctx = r["risk_context"]
    assert ctx == _rc(risk["p_gt45"])
    assert ctx["amber_min"] < ctx["red_min"]
    if r["risk_level"] == "RED":
        assert ctx["percentile"] >= 89 and ctx["ratio_to_typical"] > 1
    elif r["risk_level"] == "AMBER":
        assert 69 <= ctx["percentile"] <= 91
    else:
        assert ctx["percentile"] <= 71
    # data period
    exp_period = ("TRAIN" if req["target_hour_utc"] < "2025-01-01" else
                  "VALIDATION" if req["target_hour_utc"] < "2025-04-01" else "TEST")
    assert r["data_period"] == exp_period


@pytest.mark.parametrize("req", REQUESTS, ids=[c[0] for c in CASES])
def test_deterministic(req):
    assert predict(**req) == predict(**req)


def test_error_status_when_model_breaks(monkeypatch):
    """Any internal failure -> status 'error', never an exception (02 A4 step 10)."""
    from backend import api
    def boom():
        raise FileNotFoundError("Model file not found: models/delayband.txt")
    monkeypatch.setattr(api, "_load", boom)
    r = api.predict("ATL", "2025-06-14T22:00:00Z", "2025-06-14T16:00:00Z")
    assert r["status"] == "error" and "delayband" in r["error"]["message"]
    assert not list(VALIDATOR.iter_errors(r))
