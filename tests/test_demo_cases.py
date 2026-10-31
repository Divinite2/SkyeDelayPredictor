"""F3.5: demo presets parsed from reports/demo_cases.md format."""
from pathlib import Path

from frontend import demo_cases as D
from frontend import mock_backend
from frontend.render import parse_utc

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "tests/fixtures/demo_cases_sample.md"


def test_parse_sample():
    cases = D.parse_demo_cases(SAMPLE.read_text())
    assert len(cases) == 3
    assert cases[0] == {"label": "Storm hour flagged RED, 6 h ahead (mock)", "airport": "ATL",
                        "now_utc": "2025-06-14T16:00:00Z", "target_hour_utc": "2025-06-14T22:00:00Z"}


def test_tolerant_parsing():
    text = """Intro text
| # | Scenario | Airport | Now (UTC) | Target hour (UTC) | Extra |
|---|---|---|---|---|---|
| 1 | Storm | atl | `2025-06-14T16:00:00Z` | `2025-06-14T22:00:00Z` | x |
| 2 | Broken row | DFW | not a time | 2025-06-14T22:00:00Z | y |
"""
    cases = D.parse_demo_cases(text)
    assert len(cases) == 1                      # malformed row skipped
    assert cases[0]["airport"] == "ATL" and cases[0]["label"] == "Storm"


def test_missing_file_gives_no_presets(tmp_path):
    assert D.load_presets(tmp_path / "nope.md") == []


def test_refusal_presets_derived_from_first_case():
    presets = D.load_presets(SAMPLE)
    assert len(presets) == 6
    leads = {p["label"]: (parse_utc(p["target_hour_utc"]) - parse_utc(p["now_utc"])).total_seconds() / 3600
             for p in presets}
    assert leads["Refused: 2 h ahead"] == 2
    assert leads["Refused: 13 h ahead"] == 13
    assert presets[-1]["airport"] == "ORD"


def test_presets_produce_expected_states_on_mock():
    got = {p["label"]: mock_backend.predict(p["airport"], p["target_hour_utc"], p["now_utc"])
           for p in D.load_presets(SAMPLE)}
    assert got["Storm hour flagged RED, 6 h ahead (mock)"]["risk_level"] == "RED"
    assert got["Calm GREEN hour (mock)"]["risk_level"] == "GREEN"
    assert got["Refused: 2 h ahead"]["refusal"]["code"] == "LEAD_TOO_SHORT"
    assert got["Refused: 13 h ahead"]["refusal"]["code"] == "LEAD_TOO_LONG"
    assert got["Refused: unknown airport (ORD)"]["refusal"]["code"] == "UNKNOWN_AIRPORT"
