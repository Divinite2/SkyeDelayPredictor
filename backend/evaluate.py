"""A3 Evaluation: metrics per lead time / airport, bootstrap check, capacity RMSE,
failure cases, seasonal comparison (08 B2.7, B2.9, B2.10, B2.12, note B-b)."""
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from backend.baselines import K_IDX, THRESH, band_index
from backend.common import config
from backend.features import HUBS

RED = config()["risk_rules"]["red"]
AMBER = config()["risk_rules"]["amber"]
SEV_DEF = "> 45 min late or cancelled"
HEADLINE = config()["report_lead_times"]


def rps(E: np.ndarray, band: pd.Series) -> np.ndarray:
    """Ranked probability score per row over 5 ordered bands (normalised to [0,1])."""
    bi = band_index(band)
    Y = np.column_stack([(bi >= i).astype(float) for i in range(1, 5)])
    return ((E - Y) ** 2).sum(axis=1) / 4


def delay_metrics(df: pd.DataFrame, preds: dict) -> pd.DataFrame:
    """df: rows with label, airport, lead. preds: model name -> (n,4) exceedance matrix."""
    out = []
    groups = [("ALL", df.index)] + [(ap, df.index[df["airport"] == ap]) for ap in HUBS]
    for L in sorted(df["lead"].unique()):
        for ap, idx in groups:
            sub = df.loc[idx]
            sub = sub[sub["lead"] == L]
            if sub.empty:
                continue
            pos = df.index.get_indexer(sub.index)
            bi = band_index(sub["label"])
            y45 = (bi >= K_IDX[45]).astype(int)
            for name, E in preds.items():
                e = E[pos]
                r = {"lead": L, "airport": ap, "model": name, "n_flights": len(sub),
                     "n_severe": int(y45.sum()), "base_rate_gt45": round(y45.mean(), 4)}
                for k, i in K_IDX.items():
                    r[f"brier_gt{k}"] = round(np.mean((e[:, i - 1] - (bi >= i)) ** 2), 5)
                r["rps"] = round(rps(e, sub["label"]).mean(), 5)
                p45 = e[:, K_IDX[45] - 1]
                both = 0 < y45.sum() < len(y45)
                r["pr_auc_gt45"] = round(average_precision_score(y45, p45), 4) if both else np.nan
                r["roc_auc_gt45"] = round(roc_auc_score(y45, p45), 4) if both else np.nan
                flag = p45 >= RED["p_gt45_min"]
                r["n_red_flag"] = int(flag.sum())
                r["precision_at_red"] = round(y45[flag].mean(), 4) if flag.any() else np.nan
                r["recall_at_red"] = round(flag[y45 == 1].mean(), 4) if y45.any() else np.nan
                out.append(r)
    return pd.DataFrame(out)


def bootstrap_brier_diff(df, E_model, E_base, lead, k=45, reps=1000, seed=42):
    """Paired bootstrap of Brier(model) - Brier(B0) at P(>k), resampling TARGET HOURS
    (flights in the same hour share weather, so they are not independent)."""
    m = (df["lead"] == lead).to_numpy()
    sub = df[m]
    y = (band_index(sub["label"]) >= K_IDX[k]).astype(float)
    d = (E_model[m, K_IDX[k] - 1] - y) ** 2 - (E_base[m, K_IDX[k] - 1] - y) ** 2
    cl = pd.factorize(sub["airport"].astype(str) + sub["T"].astype(str))[0]
    sums = np.bincount(cl, weights=d)
    cnts = np.bincount(cl)
    rng = np.random.default_rng(seed)
    G = len(sums)
    boots = []
    for _ in range(reps):
        s = rng.integers(0, G, G)
        boots.append(sums[s].sum() / cnts[s].sum())
    lo, hi = np.percentile(boots, [5, 95])
    return {"lead": lead, "diff": round(d.mean(), 5), "ci90_low": round(lo, 5),
            "ci90_high": round(hi, 5), "share_model_better": round(np.mean(np.array(boots) < 0), 3),
            "n_hours": G}


