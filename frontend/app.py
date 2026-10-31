"""Controller dashboard: single page. Run with:  streamlit run frontend/app.py
BACKEND=mock (default) | real
Displays only what predict() returns; formatting is the only computation here.
"""
from __future__ import annotations

import os
import sys
from datetime import date
from html import escape
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from frontend import render as R  # noqa: E402
from frontend.backend_adapter import backend_mode, load_predict  # noqa: E402
from frontend.demo_cases import load_presets  # noqa: E402

CFG = R.load_config()
DEMO_DATE = date.fromisoformat(os.getenv("DEMO_DATE", "2025-06-14"))   # default in test period
DEMO_HOUR = 12                  # local
LEVEL_COLOUR = {"RED": "#c62828", "AMBER": "#e0a100", "GREEN": "#2e7d32"}
LEVEL_ICON = {"RED": "●", "AMBER": "▲", "GREEN": "■"}   # shape differs too, not colour alone

st.set_page_config(page_title="Airport Capacity & Delay Risk", layout="wide")
st.markdown("""<style>
.block-container {padding-top:3.2rem; max-width:1100px;}
.utc-note {color:#8a8f98; font-size:0.8rem; margin-top:-0.4rem;}
.card {border:1px solid #d0d4da; border-radius:8px; overflow:hidden; margin-top:0.4rem;}
.card-head {display:flex; justify-content:space-between; align-items:center;
            padding:0.7rem 1rem; font-weight:600; font-size:1.05rem;}
.lvl {padding:0.2rem 0.8rem; border-radius:4px; color:#fff; font-weight:800; letter-spacing:0.05em;}
.sec {padding:0.6rem 1rem; border-top:1px solid #eceef1;}
.sec-title {font-size:0.75rem; font-weight:700; color:#5f6670; letter-spacing:0.08em; margin-bottom:0.3rem;}
.row {display:flex; align-items:center; gap:0.8rem; margin:0.15rem 0;}
.row .lab {width:5.5rem; font-variant-numeric:tabular-nums;}
.track {flex:0 0 55%; height:0.85rem; background:#eceef1; border-radius:3px;}
.fill {height:100%; background:#5b6573; border-radius:3px;}
.row .val {width:3rem; text-align:right; font-variant-numeric:tabular-nums;}
.row.severe {font-weight:800;}
.row.severe .fill {background:#262b33;}
.sevtag {font-size:0.75rem; font-weight:700; color:#262b33;}
.muted {color:#8a8f98; font-size:0.8rem;}
.kv b {margin-right:0.3rem;}
ul.why {margin:0; padding-left:1.1rem;} ul.why li {margin:0.1rem 0;}
table.sim {width:100%; border-collapse:collapse; font-style:italic; color:#7a808a; font-size:0.9rem;}
table.sim th {text-align:left; font-style:normal; font-size:0.75rem; color:#5f6670; padding:0.2rem 0.4rem;}
table.sim td {padding:0.2rem 0.4rem; border-top:1px solid #f0f1f3; font-variant-numeric:tabular-nums;}
.simtag {font-style:normal; font-size:0.7rem; font-weight:700; border:1px solid #9aa0a8;
         border-radius:3px; padding:0 0.3rem; color:#5f6670;}
.refused {border:1px solid #c4c8ce; background:#f4f5f7; border-radius:8px; padding:1rem 1.2rem;}
.refused h4 {margin:0 0 0.4rem 0; color:#3c424b;}
.errbox {border:2px solid #c62828; border-radius:8px; padding:1rem 1.2rem; background:#fff;}
.errbox b {color:#c62828;}
.banner {background:#fff4c2; border:1px solid #e0c34a; border-radius:6px; padding:0.5rem 0.9rem;
         margin-bottom:0.4rem; color:#5a4a00;}
</style>""", unsafe_allow_html=True)

st.markdown("#### Airport Capacity & Delay Risk · 3–12 h ahead")

# ---------------- Back end (loaded once; F3.3 / F3.4) ----------------
@st.cache_resource(show_spinner="Loading model…")
def get_predict(mode: str):
    return load_predict(mode)


MODE = backend_mode()
predict = get_predict(MODE)

# ---------------- Session defaults (widgets are driven by these keys) ----------------
airports = list(CFG["airports"].keys())
icao_map = {v["icao"]: k for k, v in CFG["airports"].items()}
for k, v in {"free_entry": False, "apt_sel": airports[0], "apt_txt": "ATL",
             "now_day": DEMO_DATE, "now_hour": DEMO_HOUR, "tgt_lead": 6,
             "t_day": DEMO_DATE, "t_hour": DEMO_HOUR + 6}.items():
    st.session_state.setdefault(k, v)


