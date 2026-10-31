"""Controller dashboard: single page. Run with:  streamlit run frontend/app.py
BACKEND=mock (default) | real
Displays only what predict() returns; formatting is the only computation here.
v1.2 UI refresh: Skye mascot, colour-tinted result card, headline tiles, collapsible details.
"""
from __future__ import annotations

import base64
import os
import time
import sys
from datetime import date
from html import escape
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from frontend import render as R  # noqa: E402
from frontend.backend_adapter import backend_mode, load_predict  # noqa: E402
from frontend.demo_cases import MOCK_SAMPLE_PATH, load_presets  # noqa: E402

CFG = R.load_config()
DEMO_DATE = date.fromisoformat(os.getenv("DEMO_DATE", "2025-06-14"))   # default in test period
DEMO_HOUR = 12                  # local
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "skye.svg"
LOGO_URI = "data:image/svg+xml;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode()

try:
    st.set_page_config(page_title="Skye · Airport Delay Risk", page_icon=str(LOGO_PATH), layout="wide")
except Exception:  # older Streamlit without SVG page icons
    st.set_page_config(page_title="Skye · Airport Delay Risk", page_icon="✈️", layout="wide")

st.markdown("""<style>
.block-container {padding-top:2.2rem; max-width:1080px;}
/* header */
.hdr {display:flex; align-items:center; gap:0.9rem; margin-bottom:0.6rem;}
.hdr img {width:58px; height:58px;}
.hdr h1 {font-size:1.45rem; margin:0; padding:0; line-height:1.2;}
.hdr .sub {color:#5f6670; font-size:0.9rem;}
.pill {display:inline-block; padding:0.08rem 0.55rem; border-radius:999px; font-size:0.72rem;
       font-weight:700; letter-spacing:0.04em; vertical-align:middle;}
.pill.real {background:#e9f5ea; color:#2e7d32;} .pill.mock {background:#fff6db; color:#8a6100;}
.step {font-size:0.72rem; font-weight:700; color:#1f5fa8; letter-spacing:0.08em; margin:0.2rem 0 -0.2rem;}
.utc-note {color:#8a8f98; font-size:0.76rem; margin-top:-0.3rem;}
.muted {color:#8a8f98; font-size:0.8rem;}
/* result card */
.card {border:1px solid #e1e4e8; border-radius:14px; overflow:hidden; background:#fff;
       box-shadow:0 1px 3px rgba(0,0,0,0.05);}
.hero {display:flex; justify-content:space-between; align-items:center; gap:1rem; padding:1rem 1.2rem;}
.badge {display:inline-block; padding:0.3rem 0.9rem; border-radius:8px; color:#fff;
        font-weight:800; letter-spacing:0.06em; font-size:1.05rem;}
.headline {font-size:1.25rem; font-weight:700; margin-top:0.35rem;}
.where {color:#3c424b; font-size:0.92rem; margin-top:0.15rem;}
.conf {text-align:right; min-width:12rem;}
.conf .cp {display:inline-block; padding:0.2rem 0.7rem; border-radius:999px; font-weight:700; font-size:0.85rem;}
.conf .why {font-size:0.75rem; color:#5f6670; margin-top:0.25rem;}
.tiles {display:grid; grid-template-columns:repeat(4, 1fr); gap:0.7rem; padding:0.9rem 1.2rem;}
.tile {border:1px solid #eceef1; border-radius:10px; padding:0.6rem 0.8rem; background:#fafbfc;}
.tile .k {font-size:0.7rem; font-weight:700; color:#5f6670; letter-spacing:0.07em; text-transform:uppercase;}
.tile .v {font-size:1.35rem; font-weight:800; margin-top:0.15rem; font-variant-numeric:tabular-nums;}
.tile .s {font-size:0.75rem; color:#8a8f98;}
.cols {display:grid; grid-template-columns:1fr 1fr; gap:0; border-top:1px solid #eceef1;}
.cols > div {padding:0.8rem 1.2rem;} .cols > div + div {border-left:1px solid #eceef1;}
.sec-title {font-size:0.72rem; font-weight:700; color:#5f6670; letter-spacing:0.08em; margin-bottom:0.45rem;}
.row {display:flex; align-items:center; gap:0.6rem; margin:0.3rem 0;}
.row .lab {width:4.6rem; font-variant-numeric:tabular-nums; font-size:0.9rem;}
.track {flex:1; height:0.8rem; background:#eceef1; border-radius:99px; overflow:hidden;}
.fill {height:100%; background:#9aa3ae; border-radius:99px;}
.row .val {width:2.8rem; text-align:right; font-variant-numeric:tabular-nums;}
.row.severe {font-weight:800;}
.sevtag {font-size:0.68rem; font-weight:700; padding:0 0.35rem; border-radius:4px; color:#fff;}
ul.why {list-style:none; margin:0; padding:0;} ul.why li {margin:0.35rem 0; display:flex; gap:0.5rem;}
.arr {font-size:0.8rem; width:1rem; text-align:center; padding-top:0.1rem;}
.arr.increases {color:#c62828;} .arr.decreases {color:#2e7d32;}
.do {margin:0 1.2rem 0.9rem; padding:0.7rem 0.9rem; border-radius:10px; background:#eaf2fb;
     border-left:4px solid #1f5fa8;}
.do .sec-title {color:#1f5fa8; margin-bottom:0.2rem;}
details.more {padding:0.55rem 1.2rem 0.8rem; border-top:1px solid #eceef1; font-size:0.83rem; color:#5f6670;}
details.more summary {cursor:pointer; font-weight:600; color:#3c424b;}
details.more div {margin-top:0.3rem;}
.foot {margin-top:0.45rem;}
.scale {padding:0.1rem 1.2rem 0.9rem;}
.scale .bar {position:relative; display:flex; height:0.7rem; border-radius:99px; overflow:visible; margin:1.5rem 0 1.3rem;}
.scale .z {height:100%;} .scale .z.g {background:#a5d6a7; border-radius:99px 0 0 99px;}
.scale .z.a {background:#ffe08a;} .scale .z.r {background:#ef9a9a; border-radius:0 99px 99px 0;}
.scale .mk {position:absolute; top:-1.45rem; font-size:0.75rem; font-weight:800;
            white-space:nowrap; text-align:center; line-height:1;}
.scale .ln {position:absolute; top:-0.3rem; height:1.25rem; width:3px; margin-left:-1.5px; border-radius:2px;}
.scale .ty {position:absolute; top:1.05rem; transform:translateX(-50%); font-size:0.68rem; color:#5f6670; white-space:nowrap;}
.scale .ty::before {content:''; display:block; width:1px; height:0.35rem; background:#5f6670; margin:-0.25rem auto 0.05rem;}
.scale .cut {position:absolute; top:0; bottom:0; width:2px; background:#fff;}
.scale .just {font-size:0.88rem; color:#262b33;} .scale .just b {font-weight:700;}
/* other states */
.empty {display:flex; align-items:center; gap:1rem; padding:1.2rem; border:1px dashed #c9d6e6;
        border-radius:14px; background:#f6f9fd; color:#3c424b;}
.empty img {width:52px; opacity:0.9;}
.refused {border:1px solid #c4c8ce; background:#f4f5f7; border-radius:14px; padding:1rem 1.2rem;}
.refused h4 {margin:0 0 0.4rem 0; color:#3c424b;}
.errbox {border:2px solid #c62828; border-radius:14px; padding:1rem 1.2rem; background:#fff;}
.errbox b {color:#c62828;}
.banner {background:#fff4c2; border:1px solid #e0c34a; border-radius:10px; padding:0.5rem 0.9rem;
         margin-bottom:0.5rem; color:#5a4a00;}
@media (max-width: 800px) {.tiles {grid-template-columns:1fr 1fr;} .cols {grid-template-columns:1fr;}
  .cols > div + div {border-left:none; border-top:1px solid #eceef1;} .hero {flex-direction:column; align-items:flex-start;}
  .conf {text-align:left;}}
</style>""", unsafe_allow_html=True)