def capacity_hourly(df: pd.DataFrame, preds: dict) -> pd.DataFrame:
    """Aggregate arrival rows to airport-hour per lead: observed index, n arrivals, predictions."""
    d = df[["airport", "T", "lead", "label"]].copy()
    for name, p in preds.items():
        d[name] = p
    agg = {"label": ["mean", "size"], **{n: "mean" for n in preds}}
    h = d.groupby(["airport", "T", "lead"]).agg(agg)
    h.columns = ["observed", "n_arrivals"] + list(preds)
    return h.reset_index()


def capacity_metrics(h: pd.DataFrame, models: list) -> pd.DataFrame:
    out = []
    for L in sorted(h["lead"].unique()):
        for ap in ["ALL"] + HUBS:
            s = h[(h["lead"] == L) & ((h["airport"] == ap) if ap != "ALL" else True)]
            r = {"lead": L, "airport": ap, "n_hours": len(s), "n_arrivals": int(s["n_arrivals"].sum()),
                 "observed_mean": round(np.average(s["observed"], weights=s["n_arrivals"]), 4)}
            for m in models:
                r[f"rmse_{m}"] = round(np.sqrt(np.average((s[m] - s["observed"]) ** 2,
                                                          weights=s["n_arrivals"])), 4)
            out.append(r)
    return pd.DataFrame(out)


def capacity_range(h: pd.DataFrame, model: str) -> dict:
    """10th-90th percentile of validation errors (observed - predicted) per lead time."""
    res = {}
    for L, s in h.groupby("lead"):
        err = s["observed"] - s[model]
        res[int(L)] = {"low": round(float(np.percentile(err, 10)), 4),
                       "high": round(float(np.percentile(err, 90)), 4)}
    return res


def risk_level(p45, cap):
    red = (p45 >= RED["p_gt45_min"]) | (cap <= RED["capacity_index_max"])
    amber = (p45 >= AMBER["p_gt45_min"]) | (cap <= AMBER["capacity_index_max"])
    return np.where(red, "RED", np.where(amber, "AMBER", "GREEN"))


def seasonal_table(flights: pd.DataFrame) -> pd.DataFrame:
    """Note B-b: is the hard test period the season or a shift? Severe rate by year x season."""
    f = flights[flights["airport_dep"].isin(HUBS)].copy()
    loc = f["sched_dep_utc"].dt.tz_convert("UTC")
    f["year"], f["mon"] = loc.dt.year, loc.dt.month
    f["season"] = np.select([f["mon"].between(1, 3), f["mon"].between(4, 7)],
                            ["Jan-Mar", "Apr-Jul"], "Aug-Dec")
    rows = []
    for (ap, season, yr), s in f.groupby([f["airport_dep"], "season", "year"]):
        rows.append({"airport": ap, "season": season, "year": yr, "n": len(s),
                     "n_severe": int(s["severe"].sum()), "severe_rate": round(s["severe"].mean(), 4)})
    for (season, yr), s in f.groupby(["season", "year"]):
        rows.append({"airport": "ALL_HUBS", "season": season, "year": yr, "n": len(s),
                     "n_severe": int(s["severe"].sum()), "severe_rate": round(s["severe"].mean(), 4)})
    t = pd.DataFrame(rows)
    return t[t["season"] != "Aug-Dec"].sort_values(["airport", "season", "year"])


