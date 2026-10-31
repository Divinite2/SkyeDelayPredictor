"""Generates the six contract example responses (04_Data_Contract.md §8).

Values are hand-picked illustrative numbers, NOT model output. Written as a script so the
"flight probabilities == hour_delay_risk" rule holds by construction. Run:
    python contract/make_examples.py
"""
import json
from pathlib import Path

OUT = Path(__file__).parent / "examples"
NOTE = ("Nominal arrival rate not configured; capacity shown as share of scheduled "
        "arrivals delivered on time.")
TEXT = {
    "RED-1": "Consider a pre-emptive arrival-rate reduction or ground delay programme for this hour.",
    "AMBER-1": "Elevated risk: prepare contingency and re-check at the next forecast update.",
    "GREEN-1": "No action suggested by the model.",
}


def flights(airport, hour_key, rows, risk):
    out = []
    for i, (carrier, dest, dep) in enumerate(rows, 1):
        out.append({"flight_id": f"SIM-{airport}-{hour_key}-{i:02d}", "carrier": carrier,
                    "origin": airport, "dest": dest, "sched_dep_utc": dep,
                    "source": "SIMULATED", **risk})
    return out


def ok_red():
    risk = {"p_gt15": 0.702, "p_gt30": 0.501, "p_gt45": 0.384, "p_gt60": 0.281}
    return {
        "schema_version": "1.0", "status": "ok",
        "request": {"airport": "ATL", "target_hour_utc": "2025-06-14T22:00:00Z",
                    "now_utc": "2025-06-14T16:00:00Z", "lead_time_h": 6},
        "risk_level": "RED", "hour_delay_risk": risk,
        "capacity": {"index": 0.55, "index_low": 0.42, "index_high": 0.68,
                     "aar_est": None, "aar_low": None, "aar_high": None, "aar_note": NOTE},
        "drivers": [
            {"label": "Thunderstorm reported", "value": "Thunderstorm (code 25)",
             "observed_at_utc": "2025-06-14T15:00:00Z", "effect": "increases"},
            {"label": "Strong wind (crosswind worst case)", "value": "30 km/h",
             "observed_at_utc": "2025-06-14T15:00:00Z", "effect": "increases"},
            {"label": "Evening peak hour", "value": "18:00 local",
             "observed_at_utc": None, "effect": "increases"},
        ],
        "recommendation": {"rule_id": "RED-1", "text": TEXT["RED-1"], "triggered_by": "p_gt45 >= 0.30"},
        "confidence": {"level": "MEDIUM",
                       "reasons": ["Lead time 6 h", "Last weather reading 1 h before forecast"]},
        "weather_basis": {"last_obs_utc": "2025-06-14T15:00:00Z", "obs_age_h": 1},
        "flights": flights("ATL", "2025061422", [
            ("DL", "LGA", "2025-06-14T22:05:00Z"), ("DL", "MCO", "2025-06-14T22:15:00Z"),
            ("WN", "BWI", "2025-06-14T22:25:00Z"), ("DL", "ORD", "2025-06-14T22:40:00Z"),
            ("F9", "DEN", "2025-06-14T22:55:00Z")], risk),
        "data_period": "TEST", "model_version": "delayband-EXAMPLE-0000000",
        "generated_at_utc": "2025-06-14T16:00:02Z", "refusal": None, "error": None,
    }


def ok_green():
    risk = {"p_gt15": 0.143, "p_gt30": 0.081, "p_gt45": 0.052, "p_gt60": 0.037}
    return {
        "schema_version": "1.0", "status": "ok",
        "request": {"airport": "DFW", "target_hour_utc": "2025-05-06T15:00:00Z",
                    "now_utc": "2025-05-06T11:00:00Z", "lead_time_h": 4},
        "risk_level": "GREEN", "hour_delay_risk": risk,
        "capacity": {"index": 0.86, "index_low": 0.74, "index_high": 0.97,
                     "aar_est": None, "aar_low": None, "aar_high": None, "aar_note": NOTE},
        "drivers": [
            {"label": "Fair weather", "value": "Fair (code 2)",
             "observed_at_utc": "2025-05-06T11:00:00Z", "effect": "decreases"},
            {"label": "Morning hour", "value": "10:00 local",
             "observed_at_utc": None, "effect": "decreases"},
        ],
        "recommendation": {"rule_id": "GREEN-1", "text": TEXT["GREEN-1"], "triggered_by": "no RED or AMBER condition met"},
        "confidence": {"level": "HIGH",
                       "reasons": ["Lead time 4 h", "Last weather reading 0 h before forecast"]},
        "weather_basis": {"last_obs_utc": "2025-05-06T11:00:00Z", "obs_age_h": 0},
        "flights": flights("DFW", "2025050615", [
            ("AA", "ORD", "2025-05-06T15:00:00Z"), ("AA", "LAX", "2025-05-06T15:10:00Z"),
            ("AA", "MIA", "2025-05-06T15:20:00Z"), ("UA", "IAH", "2025-05-06T15:35:00Z"),
            ("AA", "PHX", "2025-05-06T15:50:00Z")], risk),
        "data_period": "TEST", "model_version": "delayband-EXAMPLE-0000000",
        "generated_at_utc": "2025-05-06T11:00:01Z", "refusal": None, "error": None,
    }


def refused(code, airport, target, now, lead, message):
    return {"schema_version": "1.0", "status": "refused",
            "request": {"airport": airport, "target_hour_utc": target, "now_utc": now,
                        "lead_time_h": lead},
            "refusal": {"code": code, "message": message}, "error": None}


EXAMPLES = {
    "example_ok_red": ok_red(),
    "example_ok_green": ok_green(),
    "example_refused_short": refused(
        "LEAD_TOO_SHORT", "ATL", "2025-06-14T18:00:00Z", "2025-06-14T16:00:00Z", 2,
        "18:00 UTC is only 2 h ahead. Below 3 h, current observations and controller judgement "
        "are more reliable. This tool forecasts 3 to 12 h ahead."),
    "example_refused_long": refused(
        "LEAD_TOO_LONG", "ATL", "2025-06-15T05:00:00Z", "2025-06-14T16:00:00Z", 13,
        "05:00 UTC is 13 h ahead. Beyond 12 h, weather (especially thunderstorms) is too "
        "unreliable to forecast delays usefully. This tool forecasts 3 to 12 h ahead."),
    "example_refused_airport": refused(
        "UNKNOWN_AIRPORT", "XYZ", "2025-06-14T22:00:00Z", "2025-06-14T16:00:00Z", 6,
        "Airport 'XYZ' is not supported. This tool covers ATL (KATL) and DFW (KDFW)."),
    "example_error": {"schema_version": "1.0", "status": "error",
                      "request": {"airport": "ATL", "target_hour_utc": "2025-06-14T22:00:00Z",
                                  "now_utc": "2025-06-14T16:00:00Z", "lead_time_h": 6},
                      "refusal": None,
                      "error": {"code": "INTERNAL",
                                "message": "Model file not found: models/delayband.txt"}},
}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, body in EXAMPLES.items():
        (OUT / f"{name}.json").write_text(json.dumps(body, indent=2) + "\n")
        print("wrote", OUT / f"{name}.json")
