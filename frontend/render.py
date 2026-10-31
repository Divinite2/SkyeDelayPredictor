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

ERROR_HEADLINE = ("The forecast could not be produced. Do not rely on this tool for this request.")
PERIOD_WARNING = ("This date is in the model's {period} period, so it isn't a fair test. "
                  "Use Apr–Jul 2025 for honest demos.")
# Display style for the back end's decisions. These map a level the back end already chose
# to colours/words; they never set thresholds. Shape differs too, so colour is never alone.
LEVEL_STYLE = {
    "RED":   {"colour": "#c62828", "tint": "#fdecea", "icon": "●",
              "headline": "High risk of severe delays"},
    "AMBER": {"colour": "#b57f00", "tint": "#fff6db", "icon": "▲",
              "headline": "Elevated risk of severe delays"},
    "GREEN": {"colour": "#2e7d32", "tint": "#e9f5ea", "icon": "■",
              "headline": "Low risk of severe delays"},
}
CONFIDENCE_STYLE = {
    "HIGH":   {"colour": "#2e7d32", "tint": "#e9f5ea"},
    "MEDIUM": {"colour": "#b57f00", "tint": "#fff6db"},
    "LOW":    {"colour": "#6b7280", "tint": "#eef0f3"},
}
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
    no_range = cap.get("index_low") is None and cap.get("index_high") is None
    # F3b.3 / F3.7: with no range, the back end's aar_note is shown as visible grey text
    visible = cap.get("aar_note") if no_range and cap.get("aar_note") else None
    return {"text": text, "aar": aar, "note": cap.get("aar_note"), "visible_note": visible}


def driver_lines(airport: str, drivers: list[dict], target_utc: str | None = None) -> list[dict]:
    """C4c (v1.1): show the date with the time when the observation's local date differs from
    the target hour's local date, so a reading from yesterday never looks later than 'now'."""
    tgt_day = utc_to_local(airport, parse_utc(target_utc)).date() if target_utc else None
    out = []
    for d in (drivers or [])[:3]:
        t = d.get("observed_at_utc")
        time = None
        if t:
            same_day = tgt_day is not None and utc_to_local(airport, parse_utc(t)).date() == tgt_day
            time = fmt_local(airport, t, with_date=not same_day)
        eff = d.get("effect")
        out.append({"label": d["label"], "value": d.get("value"), "time": time,
                    "effect": eff, "arrow": {"increases": "▲", "decreases": "▼"}.get(eff, "•")})
    return out


def delay_estimate_lines(est: dict | None) -> dict | None:
    """v1.1 likely-delay range. Text comes verbatim from the back end; formatting only."""
    if not est:
        return None
    one_in = round(1 / est["bad_case_level"]) if est.get("bad_case_level") else None
    return {"typical": est["typical_text"],
            "bad_label": f"Bad case (1-in-{one_in} chance)" if one_in else "Bad case",
            "bad": est["bad_case_text"],
            "bad_prob": pct(est.get("bad_case_prob")),
            "method": est.get("method")}


def risk_scale_view(ctx: dict | None, p45: float | None, level: str) -> dict | None:
    """v1.2 marker scale + one-line justification. All numbers come from the back end's
    risk_context; this only turns them into positions (% of the bar) and words."""
    if not ctx or p45 is None:
        return None
    top = ctx["scale_max"]

    def pos(x):
        return round(max(0.0, min(100.0, x / top * 100)), 1)

    word = {"RED": "red", "AMBER": "amber", "GREEN": "green"}[level]
    cut = {"RED": f"RED starts at {pct(ctx['red_min'])}",
           "AMBER": f"AMBER starts at {pct(ctx['amber_min'])}, RED at {pct(ctx['red_min'])}",
           "GREEN": f"AMBER starts at {pct(ctx['amber_min'])}"}[level]
    return {
        "marker": pos(p45), "marker_text": pct(p45),
        # keep the label inside the bar near either end (-100% = label left of the line)
        "label_shift": -100 if pos(p45) > 85 else (0 if pos(p45) < 15 else -50),
        "amber": pos(ctx["amber_min"]), "red": pos(ctx["red_min"]),
        "typical": pos(ctx["typical_p"]), "typical_text": pct(ctx["typical_p"]),
        "beyond": p45 > top, "top_text": pct(top),
        "justification": (f"Riskier than {ctx['percentile']}% of hours · "
                          f"{ctx['ratio_to_typical']:.1f}× a typical hour ({pct(ctx['typical_p'])})"),
        "why_colour": f"Shown {word} because {cut}. Severe delays are rare, so colours compare an hour "
                      f"with other hours rather than with 50%.",
        "basis": ctx["basis"],
    }


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
    sev = load_config()["severe_threshold_min"]
    return {
        "kind": "ok",
        "airport": f"{apt} ({icao})",
        "when": f"{fmt_local(apt, tgt, with_date=True)}–{fmt_local(apt, end)}",
        "lead_text": f"forecast {req['lead_time_h']} h ahead",
        "level_style": LEVEL_STYLE[resp["risk_level"]],
        "confidence_style": CONFIDENCE_STYLE[resp["confidence"]["level"]],
        "severe_label": f"> {sev} min",
        "severe_text": pct(resp["hour_delay_risk"].get(f"p_gt{sev}")),
        "request_utc": f"now {req['now_utc']} · target {req['target_hour_utc']}",
        "header": f"{apt} ({icao}) · {fmt_local(apt, tgt, with_date=True)}–{fmt_local(apt, end)} "
                  f"· forecast made {req['lead_time_h']} h ahead",
        "risk_level": resp["risk_level"],
        "risk_rows": risk_rows(resp["hour_delay_risk"]),
        "capacity": capacity_line(resp.get("capacity")),
        "drivers": driver_lines(apt, resp.get("drivers"), req["target_hour_utc"]),
        "do_text": resp["recommendation"]["text"],
        "rule": f"rule {resp['recommendation']['rule_id']}: {resp['recommendation']['triggered_by']}",
        "confidence_level": resp["confidence"]["level"],
        "confidence_reasons": " · ".join(resp["confidence"]["reasons"]),
        "delay_estimate": delay_estimate_lines(resp.get("delay_estimate")),
        "risk_scale": risk_scale_view(resp.get("risk_context"), resp["hour_delay_risk"].get(f"p_gt{sev}"),
                                      resp["risk_level"]),
        "thresholds": [f">{k}" for k in load_config()["delay_thresholds_min"]],
        "banner": period_banner(resp),
        "footer": f"Model {resp['model_version']} · generated {resp['generated_at_utc']}",
    }