# ---------------- Back end (loaded once; F3.3 / F3.4) ----------------
@st.cache_resource(show_spinner="Loading model…")
def get_predict(mode: str):
    return load_predict(mode)


MODE = backend_mode()
predict = get_predict(MODE)

st.markdown(
    f"<div class='hdr'><img src='{LOGO_URI}' alt='Skye mascot'/><div>"
    f"<h1>Skye · Airport Delay &amp; Capacity Risk</h1>"
    f"<div class='sub'>Hourly departure-delay risk, 3–12 h ahead. A decision aid: the controller decides. "
    f"<span class='pill {MODE}'>BACK END: {MODE.upper()}</span></div></div></div>",
    unsafe_allow_html=True)

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
if not PRESETS and MODE == "mock":   # labelled sample fixture, mock mode only (F3b.2)
    PRESETS = load_presets(MOCK_SAMPLE_PATH)


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


# ---------------- Input panel ----------------
with st.container(border=True):
    if PRESETS:
        st.selectbox("Demo cases (optional, fills the fields below)",
                     ["—"] + [c["label"] for c in PRESETS], key="preset",
                     on_change=_apply_preset, help="Filled from reports/demo_cases.json")
    else:  # F3b.2: picker hidden, manual inputs still work
        st.markdown("<div class='muted'>Demo cases not available</div>", unsafe_allow_html=True)

    free_entry = st.session_state["free_entry"]
    st.markdown("<div class='step'>① AIRPORT &nbsp;·&nbsp; ② NOW &nbsp;·&nbsp; ③ HOUR TO FORECAST</div>",
                unsafe_allow_html=True)
    c_apt, c_day, c_hr, c_tgt, c_btn = st.columns([1.3, 1.3, 0.9, 2.2, 0.9])

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
                format_func=lambda h: f"+{h} h  ·  {R.fmt_local(tz_airport, opts[h], with_date=True)}")
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
        st.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
        st.button("Check", type="primary", use_container_width=True,
                  on_click=_start, disabled=st.session_state.get("busy", False))

    tz_label = R.utc_to_local(tz_airport, now_utc).strftime("%Z")
    st.checkbox("Test mode: type any airport and any target hour (to demonstrate refusals)",
                key="free_entry")
    st.markdown(f"<div class='utc-note'>Times are {tz_airport} local ({tz_label}). "
                f"Sent to model in UTC: now {now_s} · target {target_s}</div>", unsafe_allow_html=True)

