"""One command rebuilds everything from the raw CSV:  python run_all.py

Stages implemented so far: DATA (A1 -> Gate 1).
Later stages (features, baselines, train, evaluate, model card) are appended as they are built.
Fails loudly (non-zero exit) if any hard P0 check fails.
"""
import sys

import pandas as pd

from backend.clean_flights import clean_flights
from backend.common import path
from backend.load import load_raw, raw_header
from backend.timezone_fix import add_utc_times, verify_timezones
from backend.validate import run_checks, write_report
from backend.weather_timeline import build_weather_hourly, inspect_extremes


def stage_data() -> bool:
    print("[A1.1] loading raw CSV")
    header = raw_header()
    raw = load_raw()
    raw_counts = {"cancelled": int(raw["CANCELLED"].eq(1).sum()),
                  "diverted": int(raw["DIVERTED"].eq(1).sum())}
    print("[A1.2] UTC flight times + time-zone table check")
    df, tz_stats = add_utc_times(raw)
    tz_verify = verify_timezones(df)
    print("[A1.2/A1.3] hourly weather timeline")
    wx, wx_stats = build_weather_hourly(df)
    print("[A1.4] cleaning flights")
    fl, fl_stats = clean_flights(df)

    proc = path("processed_dir")
    proc.mkdir(parents=True, exist_ok=True)
    wx.to_parquet(proc / "weather_hourly.parquet", index=False)
    fl.to_parquet(proc / "flights_clean.parquet", index=False)

    print("[A1.5] validation report")
    checks, extra = run_checks(raw, header, raw_counts, wx, wx_stats, fl, fl_stats, tz_stats,
                               tz_verify, inspect_extremes(df))
    rep = path("reports_dir") / "validation_report.md"
    write_report(checks, extra, rep)
    for c in checks:
        print(f"  {c['id']:4s} {'PASS' if c['ok'] else 'FAIL'}  {c['check']}")
    print(f"  -> {rep}")
    return all(c["ok"] for c in checks)


if __name__ == "__main__":
    ok = stage_data()
    if not ok:
        sys.exit("A P0 data check FAILED - see reports/validation_report.md")
