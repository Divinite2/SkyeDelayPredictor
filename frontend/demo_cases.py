"""Demo presets (F3.5), read from reports/demo_cases.md (back end, B3.8).

Expected format: a markdown table whose header includes columns for airport, now and
target (UTC ISO 8601 with Z). Optional columns: case / label / description.
Example:
| case | airport | now_utc | target_hour_utc | note |
|---|---|---|---|---|
| Storm hour flagged RED | ATL | 2025-06-14T16:00:00Z | 2025-06-14T22:00:00Z | ... |
Parsing is tolerant: column names are matched by keyword, extra columns ignored.
Refusal presets (2 h, 13 h, unknown airport) are derived from the first case.
"""
from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path

from frontend import render as R

DEFAULT_PATH = R.ROOT / "reports" / "demo_cases.md"
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def _cells(line: str) -> list[str]:
    return [c.strip().strip("`") for c in line.strip().strip("|").split("|")]


def _find(cols: list[str], *keys: str) -> int | None:
    for i, c in enumerate(cols):
        if any(k in c.lower() for k in keys):
            return i
    return None


def parse_demo_cases(text: str) -> list[dict]:
    cases, header = [], None
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            header = None if not line.strip() else header
            continue
        cells = _cells(line)
        if header is None:
            low = [c.lower() for c in cells]
            if any("airport" in c for c in low) and any("now" in c for c in low) \
                    and any("target" in c for c in low):
                header = {"airport": _find(cells, "airport"),
                          "now": _find(cells, "now"),
                          "target": _find(cells, "target"),
                          "label": _find(cells, "case", "label", "description", "scenario")}
            continue
        if set("".join(cells)) <= set("-: "):
            continue  # separator row
        try:
            apt = cells[header["airport"]].upper()
            now = _UTC.search(cells[header["now"]]).group(0)
            tgt = _UTC.search(cells[header["target"]]).group(0)
        except (AttributeError, IndexError, TypeError):
            continue  # skip malformed rows rather than fail the page
        label = cells[header["label"]] if header["label"] is not None and header["label"] < len(cells) else ""
        cases.append({"label": label or f"Case {len(cases) + 1}", "airport": apt,
                      "now_utc": now, "target_hour_utc": tgt})
    return cases


def refusal_presets(base: dict) -> list[dict]:
    now = R.parse_utc(base["now_utc"])
    return [
        {"label": "Refused: 2 h ahead", "airport": base["airport"], "now_utc": base["now_utc"],
         "target_hour_utc": R.to_utc_str(now + timedelta(hours=2))},
        {"label": "Refused: 13 h ahead", "airport": base["airport"], "now_utc": base["now_utc"],
         "target_hour_utc": R.to_utc_str(now + timedelta(hours=13))},
        {"label": "Refused: unknown airport (ORD)", "airport": "ORD", "now_utc": base["now_utc"],
         "target_hour_utc": base["target_hour_utc"]},
    ]


def load_presets(path: Path = DEFAULT_PATH) -> list[dict]:
    """All presets, or [] if the file is missing or has no valid rows."""
    try:
        cases = parse_demo_cases(Path(path).read_text())
    except OSError:
        return []
    return cases + refusal_presets(cases[0]) if cases else []