# ---------------- Call (one click -> one predict; response shown untouched) ----------------
if st.session_state.get("pending"):
    with st.spinner("Skye is checking the skies…"):
        _t0 = time.perf_counter()
        st.session_state["resp"] = predict(*st.session_state.pop("pending"))
        st.session_state["elapsed_s"] = time.perf_counter() - _t0  # C4b (v1.1): shown in footer
    st.session_state["busy"] = False
    st.rerun()


# ---------------- Result card ----------------
def _tile(key: str, value: str, sub: str = "", colour: str | None = None) -> str:
    style = f" style='color:{colour}'" if colour else ""
    return (f"<div class='tile'><div class='k'>{key}</div><div class='v'{style}>{value}</div>"
            f"<div class='s'>{sub}</div></div>")


def ok_card(v: dict) -> str:
    lvl, ls, cs = v["risk_level"], v["level_style"], v["confidence_style"]
    col = ls["colour"]

    hero = (f"<div class='hero' style='background:{ls['tint']}; border-left:8px solid {col}'><div>"
            f"<span class='badge' style='background:{col}'>{ls['icon']} {lvl}</span>"
            f"<div class='headline' style='color:{col}'>{ls['headline']}</div>"
            f"<div class='where'><b>{escape(v['airport'])}</b> · {escape(v['when'])} · "
            f"{escape(v['lead_text'])}</div></div>"
            f"<div class='conf'><div class='sec-title' style='margin:0 0 0.2rem'>CONFIDENCE</div>"
            f"<span class='cp' style='background:{cs['tint']}; color:{cs['colour']}'>"
            f"{v['confidence_level']}</span>"
            f"<div class='why'>{escape(v['confidence_reasons'])}</div></div></div>")

    e = v.get("delay_estimate")
    c = v.get("capacity")
    tiles = _tile(f"Severe delay ({v['severe_label']})", v["severe_text"], "chance this hour", col)
    if e:
        tiles += _tile("Middle estimate", escape(e["typical"]), "typical departure")
        tiles += _tile(escape(e["bad_label"]), escape(e["bad"]), f"{e['bad_prob']} chance")
    if c:
        tiles += _tile("Arrival capacity", escape(c["text"].split(" ")[0]),
                       "of scheduled arrivals on time")

    sc = v.get("risk_scale")
    scale = ""
    if sc:
        scale = (f"<div class='scale'><div class='sec-title'>WHY THIS COLOUR · severe-delay risk vs other hours</div>"
                 f"<div class='bar'>"
                 f"<div class='z g' style='width:{sc['amber']}%'></div>"
                 f"<div class='z a' style='width:{sc['red'] - sc['amber']}%'></div>"
                 f"<div class='z r' style='width:{100 - sc['red']}%'></div>"
                 f"<span class='cut' style='left:{sc['amber']}%'></span><span class='cut' style='left:{sc['red']}%'></span>"
                 f"<span class='ty' style='left:{sc['typical']}%'>typical {sc['typical_text']}</span>"
                 f"<span class='mk' style='left:{sc['marker']}%; color:{col}; transform:translateX({sc['label_shift']}%)'>"
                 f"this hour {sc['marker_text']}{' ▸' if sc['beyond'] else ''}</span>"
                 f"<span class='ln' style='left:{sc['marker']}%; background:{col}'></span>"
                 f"</div>"
                 f"<div class='just'><b>{escape(sc['justification'])}</b>. "
                 f"<span class='muted'>{escape(sc['why_colour'])} Scale: {escape(sc['basis'])}; "
                 f"0–{sc['top_text']}.</span></div></div>")

    rows = "".join(
        f"<div class='row{' severe' if r['severe'] else ''}'><span class='lab'>{r['label']}</span>"
        f"<div class='track'><div class='fill' style='width:{r['width']:.1f}%"
        f"{'; background:' + col if r['severe'] else ''}'></div></div>"
        f"<span class='val'>{r['text']}</span>"
        f"{f'<span class=sevtag style=background:{col}>severe</span>' if r['severe'] else ''}</div>"
        for r in v["risk_rows"])
    risk = f"<div><div class='sec-title'>DEPARTURE DELAY RISK</div>{rows}</div>"

    if v["drivers"]:
        items = "".join(
            f"<li><span class='arr {d['effect'] or ''}'>{d['arrow']}</span><span>{escape(d['label'])}"
            f"{': ' + escape(d['value']) if d['value'] else ''}"
            f"{' <span class=muted>(' + d['time'] + ')</span>' if d['time'] else ''}</span></li>"
            for d in v["drivers"])
        why = (f"<div><div class='sec-title'>WHY · top factors "
               f"<span class='muted'>(▲ raises risk, ▼ lowers it)</span></div><ul class='why'>{items}</ul></div>")
    else:
        why = "<div><div class='sec-title'>WHY</div><span class='muted'>No major factors reported.</span></div>"

    do = (f"<div class='do'><div class='sec-title'>SUGGESTED ACTION · controller decides</div>"
          f"{escape(v['do_text'])}</div>")

    details = [f"Decision rule: {escape(v['rule'])}"]
    if c:
        details.append(f"Capacity: {escape(c['text'])}{' · ' + escape(c['aar']) if c['aar'] else ''}")
        if c["visible_note"] or c["note"]:
            details.append(escape(c["visible_note"] or c["note"]))
    if e and e.get("method"):
        details.append(f"Likely delay: {escape(e['method'])}")
    details.append(f"Request (UTC): {escape(v['request_utc'])}")
    details.append(escape(v["footer"]))
    more = ("<details class='more'><summary>Details &amp; method</summary>"
            + "".join(f"<div>{d}</div>" for d in details) + "</details>")

    cap_note = (f"<div class='muted' style='padding:0 1.2rem 0.6rem'>ⓘ {escape(c['visible_note'])}</div>"
                if c and c["visible_note"] else "")
    elapsed = st.session_state.get("elapsed_s")
    foot = (f"<div class='muted foot'>Back end: {MODE}"
            + (f" · answered in {elapsed:.2f} s" if elapsed is not None else "")
            + (" (demo data, not a forecast)" if MODE == "mock" else "") + "</div>")
    return (f"<div class='card'>{hero}<div class='tiles'>{tiles}</div>{cap_note}{scale}"
            f"<div class='cols'>{risk}{why}</div>{do}{more}</div>{foot}")


resp = st.session_state.get("resp")
if resp is None:
    st.markdown(f"<div class='empty'><img src='{LOGO_URI}' alt=''/><div><b>Ready when you are.</b><br>"
                f"Pick an airport, the current time and an hour 3–12 h ahead, then press <b>Check</b>. "
                f"Or start with a demo case.</div></div>", unsafe_allow_html=True)
else:
    v = R.view_model(resp)
    if v["kind"] == "ok":
        if v["banner"]:
            st.markdown(f"<div class='banner'>⚠ {escape(v['banner'])}</div>", unsafe_allow_html=True)
        st.markdown(ok_card(v), unsafe_allow_html=True)
    elif v["kind"] == "refused":
        st.markdown(f"<div class='refused'><h4>⏸ {escape(v['title'])}</h4>{escape(v['message'])}</div>",
                    unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='errbox'><b>{R.ERROR_HEADLINE}</b>"
                    f"<div class='muted' style='margin-top:0.4rem'>{escape(v['message'])}</div></div>",
                    unsafe_allow_html=True)
