"""Mock back end: same signature as backend.api.predict (04_Data_Contract.md section 4).

Returns the example responses in contract/examples/, re-stamped to the request so the
screen shows the hour that was asked for. It decides nothing that the real back end
owns beyond choosing which example to return. Never raises.
"""
from __future__ import annotations

import copy
import re
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "contract" / "examples"
CONFIG = yaml.safe_load((ROOT / "config" / "config.yaml").read_text())

_ICAO_TO_IATA = {v["icao"]: k for k, v in CONFIG["airports"].items()}


def _load(name: str) -> dict:
    return json.loads((EXAMPLES / f"example_{name}.json").read_text())


def _parse(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _shift(ts: str | None, delta: timedelta) -> str | None:
    return None if ts is None else _fmt(_parse(ts) + delta)


def _restamp_ok(resp: dict, airport: str, target: datetime, now: datetime, lead: int) -> dict:
    """Move every timestamp in an ok example so it lines up with the requested hour."""
    delta = target - _parse(resp["request"]["target_hour_utc"])
    resp["request"] = {"airport": airport, "target_hour_utc": _fmt(target),
                       "now_utc": _fmt(now), "lead_time_h": lead}
    local_hh = target.astimezone(ZoneInfo(CONFIG["airports"][airport]["tz"])).strftime("%H:00")
    for d in resp["drivers"]:
        d["observed_at_utc"] = _shift(d["observed_at_utc"], delta)
        if d["observed_at_utc"] is None and (d["value"] or "").endswith(" local"):
            d["value"] = f"{local_hh} local"
    resp["confidence"]["reasons"] = [re.sub(r"^Lead time \d+ h$", f"Lead time {lead} h", r)
                                     for r in resp["confidence"]["reasons"]]
    resp["weather_basis"]["last_obs_utc"] = _shift(resp["weather_basis"]["last_obs_utc"], delta)
    resp["generated_at_utc"] = _shift(resp["generated_at_utc"], delta)
    for i, f in enumerate(resp["flights"], start=1):
        f["sched_dep_utc"] = _shift(f["sched_dep_utc"], delta)
        if f["dest"] == airport:
            f["dest"] = f["origin"]
        f["origin"] = airport
        f["flight_id"] = f"SIM-{airport}-{target.strftime('%Y%m%d%H')}-{i:02d}"
    return resp


def _refused(name: str, airport: str, target_s: str, now_s: str, lead, message: str) -> dict:
    resp = _load(name)
    resp["request"] = {"airport": airport, "target_hour_utc": target_s,
                       "now_utc": now_s, "lead_time_h": lead}
    resp["refusal"]["message"] = message
    return resp


def _period(target: datetime) -> str:
    d = target.date().isoformat()
    for name, label in (("test", "TEST"), ("validation", "VALIDATION")):
        if d >= CONFIG["splits"][name]["start"]:
            return label
    return "TRAIN"


def predict(airport: str, target_hour_utc: str, now_utc: str) -> dict:
    """Mock of backend.api.predict. Never raises."""
    try:
        code = (airport or "").strip().upper()
        code = _ICAO_TO_IATA.get(code, code)

        if code == "BAD":  # deliberately broken (P>45 > P>30) to test the safety check
            resp = json.loads((ROOT / "tests" / "fixtures" / "broken_monotonic.json").read_text())
            return resp

        if code == "ERR":
            resp = _load("error")
            resp["request"].update(target_hour_utc=target_hour_utc, now_utc=now_utc)
            return resp

        if code not in CONFIG["airports"]:
            return _refused("refused_airport", code, target_hour_utc, now_utc, None,
                            f"{code} is not in the processed data. This tool currently covers "
                            + " and ".join(f"{k} ({v['icao']})" for k, v in CONFIG["airports"].items())
                            + ".")

        target, now = _parse(target_hour_utc), _parse(now_utc)
        lead = int((target - now).total_seconds() // 3600)
        lo, hi = CONFIG["lead_time_hours"]["min"], CONFIG["lead_time_hours"]["max"]
        hhmm = target.strftime("%H:%M")

        if lead < lo:
            return _refused("refused_short", code, target_hour_utc, now_utc, lead,
                            (f"{hhmm} UTC is in the past." if lead < 0 else f"{hhmm} UTC is only {lead} h ahead.")
                            + f" Below {lo} h, current observations "
                            f"and controller judgement are more reliable. This tool forecasts "
                            f"{lo} to {hi} h ahead.")
        if lead > hi:
            return _refused("refused_long", code, target_hour_utc, now_utc, lead,
                            f"{hhmm} UTC is {lead} h ahead. Beyond {hi} h, weather (especially "
                            f"thunderstorms) is too unreliable to forecast usefully. This tool "
                            f"forecasts {lo} to {hi} h ahead.")

        name = "ok_red" if target.hour % 2 == 0 else "ok_green"   # alternate by hour
        resp = _restamp_ok(copy.deepcopy(_load(name)), code, target, now, lead)
        resp["data_period"] = _period(target)
        return resp

    except Exception as exc:  # contract: never raise
        return {"schema_version": "1.0", "status": "error",
                "request": {"airport": str(airport), "target_hour_utc": str(target_hour_utc),
                            "now_utc": str(now_utc), "lead_time_h": None},
                "refusal": None,
                "error": {"code": "MOCK_INTERNAL", "message": f"{type(exc).__name__}: {exc}"}}
