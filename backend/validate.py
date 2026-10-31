"""A1.5 Validation report (V1-V10) + evidence figures for Gate 1."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from backend.common import config, path
from backend.load import DTYPES, is_banned
from backend.weather_timeline import COCO_LABEL, coco_group

HUBS = list(config()["airports"])
SEASONS = {"summer (Jun-Aug)": [6, 7, 8], "winter (Dec-Feb)": [12, 1, 2]}
PEAK_OK = range(13, 19)  # 13:00-18:00 local inclusive


def _tz(ap):
    return config()["airports"][ap]["tz"]


# ---------------------------------------------------------------- V3 time-zone repair
def timezone_check(raw: pd.DataFrame, wx: pd.DataFrame) -> tuple[list[dict], plt.Figure]:
    rows = []
    fig, axes = plt.subplots(len(HUBS), len(SEASONS), figsize=(12, 7), sharex=True)
    for i, ap in enumerate(HUBS):
        # BEFORE: raw temp on the flight row, plotted against the raw LOCAL scheduled dep hour
        r = raw[raw["ORIGIN"] == ap]
        r_month = pd.to_datetime(r["FL_DATE"]).dt.month
        # AFTER: repaired timeline, UTC obs time converted to local with zoneinfo
        w = wx[wx["airport"] == ap].copy()
        loc = w["obs_time_utc"].dt.tz_convert(_tz(ap))
        w["local_hour"], w["month"] = loc.dt.hour, loc.dt.month
        for j, (season, months) in enumerate(SEASONS.items()):
            before = (r[r_month.isin(months)].assign(h=(r["CRS_DEP_TIME"] // 100).astype(int))
                      .groupby("h")["temp_ORIGIN"].mean().astype(float))
            after = w[w["month"].isin(months)].groupby("local_hour")["temp_c"].mean()
            ax = axes[i, j]
            ax.plot(before.index, before.values, "o--", color="grey", label="before (as provided)")
            ax.plot(after.index, after.values, "o-", color="C3", label="after repair")
            ax.axvspan(13, 18, color="green", alpha=0.08)
            ax.set_title(f"{ap} {season}")
            ax.set_ylabel("mean temp °C")
            pb, pa = int(before.idxmax()), int(after.idxmax())
            rows.append({"airport": ap, "season": season, "before_coolest": int(before.idxmin()),
                         "before_peak": pb, "before_min_c": round(before.min(), 1),
                         "before_max_c": round(before.max(), 1), "after_peak": pa,
                         "after_coolest": int(after.idxmin()), "pass": pa in PEAK_OK})
    for ax in axes[-1]:
        ax.set_xlabel("local hour")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Time-zone repair: mean temperature by LOCAL hour (green band = expected peak 13-18)")
    fig.tight_layout()
    return rows, fig


# ---------------------------------------------------------------- V5 coverage
def coverage(wx: pd.DataFrame) -> tuple[dict, plt.Figure]:
    res, fig = {}, plt.figure(figsize=(10, 4))
    for ap in HUBS:
        w = wx[wx["airport"] == ap]
        local = w["obs_time_utc"].dt.tz_convert(_tz(ap))
        per_day = local.dt.date.value_counts()
        all_days = pd.date_range("2023-01-01", "2025-07-31").date
        per_day = per_day.reindex(all_days, fill_value=0)
        res[ap] = {"mean_hours_per_day": round(per_day.mean(), 2),
                   "median": float(per_day.median()), "days_with_zero": int((per_day == 0).sum()),
                   "share_by_local_hour_min": round(local.dt.hour.value_counts(normalize=True)
                                                    .reindex(range(24), fill_value=0).min(), 4)}
        plt.plot(local.dt.hour.value_counts().reindex(range(24), fill_value=0) / len(per_day),
                 "o-", label=ap)
    plt.xlabel("local hour")
    plt.ylabel("share of days with an observation")
    plt.title("Weather coverage by local hour (observations exist only where a sampled flight was)")
    plt.legend()
    plt.tight_layout()
    return res, fig


# ---------------------------------------------------------------- B1.8 coco check
def severe_by_weather(raw: pd.DataFrame, flights: pd.DataFrame) -> tuple[pd.DataFrame, plt.Figure]:
    hub = raw["ORIGIN"].isin(HUBS).to_numpy()
    coco = raw.loc[hub, "coco_ORIGIN"].astype("float64").where(lambda c: c.isin(list(COCO_LABEL)))
    f = flights.loc[hub]
    df = pd.DataFrame({"group": coco.map(coco_group).fillna("invalid/null").to_numpy(),
                       "code": coco.to_numpy(), "severe": f["severe"].to_numpy(),
                       "dep_gt45": (f["dep_delay_min"] > 45).to_numpy()})
    order = ["calm", "low_visibility", "rain", "winter", "showers", "convective", "invalid/null"]
    tab = (df.groupby("group").agg(n=("severe", "size"), severe_rate=("severe", "mean"),
                                   dep_gt45_rate=("dep_gt45", "mean"))
           .reindex([o for o in order if o in set(df["group"])]))
    codes = df.groupby("code").agg(n=("severe", "size"), severe_rate=("severe", "mean"))
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(tab.index, tab["severe_rate"] * 100, color="C0")
    for k, (n, r) in enumerate(zip(tab["n"], tab["severe_rate"])):
        ax.text(k, r * 100 + 0.5, f"{r:.0%}\nn={n}", ha="center", fontsize=8)
    ax.axhline(df["severe"].mean() * 100, ls="--", color="grey", label="overall")
    ax.set_ylabel("% departures > 45 min or cancelled")
    ax.set_title("ATL+DFW: severe-delay rate by weather group at scheduled departure (raw, all periods)")
    ax.legend()
    fig.tight_layout()
    return tab, codes, fig


# ---------------------------------------------------------------- V9 splits
def split_table(flights: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ap in HUBS + ["ALL_HUBS"]:
        dep = flights[flights["airport_dep"].isin(HUBS if ap == "ALL_HUBS" else [ap])]
        arr = flights[flights["airport_arr"].isin(HUBS if ap == "ALL_HUBS" else [ap])]
        for s in ["train", "validation", "test"]:
            d, a = dep[dep["split_dep"] == s], arr[arr["split_arr"] == s]
            rows.append({"airport": ap, "split": s, "departures": len(d),
                         "severe_rate(>45 or cancelled)": round(d["severe"].mean(), 4),
                         "dep_delay_gt45_rate": round((d["dep_delay_min"] > 45).mean(), 4),
                         "arrivals": len(a), "delivered_rate": round(a["delivered"].mean(), 4)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- report
def run_checks(raw, header, raw_full_counts, wx, wx_stats, fl, fl_stats, tz_stats, tz_verify,
               extremes) -> tuple[list[dict], dict]:
    figs = path("figures_dir")
    figs.mkdir(parents=True, exist_ok=True)
    checks, extra = [], {}

    def add(vid, name, ok, found, action):
        checks.append({"id": vid, "check": name, "ok": ok, "found": found, "action": action})

    # V1
    missing = [c for c in DTYPES if c not in header]
    add("V1", "Required columns and dtypes", not missing and len(raw) == 148_273,
        f"{len(header)} columns in file; {len(DTYPES)} required, missing: {missing or 'none'}; "
        f"{len(raw):,} rows; dates {raw['FL_DATE'].min()} → {raw['FL_DATE'].max()}; "
        f"{raw['ORIGIN'].nunique()} origin airports; " + "; ".join(
            f"{ap} {int((raw['ORIGIN'] == ap).sum()):,} dep / {int((raw['DEST'] == ap).sum()):,} arr"
            for ap in HUBS),
        "Loaded with explicit dtypes (backend/load.py)")
    # V2
    add("V2", "Duplicates", fl_stats["duplicates"] == 0, f"{fl_stats['duplicates']} on "
        "(FL_DATE, carrier, flight no., ORIGIN, DEST)", "Asserted 0 in clean_flights.py")
    # V3
    tzrows, fig = timezone_check(raw, wx)
    fig.savefig(figs / "timezone_fix.png", dpi=120)
    plt.close(fig)
    extra["tz_rows"] = tzrows
    add("V3", "Time-zone repair", all(r["pass"] for r in tzrows),
        "; ".join(f"{r['airport']} {r['season'].split()[0]}: peak {r['before_peak']}:00 → "
                  f"{r['after_peak']}:00 local" for r in tzrows),
        "Weather re-keyed local→UTC; figure reports/figures/timezone_fix.png")
    add("V3b", "Airport time-zone table vs schedule (added check, D-007)",
        tz_verify["atl_dfw_match_rate"] > 0.99,
        f"implied local arrival = CRS_ARR_TIME for {tz_verify['match_rate']:.2%} of "
        f"{tz_verify['n_checked']:,} flights ({tz_verify['atl_dfw_match_rate']:.2%} for flights "
        f"touching ATL/DFW); DST gap times shifted: {tz_stats['nonexistent_shifted']}, "
        f"ambiguous resolved: {tz_stats['ambiguous_resolved']}",
        "sched_arr_utc = sched_dep_utc + CRS_ELAPSED_TIME; mismatches listed below")
    # V4
    add("V4", "Weather conflicts", wx_stats["conflict_rate_all"] < 0.01,
        f"{wx_stats['conflicts']:,} of {wx_stats['airport_hours']:,} airport-hours "
        f"({wx_stats['conflict_rate_all']:.3%}); {wx_stats['conflict_rate_multi']:.3%} of the "
        f"{wx_stats['airport_hours_multi_source']:,} hours with >1 source row",
        "conflict_flag set; median (numeric) / mode (coco) taken")
    # V5
    cov, fig = coverage(wx)
    fig.savefig(figs / "weather_coverage.png", dpi=120)
    plt.close(fig)
    extra["coverage"] = cov
    add("V5", "Weather coverage (report only)", True,
        "; ".join(f"{ap}: {v['mean_hours_per_day']} h/day (median {v['median']:.0f}), "
                  f"{v['days_with_zero']} days with none" for ap, v in cov.items()),
        "obs_age_h feature + confidence rule + NO_RECENT_WEATHER refusal handle gaps; "
        "figure reports/figures/weather_coverage.png")
    # V6
    rn = wx_stats["range_nulled"]
    add("V6", "Range violations", True,
        ", ".join(f"{k}: {v}" for k, v in rn.items()) + f"; invalid coco (0/other): "
        f"{wx_stats['coco_invalid_to_null']}", "Nulled in source rows before combining; no rows deleted")
    # V7
    add("V7", "Fake zeros", wx_stats["snow_nonzero"] == 0,
        f"snow non-zero in {wx_stats['snow_nonzero']} source values → column dropped; "
        f"wpgt zeros nulled: {wx_stats['wpgt_zero_to_null']:,}; wpgt non-null share of "
        f"airport-hours after nulling: {wx_stats['wpgt_nonnull_share']:.2%} → "
        f"{'KEPT' if wx_stats['wpgt_kept'] else 'DROPPED (≤10%)'}", "See decisions_log D-008")
    # V8
    ok8 = (fl_stats["cancelled"] == raw_full_counts["cancelled"]
           and fl_stats["diverted"] == raw_full_counts["diverted"])
    add("V8", "Cancelled and diverted handling", ok8,
        f"cancelled {fl_stats['cancelled']:,} (raw {raw_full_counts['cancelled']:,}); diverted "
        f"{fl_stats['diverted']:,} (raw {raw_full_counts['diverted']:,}); cancelled-with-delay "
        f"flagged {fl_stats['cancelled_with_delay']}; non-cancelled rows with no DEP_DELAY: "
        f"{fl_stats['missing_delay_not_cancelled']}",
        "Cancelled → gt60 and not delivered; diverted keep dep delay, not delivered")
    # V9
    st = split_table(fl)
    extra["splits"] = st
    add("V9", "Split sizes", bool((st["departures"] > 0).all()),
        "see split table below", "Split by target hour (UTC); 12 h purge applied at feature stage (A2)")
    # V10
    banned = [c for c in wx.columns if is_banned(c)]
    add("V10", "Banned columns", not banned,
        f"weather_hourly (the only feature source so far): {banned or 'none'}. "
        "Feature table does not exist yet; same check re-runs on it in A2 + tests/test_leakage.py",
        "is_banned() in backend/load.py implements the 02 §A2 list")
    # B1.8
    tab, codes, fig = severe_by_weather(raw, fl)
    fig.savefig(figs / "severe_by_weather.png", dpi=120)
    plt.close(fig)
    extra["severe_by_weather"], extra["severe_by_code"] = tab, codes
    extra["extremes"] = extremes
    extra["tz_verify"], extra["wx_stats"], extra["fl_stats"] = tz_verify, wx_stats, fl_stats
    return checks, extra


def write_report(checks, extra, out_path):
    L = ["# Validation report (Gate 1 / Checkpoint B-1)", "",
         "Generated by `python run_all.py`. All times UTC unless stated.", "",
         "| # | Check | Result | Found | Action |", "|---|---|---|---|---|"]
    for c in checks:
        L.append(f"| {c['id']} | {c['check']} | {'✅' if c['ok'] else '❌'} | {c['found']} | {c['action']} |")
    L += ["", "## V3 Time-zone repair detail", "",
          pd.DataFrame(extra["tz_rows"]).to_markdown(index=False), "",
          "## V3b Time-zone table: lowest match rates", "",
          f"Origins: {extra['tz_verify']['worst_origins']}", "",
          f"Destinations: {extra['tz_verify']['worst_dests']}", "",
          "## V9 Split table (departures by scheduled-departure UTC; arrivals by scheduled-arrival UTC)",
          "", extra["splits"].to_markdown(index=False), "",
          "## B1.8 Weather-code check: severe-delay rate by weather group (ATL+DFW departures)", "",
          "Weather at the flight's own scheduled departure hour, as provided. **Evidence only, "
          "never a feature** (that would be leakage).", "",
          extra["severe_by_weather"].assign(
              severe_rate=lambda t: t["severe_rate"].round(3),
              dep_gt45_rate=lambda t: t["dep_gt45_rate"].round(3)).to_markdown(), "",
          "By code (n, severe rate): " + "; ".join(
              f"{int(k)}: {int(r.n)}, {r.severe_rate:.0%}" for k, r in extra["severe_by_code"].iterrows()),
          "", "## A1.3 Extreme wind / gust rows (wpgt ≥ 200 or wspd ≥ 90 km/h)", "",
          extra["extremes"].to_markdown(index=False), "",
          "## Raw cleaning statistics", "", f"- weather: {extra['wx_stats']}",
          f"- flights: {extra['fl_stats']}"]
    out_path.write_text("\n".join(L) + "\n")