def _known(code: str) -> str | None:
    code = icao_map.get(code, code)
    return code if code in CFG["airports"] else None


# ---------------- Demo presets (F3.5) ----------------
PRESETS = load_presets()
if not PRESETS and MODE == "mock":   # until the back end delivers reports/demo_cases.md
    PRESETS = load_presets(R.ROOT / "tests" / "fixtures" / "demo_cases_sample.md")


def _apply_preset():
    label = st.session_state.get("preset")
    case = next((c for c in PRESETS if c["label"] == label), None)
    if not case:
        return
    now, tgt = R.parse_utc(case["now_utc"]), R.parse_utc(case["target_hour_utc"])
    tz_apt = _known(case["airport"]) or airports[0]
    now_loc, tgt_loc = R.utc_to_local(tz_apt, now), R.utc_to_local(tz_apt, tgt)
    lead = int((tgt - now).total_seconds() // 3600)
    lt = CFG["lead_time_hours"]
    ss = st.session_state
    ss["now_day"], ss["now_hour"] = now_loc.date(), now_loc.hour
    if _known(case["airport"]) and lt["min"] <= lead <= lt["max"]:
        ss["free_entry"], ss["apt_sel"], ss["tgt_lead"] = False, _known(case["airport"]), lead
    else:  # refusal demos need free entry
        ss["free_entry"], ss["apt_txt"] = True, case["airport"]
        ss["t_day"], ss["t_hour"] = tgt_loc.date(), tgt_loc.hour
    ss.pop("resp", None)


if PRESETS:
    st.selectbox("Demo cases", ["—"] + [c["label"] for c in PRESETS], key="preset",
                 on_change=_apply_preset, help="Filled from reports/demo_cases.md")

# ---------------- Input bar ----------------
free_entry = st.session_state["free_entry"]
c_apt, c_day, c_hr, c_tgt, c_btn = st.columns([1.3, 1.3, 0.9, 2.2, 0.8])

with c_apt:
    if free_entry:
        airport_in = st.text_input("Airport (IATA/ICAO)", key="apt_txt").strip().upper()
    else:
        airport_in = st.selectbox("Airport", airports, key="apt_sel",
                                  format_func=lambda a: f"{a} ({CFG['airports'][a]['icao']})")
# Time zone for the pickers: the chosen airport if known, otherwise the first configured.
tz_airport = _known(airport_in) or airports[0]

with c_day:
    now_day = st.date_input("Now · date (local)", key="now_day")
with c_hr:
    now_hour = st.selectbox("Now · hour", list(range(24)), key="now_hour",
                            format_func=lambda h: f"{h:02d}:00")
now_utc = R.local_to_utc(tz_airport, now_day, now_hour)

with c_tgt:
    if not free_entry:
        opts = dict(R.target_options(now_utc))          # lead_h -> target_utc
        if st.session_state["tgt_lead"] not in opts:
            st.session_state["tgt_lead"] = min(opts)
        lead_sel = st.selectbox(
            "Target hour (local)", list(opts), key="tgt_lead",
            format_func=lambda h: f"{R.fmt_local(tz_airport, opts[h], with_date=True)}  ·  +{h} h")
        target_utc = opts[lead_sel]
    else:
        t1, t2 = st.columns(2)
        with t1:
            t_day = st.date_input("Target · date", key="t_day")
        with t2:
            t_hour = st.selectbox("Target · hour", list(range(24)), key="t_hour",
                                  format_func=lambda h: f"{h:02d}:00")
        target_utc = R.local_to_utc(tz_airport, t_day, t_hour)

now_s, target_s = R.to_utc_str(now_utc), R.to_utc_str(target_utc)


def _start():
    st.session_state["busy"] = True
    st.session_state["pending"] = (airport_in, target_s, now_s)


with c_btn:
    st.write("")
    st.write("")
    st.button("Check", type="primary", use_container_width=True,
              on_click=_start, disabled=st.session_state.get("busy", False))

st.checkbox("Test mode: type any airport and any target hour (to demonstrate refusals)",
            key="free_entry")
tz_label = R.utc_to_local(tz_airport, now_utc).strftime("%Z")
st.markdown(f"<div class='utc-note'>Sent to model in UTC — now: {now_s} · target: {target_s} "
            f"· times above are {tz_airport} local ({tz_label}) · back end: {MODE}</div>",
            unsafe_allow_html=True)
st.divider()

# ---------------- Call (one click -> one predict; response shown untouched) ----------------
if st.session_state.get("pending"):
    with st.spinner("Calculating…"):
        st.session_state["resp"] = predict(*st.session_state.pop("pending"))
    st.session_state["busy"] = False
    st.rerun()


# ---------------- Cards ----------------
def ok_card(v: dict) -> str:
    lvl = v["risk_level"]
    col = LEVEL_COLOUR[lvl]
    rows = "".join(
        f"<div class='row{' severe' if r['severe'] else ''}'><span class='lab'>{r['label']}</span>"
        f"<div class='track'><div class='fill' style='width:{r['width']:.1f}%'></div></div>"
        f"<span class='val'>{r['text']}</span>"
        f"{'<span class=sevtag>◀ severe</span>' if r['severe'] else ''}</div>"
        for r in v["risk_rows"])
    cap = ""
    if v["capacity"]:
        c = v["capacity"]
        title = f" title='{escape(c['note'])}'" if c["note"] else ""
        aar = f" · {escape(c['aar'])}" if c["aar"] else ""
        cap = (f"<div class='sec'><div class='sec-title'>ARRIVAL CAPACITY</div>"
               f"<span{title}>{escape(c['text'])}{aar} <span class='muted'>ⓘ</span></span></div>")
    why = ""
    if v["drivers"]:
        items = "".join(
            f"<li>{escape(d['label'])}{': ' + escape(d['value']) if d['value'] else ''}"
            f"{' <span class=muted>(' + d['time'] + ')</span>' if d['time'] else ''}</li>"
            for d in v["drivers"])
        why = f"<div class='sec'><div class='sec-title'>WHY</div><ul class='why'>{items}</ul></div>"
    flights = ""
    if v["flights"]:
        th = "".join(f"<th>{t}</th>" for t in v["thresholds"])
        trs = "".join(
            f"<tr><td>{escape(f['id'])}</td><td>{escape(f['carrier'])}</td><td>{escape(f['route'])}</td>"
            f"<td>{f['dep']}</td><td><span class='simtag'>{f['tag']}</span></td>"
            + "".join(f"<td>{p}</td>" for p in f["probs"]) + "</tr>"
            for f in v["flights"])
        flights = (f"<div class='sec'><div class='sec-title'>EXAMPLE FLIGHTS IN THIS HOUR (SIMULATED)</div>"
                   f"<table class='sim'><tr><th>ID</th><th>Carrier</th><th>Route</th><th>Dep</th>"
                   f"<th>Source</th>{th}</tr>{trs}</table>"
                   f"<div class='muted' style='margin-top:0.3rem'>ⓘ {R.SIM_NOTE}</div></div>")
    return (
        f"<div class='card' style='border-left:6px solid {col}'>"
        f"<div class='card-head'><span>{escape(v['header'])}</span>"
        f"<span class='lvl' style='background:{col}'>{LEVEL_ICON[lvl]} {lvl}</span></div>"
        f"<div class='sec'><div class='sec-title'>DEPARTURE DELAY RISK</div>{rows}</div>"
        f"{cap}{why}"
        f"<div class='sec'><div class='sec-title'>DO · suggestion, controller decides</div>"
        f"{escape(v['do_text'])} <span class='muted'>({escape(v['rule'])})</span></div>"
        f"<div class='sec kv'><span class='sec-title'>CONFIDENCE&nbsp;</span>"
        f"<b>{v['confidence_level']}</b><span class='muted'>· {escape(v['confidence_reasons'])}</span></div>"
        f"{flights}</div>"
        f"<div class='muted' style='margin-top:0.4rem'>{escape(v['footer'])}</div>")


resp = st.session_state.get("resp")
if resp is None:
    st.caption("Choose an airport and hour, then press **Check**.")
else:
    v = R.view_model(resp)
    if v["kind"] == "ok":
        if v["banner"]:
            st.markdown(f"<div class='banner'>⚠ {escape(v['banner'])}</div>", unsafe_allow_html=True)
        st.markdown(ok_card(v), unsafe_allow_html=True)
    elif v["kind"] == "refused":
        st.markdown(f"<div class='refused'><h4>{escape(v['title'])}</h4>{escape(v['message'])}</div>",
                    unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='errbox'><b>{R.ERROR_HEADLINE}</b>"
                    f"<div class='muted' style='margin-top:0.4rem'>{escape(v['message'])}</div></div>",
                    unsafe_allow_html=True)
