"""F-3b (F3b.1, F3b.2, F3b.4): demo presets read from reports/demo_cases.json (L-017, L-019)."""
import json
from pathlib import Path

import pytest

from frontend import demo_cases as D
from frontend import mock_backend

ROOT = Path(__file__).resolve().parent.parent
REAL = ROOT / "reports/demo_cases.json"
SAMPLE = ROOT / "tests/fixtures/demo_cases_sample.json"
KEYS = ["id", "label", "airport", "now_utc", "target_hour_utc"]


def _write(tmp_path, obj):
    p = tmp_path / "demo_cases.json"
    p.write_text(obj if isinstance(obj, str) else json.dumps(obj))
    return p


def test_parse_real_file_labels_verbatim_in_order():
    """Presets = exactly the cases in the back end's JSON: same count, order and label text."""
    raw = json.loads(REAL.read_text())["cases"]
    presets = D.load_presets(REAL)
    assert [p["label"] for p in presets] == [c["label"] for c in raw]
    assert [p["id"] for p in presets] == [c["id"] for c in raw]
    assert presets == [{k: c[k] for k in KEYS} for c in raw]


def test_no_extra_or_auto_refusal_presets():
    presets = D.load_presets(REAL)
    assert len(presets) == len(json.loads(REAL.read_text())["cases"])
    assert not any("unknown airport" in p["label"].lower() for p in presets)
    assert not hasattr(D, "refusal_presets")


def test_no_duplicate_labels_or_ids_in_real_file():
    presets = D.load_presets(REAL)
    for k in ("id", "label"):
        assert len({p[k] for p in presets}) == len(presets)


def test_duplicate_labels_rejected(tmp_path):
    c = {"id": "a", "label": "Same", "airport": "ATL",
         "now_utc": "2025-06-14T16:00:00Z", "target_hour_utc": "2025-06-14T22:00:00Z"}
    p = _write(tmp_path, {"cases": [c, dict(c, id="b")]})
    assert D.load_presets(p) == []


def test_missing_file_gives_no_presets(tmp_path):
    assert D.load_presets(tmp_path / "nope.json") == []


@pytest.mark.parametrize("content", [
    "not json {",
    [],
    {"version": "x"},
    {"cases": []},
    {"cases": "nope"},
    {"cases": [{"id": "a", "label": "A", "airport": "ATL", "now_utc": "2025-06-14T16:00:00Z"}]},
    {"cases": [{"id": "a", "label": "A", "airport": "ATL",
                "now_utc": "2025-06-14 16:00", "target_hour_utc": "2025-06-14T22:00:00Z"}]},
    {"cases": [{"id": "a", "label": "", "airport": "ATL",
                "now_utc": "2025-06-14T16:00:00Z", "target_hour_utc": "2025-06-14T22:00:00Z"}]},
], ids=["bad_json", "list", "no_cases", "empty_cases", "cases_not_list", "missing_field",
        "bad_time", "empty_label"])
def test_invalid_file_gives_no_presets(tmp_path, content):
    p = _write(tmp_path, content if isinstance(content, str) else json.dumps(content))
    assert D.load_presets(p) == []


def test_sample_fixture_is_labelled_and_states_on_mock():
    """The mock-only sample fixture: labelled as a sample, and gives the expected mock states."""
    presets = D.load_presets(SAMPLE)
    assert len(presets) == 5 and all("mock sample" in p["label"] for p in presets)
    got = {p["id"]: mock_backend.predict(p["airport"], p["target_hour_utc"], p["now_utc"]) for p in presets}
    assert got["true_red"]["risk_level"] == "RED"
    assert got["calm"]["risk_level"] == "GREEN"
    assert got["too_soon"]["refusal"]["code"] == "LEAD_TOO_SHORT"
    assert got["too_far"]["refusal"]["code"] == "LEAD_TOO_LONG"
