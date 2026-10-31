"""Demo presets (F3.5 / F-3b, L-017, L-019), read from reports/demo_cases.json (back end, B3.8).

Expected format (written by run_all.py: build_demo_cases()):
    {"version": "...", "cases": [{"id", "label", "airport", "now_utc", "target_hour_utc"}, ...]}

Rules:
- Every case in the file becomes one preset, in file order, with its label shown verbatim.
- No hard-coded ids and no extra presets (the back end already supplies its refusal cases).
- If the file is missing or invalid, load_presets() returns [] and the app hides the picker.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from frontend import render as R

DEFAULT_PATH = R.ROOT / "reports" / "demo_cases.json"
MOCK_SAMPLE_PATH = R.ROOT / "tests" / "fixtures" / "demo_cases_sample.json"  # mock mode only
REQUIRED = ("id", "label", "airport", "now_utc", "target_hour_utc")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class InvalidDemoCases(ValueError):
    """The demo-cases JSON does not have the expected shape."""


def parse_demo_cases(text: str) -> list[dict]:
    """JSON text -> list of cases (file order, labels verbatim). Raises InvalidDemoCases."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidDemoCases(f"not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list) or not data["cases"]:
        raise InvalidDemoCases("expected an object with a non-empty 'cases' list")
    cases = []
    for i, c in enumerate(data["cases"]):
        if not isinstance(c, dict) or any(not isinstance(c.get(k), str) or not c[k] for k in REQUIRED):
            raise InvalidDemoCases(f"case {i}: needs non-empty string fields {REQUIRED}")
        if not (_UTC.match(c["now_utc"]) and _UTC.match(c["target_hour_utc"])):
            raise InvalidDemoCases(f"case {i}: times must be UTC 'YYYY-MM-DDTHH:MM:SSZ'")
        cases.append({k: c[k] for k in REQUIRED})
    for k in ("id", "label"):
        vals = [c[k] for c in cases]
        if len(set(vals)) != len(vals):
            raise InvalidDemoCases(f"duplicate {k} values")
    return cases


def load_presets(path: Path = DEFAULT_PATH) -> list[dict]:
    """All presets from the JSON file, or [] if it is missing or invalid."""
    try:
        return parse_demo_cases(Path(path).read_text())
    except (OSError, InvalidDemoCases):
        return []
