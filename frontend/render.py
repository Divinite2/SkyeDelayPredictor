"""Pure display helpers: response dict / config -> display pieces. No Streamlit here,
so everything is unit-testable. Formatting only; never decides risk, colour or advice.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parent.parent
UTC_FMT = "%Y-%m-%dT%H:%M:%SZ"
DASH = "—"

SIM_NOTE = ("Simulated flights to illustrate a full schedule. Each shows the risk for the "
            "whole hour, not an individual flight prediction.")
ERROR_HEADLINE = ("The forecast could not be produced. Do not rely on this tool for this request.")
PERIOD_WARNING = ("This date is in the model's {period} period, so it isn't a fair test. "
                  "Use Apr–Jul 2025 for honest demos.")
REFUSAL_TITLES = {
    "LEAD_TOO_SHORT": "Too soon to forecast",
    "LEAD_TOO_LONG": "Too far ahead to forecast",
    "UNKNOWN_AIRPORT": "Airport not in data",
    "NOT_ON_THE_HOUR": "Cannot forecast this request",
    "OUT_OF_DATA_RANGE": "Cannot forecast this request",
    "NO_RECENT_WEATHER": "Cannot forecast this request",
}


# ---------- config & schema ----------
@lru_cache(maxsize=1)
def load_config() -> dict:
    return yaml.safe_load((ROOT / "config" / "config.yaml").read_text())


@lru_cache(maxsize=1)
def load_schema() -> dict:
    return json.loads((ROOT / "contract" / "schema.json").read_text())


def validate_response(resp: dict) -> str | None:
    """Return None if the response matches contract/schema.json, else a short reason."""
    import jsonschema
    try:
        jsonschema.Draft202012Validator(load_schema()).validate(resp)
        return None
    except jsonschema.ValidationError as exc:
        path = "/".join(str(p) for p in exc.absolute_path) or "(root)"
        return f"Response does not match contract at '{path}': {exc.message}"


# ---------- time conversion (local on screen, UTC to the back end) ----------
def tz_for(airport: str) -> ZoneInfo:
    return ZoneInfo(load_config()["airports"][airport]["tz"])


def local_to_utc(airport: str, day: date, hour: int) -> datetime:
    """Local wall-clock hour at the airport -> aware UTC datetime."""
    local = datetime(day.year, day.month, day.day, hour, tzinfo=tz_for(airport))
    return local.astimezone(timezone.utc)


def utc_to_local(airport: str, ts_utc: datetime) -> datetime:
    return ts_utc.astimezone(tz_for(airport))


def to_utc_str(ts_utc: datetime) -> str:
    return ts_utc.astimezone(timezone.utc).strftime(UTC_FMT)


def parse_utc(ts: str) -> datetime:
    return datetime.strptime(ts, UTC_FMT).replace(tzinfo=timezone.utc)


def fmt_local(airport: str, ts_utc: datetime | str, with_date: bool = False) -> str:
    """'18:00 EDT' or 'Sat 14 Jun 18:00 EDT'."""
    if isinstance(ts_utc, str):
        ts_utc = parse_utc(ts_utc)
    loc = utc_to_local(airport, ts_utc)
    return loc.strftime("%a %d %b %H:%M %Z" if with_date else "%H:%M %Z")


def target_options(now_utc: datetime) -> list[tuple[int, datetime]]:
    """(lead_h, target_utc) for the configured window, built in UTC so a DST change can
    never skip or repeat an hour. Convenience only; the back end enforces the rule."""
    lt = load_config()["lead_time_hours"]
    return [(h, now_utc + timedelta(hours=h)) for h in range(lt["min"], lt["max"] + 1)]


# ---------- number formatting ----------
def pct(p: float | None) -> str:
    """0.384 -> '38%'. Standard (half-up) rounding. None -> '—', never '0%'."""
    if p is None:
        return DASH
    whole = (Decimal(str(p)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{int(whole)}%"


def bar_width(p: float | None) -> float:
    """Bar length in % of track. Pure formatting."""
    return 0.0 if p is None else max(0.0, min(100.0, p * 100))


def is_monotonic(risk: dict) -> bool:
    keys = [f"p_gt{k}" for k in load_config()["delay_thresholds_min"]]
    vals = [risk.get(k) for k in keys]
    if any(v is None for v in vals):
        return False
    return all(a >= b for a, b in zip(vals, vals[1:]))


# ---------- card pieces ----------
def risk_rows(risk: dict) -> list[dict]:
    cfg = load_config()
    sev = cfg["severe_threshold_min"]
    return [{"label": f"> {k} min", "p": risk.get(f"p_gt{k}"), "text": pct(risk.get(f"p_gt{k}")),
             "width": bar_width(risk.get(f"p_gt{k}")), "severe": k == sev}
            for k in cfg["delay_thresholds_min"]]


def capacity_line(cap: dict | None) -> dict | None:
    """None -> line hidden (index missing)."""
    if not cap or cap.get("index") is None:
        return None
    text = f"{pct(cap['index'])} of scheduled arrivals on time"
    if cap.get("index_low") is not None and cap.get("index_high") is not None:
        text += f" (likely {pct(cap['index_low'])[:-1]}–{pct(cap['index_high'])})"
    aar = None
    if cap.get("aar_est") is not None:
        aar = f"≈ {round(cap['aar_est'])} arrivals/h"
        if cap.get("aar_low") is not None and cap.get("aar_high") is not None:
            aar += f" ({round(cap['aar_low'])}–{round(cap['aar_high'])})"
    return {"text": text, "aar": aar, "note": cap.get("aar_note")}


def driver_lines(airport: str, drivers: list[dict]) -> list[dict]:
    out = []
    for d in (drivers or [])[:3]:
        t = d.get("observed_at_utc")
        out.append({"label": d["label"], "value": d.get("value"),
                    "time": fmt_local(airport, t) if t else None,
                    "effect": d.get("effect")})
    return out


def flight_rows(airport: str, flights: list[dict]) -> list[dict]:
    keys = [f"p_gt{k}" for k in load_config()["delay_thresholds_min"]]
    return [{"id": f["flight_id"], "carrier": f["carrier"],
             "route": f"{f['origin']}→{f['dest']}",
             "dep": fmt_local(airport, f["sched_dep_utc"]),
             "tag": "SIMULATED",
             "probs": [pct(f.get(k)) for k in keys]}
            for f in (flights or [])]


def period_banner(resp: dict) -> str | None:
    p = resp.get("data_period")
    return None if p in (None, "TEST") else PERIOD_WARNING.format(period=p)


def view_model(resp: dict) -> dict:
    """Decide which card to show. Schema or monotonic failure -> error card, never numbers."""
    problem = validate_response(resp)
    if problem:
        return {"kind": "error", "message": problem}
    status = resp["status"]
    if status == "error":
        return {"kind": "error", "message": resp["error"].get("message", "")}
    if status == "refused":
        code = resp["refusal"]["code"]
        return {"kind": "refused", "title": REFUSAL_TITLES.get(code, "Cannot forecast this request"),
                "message": resp["refusal"]["message"], "code": code}
    if not is_monotonic(resp["hour_delay_risk"]):
        return {"kind": "error",
                "message": "Inconsistent risk values received (a higher delay threshold had a higher "
                           "probability than a lower one)."}

    req, apt = resp["request"], resp["request"]["airport"]
    tgt = parse_utc(req["target_hour_utc"])
    end = tgt + timedelta(hours=1)
    icao = load_config()["airports"].get(apt, {}).get("icao", "")
    return {
        "kind": "ok",
        "header": f"{apt} ({icao}) · {fmt_local(apt, tgt, with_date=True)}–{fmt_local(apt, end)} "
                  f"· forecast made {req['lead_time_h']} h ahead",
        "risk_level": resp["risk_level"],
        "risk_rows": risk_rows(resp["hour_delay_risk"]),
        "capacity": capacity_line(resp.get("capacity")),
        "drivers": driver_lines(apt, resp.get("drivers")),
        "do_text": resp["recommendation"]["text"],
        "rule": f"rule {resp['recommendation']['rule_id']}: {resp['recommendation']['triggered_by']}",
        "confidence_level": resp["confidence"]["level"],
        "confidence_reasons": " · ".join(resp["confidence"]["reasons"]),
        "flights": flight_rows(apt, resp.get("flights")),
        "thresholds": [f">{k}" for k in load_config()["delay_thresholds_min"]],
        "banner": period_banner(resp),
        "footer": f"Model {resp['model_version']} · generated {resp['generated_at_utc']}",
    }