# --------------------------------------------------------------------------- failure cases
def hour_table(dep: pd.DataFrame, E: np.ndarray, cap_pred: np.ndarray, lead: int) -> pd.DataFrame:
    """One row per (airport, target hour) at a given lead: prediction vs what happened."""
    d = dep.copy()
    d["p45"], d["p15"], d["cap"] = E[:, 2], E[:, 0], cap_pred
    d = d[d["lead"] == lead]
    d["bi"] = band_index(d["label"])
    g = d.groupby(["airport", "T"])
    h = g.agg(n_flights=("flight_id", "size"), n_severe=("severe", "sum"),
              n_on_time=("bi", lambda b: int((b == 0).sum())), p45=("p45", "first"),
              p15=("p15", "first"), cap=("cap", "first"), issue=("issue_time_utc", "first"),
              obs_age_h=("obs_age_h", "first")).reset_index()
    h["severe_share"] = h["n_severe"] / h["n_flights"]
    h["risk"] = risk_level(h["p45"].to_numpy(), h["cap"].to_numpy())
    h["risk_delay_only"] = risk_level(h["p45"].to_numpy(), np.ones(len(h)))
    return h


def what_happened_weather(wx_ap: pd.DataFrame, t, T) -> pd.DataFrame:
    """Weather observed AFTER the forecast was issued (t, T+1h] — for explanation only."""
    m = (wx_ap["obs_time_utc"] > t) & (wx_ap["obs_time_utc"] <= T + pd.Timedelta(hours=1))
    return wx_ap.loc[m, ["obs_time_utc", "temp_c", "prcp_mm", "wspd_kmh", "coco", "coco_label"]]


def failure_cases_md(split: str, h: pd.DataFrame, dep: pd.DataFrame, flights, ctx, lead: int) -> str:
    """Pick one miss + one false alarm and render them with inputs, timestamps and reasons."""
    def fmt(ts):
        return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%MZ")

    def local(ap, ts):
        return pd.Timestamp(ts).tz_convert(config()["airports"][ap]["tz"]).strftime("%a %H:%M local")

    def block(title, row, kind):
        ap, T, t = row["airport"], row["T"], row["issue"]
        x = dep[(dep["airport"] == ap) & (dep["T"] == T) & (dep["lead"] == lead)].iloc[0]
        fl = flights[(flights["airport_dep"] == ap) & (flights["sched_dep_utc"].dt.floor("h") == T)]
        after = what_happened_weather(ctx.wx[ap], t, T)
        L = [f"### {title}: {ap}, target hour {fmt(T)} ({local(ap, T)}), forecast issued {fmt(t)} "
             f"({lead} h ahead)", "",
             f"**Prediction:** risk **{row['risk']}** · P(>45) = {row['p45']:.3f} · P(>15) = "
             f"{row['p15']:.3f} · capacity index {row['cap']:.2f}", "",
             f"**What happened (n = {row['n_flights']} sampled departures):** {int(row['n_severe'])} "
             f"severe ({SEV_DEF}), {int(row['n_on_time'])} on time (≤ 15 min). Delays: "
             + ", ".join(f"{r.carrier} → {r.airport_arr}: " + ("CANCELLED" if r.cancelled else
                                                              f"{r.dep_delay_min:+.0f} min")
                         for r in fl.itertuples()), "",
             "**Inputs the model saw (weather as of the issue time):**", "",
             f"- last observation {fmt(t - pd.Timedelta(hours=x['obs_age_h']))} "
             f"(age {x['obs_age_h']:.0f} h): temp {x['temp_c']:.1f} °C, wind {x['wspd_kmh']:.1f} km/h, "
             f"precip {x['prcp_mm']:.1f} mm, pressure {x['pres_hpa']:.1f} hPa, group "
             f"{next((g for g in ['convective','showers','rain','low_visibility','winter','calm'] if x['coco_'+g] == 1), 'unknown')}",
             f"- storm in last 6 h: {int(x['storm_last_6h'])} · hours since storm: "
             f"{x['hours_since_storm']:.0f} · max wind 6 h: {x['wspd_max_6h']:.1f} km/h · precip 6 h: {x['prcp_sum_6h']:.1f} mm",
             f"- evening flag {int(x['evening_flag'])} · relative traffic {x['rel_volume']:.2f} · "
             f"scheduled deps/arrs in hour (sample) {int(x['sched_deps_in_hour'])}/{int(x['sched_arrs_in_hour'])}",
             "", "**Weather observed after the forecast was issued (not available to the model):**", ""]
        L.append(after.assign(obs_time_utc=after["obs_time_utc"].map(fmt)).to_markdown(index=False)
                 if len(after) else "_no observations between issue time and target hour_")
        L += ["", "**Reason (analysis):** " + reason(kind, x, after, row, fl), "",
              "**What would fix it:** " + fix(kind, x, after), ""]
        return "\n".join(L)

    out = [f"## {split.capitalize()} set ({lead} h ahead)", "",
           f"Candidate hours: {len(h)} airport-hours. Risk from the STARTING config rules "
           f"(RED: P(>45) ≥ {RED['p_gt45_min']} or capacity ≤ {RED['capacity_index_max']}; AMBER: "
           f"P(>45) ≥ {AMBER['p_gt45_min']} or capacity ≤ {AMBER['capacity_index_max']}). Rule tuning is B3.2.",
           "", "Risk-level distribution: " + ", ".join(
               f"{k} {v}" for k, v in h["risk"].value_counts().items()), ""]
    miss = h[h["risk"] == "GREEN"].sort_values(["severe_share", "n_severe", "n_flights"],
                                               ascending=False)
    fa = h[(h["risk"] == "RED") & (h["n_on_time"] == h["n_flights"])].sort_values(
        ["p45", "n_flights"], ascending=False)
    if len(miss):
        out.append(block("Miss (GREEN predicted, severe delays happened)", miss.iloc[0], "miss"))
    else:
        out.append("_No GREEN hour with severe delays: no miss under these rules._\n")
    if len(fa):
        out.append(block("False alarm (RED predicted, all flights on time)", fa.iloc[0], "fa"))
    else:
        out.append("_No RED hour with all flights on time._\n")
    return "\n".join(out)


