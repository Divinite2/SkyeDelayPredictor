"""F3.2 / F3.3: the adapter passes real responses through untouched and never crashes."""
import copy
import json
import sys
import types
from pathlib import Path

import pytest

from frontend import backend_adapter as A
from frontend.render import validate_response, view_model

ROOT = Path(__file__).resolve().parent.parent
RED = json.loads((ROOT / "contract/examples/example_ok_red.json").read_text())


@pytest.fixture
def fake_real_backend(monkeypatch):
    """Install a fake backend.api whose predict() returns a fixed response."""
    calls = []
    canned = copy.deepcopy(RED)
    # Deliberately different from what the mock would produce for this request:
    # if anything re-stamped it, these values would change.
    canned["request"]["target_hour_utc"] = "2025-06-14T22:00:00Z"
    canned["model_version"] = "real-model-xyz"

    def predict(airport, target_hour_utc, now_utc):
        calls.append((airport, target_hour_utc, now_utc))
        return canned

    pkg, api = types.ModuleType("backend"), types.ModuleType("backend.api")
    api.predict = predict
    pkg.api = api
    monkeypatch.setitem(sys.modules, "backend", pkg)
    monkeypatch.setitem(sys.modules, "backend.api", api)
    return canned, calls


def test_real_response_passes_through_untouched(fake_real_backend):
    canned, calls = fake_real_backend
    snapshot = copy.deepcopy(canned)
    predict = A.load_predict("real")
    out = predict("DFW", "2025-07-01T03:00:00Z", "2025-06-30T20:00:00Z")
    assert out is canned            # same object, not a rebuilt copy
    assert out == snapshot          # and not mutated
    assert calls == [("DFW", "2025-07-01T03:00:00Z", "2025-06-30T20:00:00Z")]


def test_import_failure_shows_error_card(monkeypatch):
    monkeypatch.setitem(sys.modules, "backend", None)      # forces ImportError
    monkeypatch.setitem(sys.modules, "backend.api", None)
    out = A.load_predict("real")("ATL", "2025-06-14T22:00:00Z", "2025-06-14T16:00:00Z")
    assert out["status"] == "error" and out["error"]["code"] == "BACKEND_UNAVAILABLE"
    assert validate_response(out) is None
    assert view_model(out)["kind"] == "error"


def test_exception_inside_predict_shows_error_card(monkeypatch):
    api = types.ModuleType("backend.api")

    def boom(*_):
        raise RuntimeError("model file missing")
    api.predict = boom
    monkeypatch.setitem(sys.modules, "backend", types.ModuleType("backend"))
    monkeypatch.setitem(sys.modules, "backend.api", api)
    out = A.load_predict("real")("ATL", "2025-06-14T22:00:00Z", "2025-06-14T16:00:00Z")
    assert out["error"]["code"] == "BACKEND_EXCEPTION"
    assert view_model(out)["kind"] == "error"


def test_mode_selection(monkeypatch):
    monkeypatch.setenv("BACKEND", "real")
    assert A.backend_mode() == "real"
    monkeypatch.setenv("BACKEND", "mock")
    assert A.backend_mode() == "mock"
    monkeypatch.delenv("BACKEND")
    assert A.backend_mode() == "mock"


def test_mock_mode_still_works():
    out = A.load_predict("mock")("ATL", "2025-06-14T22:00:00Z", "2025-06-14T16:00:00Z")
    assert out["status"] == "ok" and validate_response(out) is None
