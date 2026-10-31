"""One command rebuilds everything from the raw CSV:  python run_all.py

Stages: DATA (A1, Gate 1) -> FEATURES (A2) -> BASELINES + MODELS (A3) -> EVALUATION (validation)
-> one TEST run (B2.9) -> reports + model card.
`--no-test` skips the test-set evaluation (used only while developing; see decisions_log).
Fails loudly (non-zero exit) if any hard P0 check fails.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd

from backend.baselines import THRESH, Climatology, LogisticBaseline, exceed_targets
from backend.clean_flights import clean_flights
from backend.common import config, path
from backend.evaluate import (HEADLINE, SEV_DEF, bootstrap_brier_diff, capacity_hourly,
                              capacity_metrics, capacity_range, delay_metrics, failure_cases_md,
                              hour_table, seasonal_table)
from backend.features import FEATURES, Context, build_rows, save_rows
from backend.load import is_banned, load_raw, raw_header
from backend.timezone_fix import add_utc_times, verify_timezones
from backend.train import (predict_capacity, predict_delay, train_capacity_model,
                           train_delay_model)
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
    write_report(checks, extra, path("reports_dir") / "validation_report.md")
    for c in checks:
        print(f"  {c['id']:4s} {'PASS' if c['ok'] else 'FAIL'}  {c['check']}")
    return all(c["ok"] for c in checks)


def git_sha():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=path("models_dir").parent,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "nogit"


def md(df):
    return df.to_markdown(index=False)


def stage_model(run_test: bool) -> bool:
    proc, models_dir, rep = path("processed_dir"), path("models_dir"), path("reports_dir")
    models_dir.mkdir(exist_ok=True)
    fl = pd.read_parquet(proc / "flights_clean.parquet")
    wx = pd.read_parquet(proc / "weather_hourly.parquet")

    print("[A2] features")
    ctx = Context(fl, wx)
    dep, dep_stats = build_rows(ctx, fl, "dep")
    arr, arr_stats = build_rows(ctx, fl, "arr")
    banned = [c for c in FEATURES if is_banned(c)]
    assert not banned, f"banned columns in feature list: {banned}"
    save_rows(dep, "features")
    save_rows(arr, "cap_features")
    joblib.dump(ctx, models_dir / "context.joblib")
    S = {s: dep[dep["split"] == s].reset_index(drop=True) for s in ["train", "validation", "test"]}
    C = {s: arr[arr["split"] == s].reset_index(drop=True) for s in ["train", "validation", "test"]}

    print("[A3] baselines B0 / B1")
    one = S["train"].drop_duplicates("flight_id")
    b0 = Climatology().fit(one, exceed_targets(one["label"]))
    b1 = LogisticBaseline().fit(S["train"], S["train"]["label"])
    one_c = C["train"].drop_duplicates("flight_id")
    b0c = Climatology().fit(one_c, {"delivered": one_c["label"].to_numpy()})

    print("[A3] LightGBM delay-band model (random search on validation)")
    m_delay, p_delay, search = train_delay_model(S["train"], S["validation"])
    print("[A3] LightGBM capacity model")
    m_cap, p_cap = train_capacity_model(C["train"], C["validation"])
    m_delay.save_model(str(models_dir / "delayband.txt"), num_iteration=m_delay.best_iteration)
    m_cap.save_model(str(models_dir / "capacity.txt"), num_iteration=m_cap.best_iteration)
    joblib.dump({"b0": b0, "b1": b1, "b0_capacity": b0c}, models_dir / "baselines.joblib")

    def evaluate(split):
        d, c = S[split], C[split]
        E = {"B0": b0.predict_exceed(d), "B1": b1.predict_exceed(d), "LGBM": predict_delay(m_delay, d)}
        for name, e in E.items():  # B2.5 / Gate 2c: monotonic on every row
            assert np.all(np.diff(e, axis=1) <= 1e-12), f"{name} monotonicity violated"
        dm = delay_metrics(d, E)
        boot = pd.DataFrame([bootstrap_brier_diff(d, E["LGBM"], E["B0"], L) for L in HEADLINE])
        cp = {"B0": b0c.predict(c, "delivered"), "LGBM": predict_capacity(m_cap, c)}
        ch = capacity_hourly(c, cp)
        cm = capacity_metrics(ch, ["B0", "LGBM"])
        cap_dep = predict_capacity(m_cap, d)  # hour-level features are shared
        return dict(E=E, dm=dm, boot=boot, ch=ch, cm=cm, cap_dep=cap_dep)

    print("[A3] evaluating on VALIDATION")
    V = evaluate("validation")
    cap_rng = capacity_range(V["ch"], "LGBM")
    T = None
    if run_test:
        print("[B2.9] single TEST-set run (tuning frozen)")
        T = evaluate("test")

    # ------------------------------------------------------------------ checks (Gate 2)
    gate = {}
    v = V["dm"]
    def b45(L, model, df=v):
        return df[(df.lead == L) & (df.airport == "ALL") & (df.model == model)]["brier_gt45"].iloc[0]
    gate["beats_B0_brier45_L3"] = bool(b45(3, "LGBM") < b45(3, "B0"))
    gate["beats_B0_brier45_L6"] = bool(b45(6, "LGBM") < b45(6, "B0"))
    max_auc = float(np.nanmax(pd.concat([V["dm"]] + ([T["dm"]] if T else []))["roc_auc_gt45"]))
    gate["max_roc_auc"] = round(max_auc, 4)
    gate["smell_test_ok"] = max_auc <= 0.95
    gate["monotonic_ok"] = True  # asserted above; would have raised

    # ------------------------------------------------------------------ reports
    write_metrics(V, T, search, dep_stats, arr_stats, fl, gate)
    fc = ["# Failure cases (B2.10)", "",
          f"Severe = **{SEV_DEF}**. Every rate shows its count. Picked automatically by rule "
          "(miss = GREEN hour with the highest observed severe share; false alarm = RED hour with "
          "all flights on time and the highest P(>45)); the reasons were then checked by hand.", ""]
    for split, R in [("validation", V)] + ([("test", T)] if T else []):
        h = hour_table(S[split], R["E"]["LGBM"], R["cap_dep"], 6)
        fc.append(failure_cases_md(split, h, S[split], fl, ctx, 6))
    (rep / "failure_cases.md").write_text("\n".join(fc) + "\n")

    card = {
        "model_version": f"delayband-{datetime.now(timezone.utc):%Y%m%d}-{git_sha()}",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "airports": list(config()["airports"]),
        "training_period": config()["splits"]["train"],
        "validation_period": config()["splits"]["validation"],
        "test_period": config()["splits"]["test"],
        "test_evaluated": bool(run_test),
        "lead_times_h": [3, 12],
        "features": FEATURES,
        "delay_model": {"file": "models/delayband.txt", "type": "LightGBM multiclass (5 ordered bands)",
                        "params": {k: v for k, v in p_delay.items() if k != "verbose"},
                        "best_iteration": m_delay.best_iteration},
        "capacity_model": {"file": "models/capacity.txt", "type": "LightGBM binary (delivered on time)",
                           "params": {k: v for k, v in p_cap.items() if k != "verbose"},
                           "best_iteration": m_cap.best_iteration,
                           "range_offsets_by_lead": cap_rng,
                           "note": "AAR is not in the provided data. This is a delivered-on-time arrival index from a ~1% flight sample."},
        "severe_definition": SEV_DEF,
        "training_rows": dep_stats["rows_per_split"], "capacity_rows": arr_stats["rows_per_split"],
        "validation_scores": V["dm"][(V["dm"].airport == "ALL") & V["dm"].lead.isin(HEADLINE)]
            .to_dict(orient="records"),
        "validation_capacity_rmse": V["cm"][(V["cm"].airport == "ALL") & V["cm"].lead.isin(HEADLINE)]
            .to_dict(orient="records"),
        "gate2": gate,
    }
    (models_dir / "model_card.json").write_text(json.dumps(card, indent=2, default=str))
    print("  gate:", gate)
    return gate["smell_test_ok"] and gate["monotonic_ok"]


def headline(dm, cols):
    d = dm[dm.lead.isin(HEADLINE)]
    return d[["lead", "airport", "model", "n_flights", "n_severe", "base_rate_gt45"] + cols]


def write_metrics(V, T, search, dep_stats, arr_stats, fl, gate):
    rep = path("reports_dir")
    L = ["# Metrics (Gate 2 / Checkpoint B-2)", "",
         f"Severe = **{SEV_DEF}**. Brier and RPS: lower is better. PR-AUC: higher is better; compare "
         "with the base rate (= PR-AUC of a random model). Precision/recall at RED use the STARTING "
         f"threshold P(>45) ≥ {config()['risk_rules']['red']['p_gt45_min']} (tuned in B3.2). "
         "Every rate has its count (n_flights / n_severe / n_arrivals).", "",
         "Models: **B0** climatology (airport × local hour × month, shrunk), **B1** logistic "
         "regression (same features), **LGBM** LightGBM 5-band model.", "",
         "## Training data (B2.1)", "",
         f"- Delay rows (flight × lead 3–12): {dep_stats['rows_per_split']} · flights: "
         f"{dep_stats['flights_per_split']} · purged at split edges (issue time in earlier split): "
         f"{dep_stats['purged_boundary']} · dropped, no weather in the 12 h before issue: "
         f"{dep_stats['dropped_no_recent_weather']}",
         f"- Capacity rows: {arr_stats['rows_per_split']} · flights: {arr_stats['flights_per_split']} "
         f"· purged {arr_stats['purged_boundary']} · dropped {arr_stats['dropped_no_recent_weather']}", "",
         "## Gate 2 summary", "", "```", json.dumps(gate, indent=2), "```", ""]
    for split, R in [("VALIDATION (Jan–Mar 2025)", V)] + ([("TEST (Apr–Jul 2025), single run", T)] if T else []):
        L += [f"## {split}", "", "### Delay risk, headline lead times", "",
              md(headline(R["dm"], ["brier_gt15", "brier_gt30", "brier_gt45", "brier_gt60", "rps"])), "",
              "### Severe (> 45) detection", "",
              md(headline(R["dm"], ["pr_auc_gt45", "roc_auc_gt45", "n_red_flag", "precision_at_red",
                                    "recall_at_red"])), "",
              "### Is LGBM's Brier(>45) gain over B0 real? Paired bootstrap over target hours", "",
              "diff = Brier(LGBM) − Brier(B0); negative = LGBM better. 90% interval.", "",
              md(R["boot"]), "",
              "### Capacity index RMSE (airport-hour level, weighted by arrivals)", "",
              md(R["cm"][R["cm"].lead.isin(HEADLINE)]), "",
              "<details><summary>All lead times 3–12, all models (delay)</summary>", "",
              md(R["dm"]), "", "</details>", "",
              "<details><summary>All lead times 3–12 (capacity)</summary>", "",
              md(R["cm"]), "", "</details>", ""]
    import lightgbm as lgb
    imp = []
    for name in ["delayband", "capacity"]:
        b = lgb.Booster(model_file=str(path("models_dir") / f"{name}.txt"))
        g = pd.Series(b.feature_importance("gain"), b.feature_name())
        imp.append((g / g.sum()).rename(name))
    imp = pd.concat(imp, axis=1).sort_values("delayband", ascending=False).round(3)
    L += ["## Feature importance (share of total gain)", "",
          "Read with care: month, time of day and traffic dominate. The weather signal in a ~1% sample "
          "with ~9–10 readings per day is weak, which is why the gain over climatology is small.", "",
          imp.reset_index(names="feature").to_markdown(index=False), ""]
    L += ["## Seasonal comparison (lead note B-b): is the hard test period the season?", "",
          md(seasonal_table(fl)), "",
          "## Hyper-parameter search (validation multi-logloss, ≤ 20 configs)", "",
          md(search), ""]
    (rep / "metrics.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    args = set(sys.argv[1:])
    if not stage_data():
        sys.exit("A P0 data check FAILED - see reports/validation_report.md")
    if "--data-only" in args:
        sys.exit(0)
    if not stage_model(run_test="--no-test" not in args):
        sys.exit("A P0 model check FAILED - see reports/metrics.md")