def reason(kind, x, after, row, fl):
    r = []
    conv_after = after["coco"].isin([23, 24, 25, 26, 27]).any() if len(after) else False
    rain_after = after["coco"].isin(list(range(7, 23))).any() if len(after) else False
    if kind == "miss":
        if conv_after:
            r.append("a thunderstorm was reported AFTER the forecast was issued; nothing in the "
                     "observations up to the issue time showed it coming")
        elif rain_after:
            r.append("precipitation developed after the forecast was issued")
        if x["obs_age_h"] >= 3:
            r.append(f"the latest reading was already {x['obs_age_h']:.0f} h old")
        if fl["cancelled"].any():
            r.append("cancellations count as severe; cancellations often have non-weather causes "
                     "(crew, aircraft, upstream disruption) the model cannot see")
        if not r:
            r.append("weather at and after the issue time was benign, so the delay most likely had a "
                     "non-weather cause (late inbound aircraft, carrier or NAS delay) that is outside "
                     "the model's inputs; with ~1 sampled flight per hour, one flight decides the hour")
    else:
        if x["storm_last_6h"] == 1 or x["coco_convective"] == 1:
            r.append("a storm was observed shortly before the issue time and the model expected it to "
                     "persist into the target hour")
        if row["cap"] <= RED["capacity_index_max"] and row["p45"] < RED["p_gt45_min"]:
            r.append(f"RED was triggered by the capacity condition (index {row['cap']:.2f} ≤ "
                     f"{RED['capacity_index_max']}), not by delay risk; the starting capacity "
                     "thresholds sit close to the base rate and need tuning (B3.2)")
        if not conv_after and len(after):
            r.append("the observations after the issue time show the weather had cleared")
        if not r:
            r.append("the risk factors (time of day, traffic) were high but the flights left on time")
    return "; ".join(r) + "."


def fix(kind, x, after):
    if kind == "miss":
        return ("forecast weather (TAF / convective outlooks) instead of only past observations; a "
                "full flight schedule (real hourly volume and inbound delays); more frequent "
                "observations (METAR every hour instead of ~9-10 per day).")
    return ("forecast weather (TAF) to tell when a storm will end; calibrated RED thresholds tuned on "
            "validation to a stated false-alarm rate (B3.2); a full sample of flights per hour.")
