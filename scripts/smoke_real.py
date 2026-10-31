"""J-1 smoke test: real predict() vs the contract. Run: python scripts/smoke_real.py"""
import json, time, pathlib, sys, jsonschema

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # glue: allow running from scripts/ (I-log)
from backend.api import predict

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "contract/schema.json").read_text())
CASES = json.loads((ROOT / "reports/demo_cases.json").read_text())["cases"]
EXTRA = [  # must be refused or errored, never crash
    {"id": "bad_airport", "airport": "XYZ", "now_utc": "2025-06-14T16:00:00Z", "target_hour_utc": "2025-06-14T22:00:00Z"},
    {"id": "not_on_hour", "airport": "ATL", "now_utc": "2025-06-14T16:00:00Z", "target_hour_utc": "2025-06-14T22:30:00Z"},
    {"id": "out_of_range", "airport": "ATL", "now_utc": "2026-01-01T00:00:00Z", "target_hour_utc": "2026-01-01T06:00:00Z"},
    {"id": "icao_code", "airport": "KDFW", "now_utc": "2025-05-06T11:00:00Z", "target_hour_utc": "2025-05-06T17:00:00Z"},
]
K = ["p_gt15", "p_gt30", "p_gt45", "p_gt60"]
rows = []
for c in CASES + EXTRA:
    t0 = time.perf_counter()
    r = predict(c["airport"], c["target_hour_utc"], c["now_utc"])
    dt = time.perf_counter() - t0
    jsonschema.validate(r, SCHEMA)
    note = r["status"]
    if r["status"] == "ok":
        p = [r["hour_delay_risk"][k] for k in K]
        assert p == sorted(p, reverse=True), f"{c['id']}: risks not monotonic"
        for d in r["drivers"]:
            assert d["observed_at_utc"] is None or d["observed_at_utc"] <= r["request"]["now_utc"], f"{c['id']}: future driver"
        assert "flights" not in r, f"{c['id']}: v1.1 has no flight list"
        e = r["delay_estimate"]
        assert r["data_period"] == "TEST", f"{c['id']}: demo case not in test period"
        note = f'{r["risk_level"]} p>45={r["hour_delay_risk"]["p_gt45"]:.2f} cap={r["capacity"]["index"]:.2f} conf={r["confidence"]["level"]} | mid={e["typical_text"]} bad={e["bad_case_text"]} ({e["bad_case_prob"]:.2f})'
    elif r["status"] == "refused":
        note = f'refused {r["refusal"]["code"]}'
    assert r == predict(c["airport"], c["target_hour_utc"], c["now_utc"]), f"{c['id']}: not deterministic"
    rows.append((c["id"], note, f"{dt:.2f}s"))
for row in rows:
    print(" | ".join(row))
