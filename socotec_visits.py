"""
SOCOTEC Arabia — Zone & Engineer Management
Replaces AppSheet IDI Zone Assistant + Engineer Coverage tracker.

Pages:
  1. Zone Directory   — search any area → see assigned engineers
  2. Area Manager     — add / edit / delete area-engineer assignments
  3. Coverage Manager — temporary substitutions (vacation / leave)
"""

import streamlit as st
import pandas as pd
import sqlite3
import os
import base64
from datetime import date, datetime, timedelta
from pathlib import Path

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
APP_DIR     = os.path.dirname(os.path.abspath(__file__))
# DB_PATH: writable on both local and Streamlit Community Cloud
DB_PATH     = os.environ.get("DB_PATH", os.path.join(APP_DIR, "socotec_zones.db"))
LOGO_PATH   = os.path.join(APP_DIR, "socotec_logo.jpg")
ZONE_RIYADH = os.path.join(APP_DIR, "Riyadh_Zone_Eng_Log.xlsx")
ZONE_IDI    = os.path.join(APP_DIR, "IDI_Zone_Eng_Log.xlsx")

# Streamlit Community Cloud: files are served from the GitHub repo root
# If zone files not found at APP_DIR, try repo root
import sys
_repo_root = os.path.dirname(APP_DIR) if not os.path.exists(ZONE_RIYADH) else APP_DIR
if not os.path.exists(ZONE_RIYADH):
    ZONE_RIYADH = os.path.join(_repo_root, "Riyadh_Zone_Eng_Log.xlsx")
if not os.path.exists(ZONE_IDI):
    ZONE_IDI = os.path.join(_repo_root, "IDI_Zone_Eng_Log.xlsx")

# ─────────────────────────────────────────────
#  BRAND STYLING
# ─────────────────────────────────────────────
BRAND_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&display=swap');

html, body, [class*="css"], .stMarkdown, .stText {
    font-family: 'DM Sans', sans-serif !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0b1f3a !important;
    border-right: 1px solid #162f4f;
}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] span {
    color: #c8d8ea !important;
}
section[data-testid="stSidebar"] .stRadio label {
    font-size: 14px;
    padding: 7px 10px;
    border-radius: 7px;
    display: block;
    transition: background 0.15s;
    cursor: pointer;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(0,120,212,0.18) !important;
    color: #ffffff !important;
}
section[data-testid="stSidebar"] input {
    background: #0f2540 !important;
    border: 1px solid #1d3a5e !important;
    color: #e0eaf5 !important;
    border-radius: 7px !important;
    font-size: 13px !important;
}
section[data-testid="stSidebar"] select {
    background: #0f2540 !important;
    border: 1px solid #1d3a5e !important;
    color: #e0eaf5 !important;
}
section[data-testid="stSidebar"] hr {
    border-color: #162f4f !important;
    margin: 14px 0;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stTextInput label {
    font-size: 10.5px !important;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: #4a7aaa !important;
    font-weight: 600;
}
section[data-testid="stSidebar"] button {
    background: #0f3460 !important;
    color: #7eb8f7 !important;
    border: 1px solid #1d4a7a !important;
    border-radius: 6px !important;
    font-size: 13px !important;
}
section[data-testid="stSidebar"] button:hover {
    background: #174a82 !important;
    color: #ffffff !important;
}

/* Main content — force light background on all Streamlit containers */
.main .block-container { padding-top: 28px; max-width: 1120px; }
.stApp, [data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
[data-testid="block-container"] {
    background: #f7f9fc !important;
}
/* Override any dark mode remnants */
[data-testid="stMarkdownContainer"] { color: #0b1f3a; }

/* Page header */
.soco-header {
    margin-bottom: 28px;
    padding-bottom: 18px;
    border-bottom: 2px solid #dde6f2;
    background: #ffffff;
    padding: 20px 24px;
    border-radius: 12px;
    border: 1px solid #dde6f2;
    box-shadow: 0 1px 4px rgba(0,40,100,0.06);
    margin-bottom: 24px;
}
.soco-header h2 {
    font-size: 24px;
    font-weight: 600;
    color: #0b1f3a;
    margin: 0 0 3px 0;
    letter-spacing: -0.025em;
}
.soco-header .sub {
    font-size: 13px;
    color: #7a92aa;
    font-weight: 400;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: #ffffff !important;
    border: 1px solid #d5e3f0 !important;
    box-shadow: 0 2px 6px rgba(0,40,100,0.08) !important;
    border-radius: 12px;
    padding: 16px 20px 14px;
}
[data-testid="metric-container"] label {
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #5a7899 !important;
    font-weight: 600;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 30px !important;
    font-weight: 600 !important;
    color: #0b1f3a !important;
    letter-spacing: -0.02em;
}

/* Primary button */
.stButton > button[kind="primary"],
button[data-testid="baseButton-primary"] {
    background: #0078d4 !important;
    color: white !important;
    border: none !important;
    border-radius: 7px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    font-size: 13.5px !important;
    padding: 9px 20px !important;
    transition: background 0.15s !important;
}
.stButton > button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover {
    background: #006bbf !important;
}
/* Secondary */
.stButton > button[kind="secondary"],
button[data-testid="baseButton-secondary"] {
    background: transparent !important;
    color: #0078d4 !important;
    border: 1.5px solid #b3d1f0 !important;
    border-radius: 7px !important;
    font-size: 13px !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #eef5fc !important;
    border-color: #0078d4 !important;
}

/* Expander — zone cards */
details[data-testid="stExpander"] {
    border: 1px solid #dde6f2 !important;
    border-radius: 10px !important;
    margin-bottom: 7px;
    background: #ffffff;
    box-shadow: 0 1px 3px rgba(0,40,100,0.05);
    transition: box-shadow 0.15s;
}
details[data-testid="stExpander"]:hover {
    box-shadow: 0 2px 8px rgba(0,60,120,0.07);
}
details[data-testid="stExpander"][open] {
    border-color: #0078d4 !important;
    box-shadow: 0 0 0 2.5px rgba(0,120,212,0.1);
}
details[data-testid="stExpander"] summary {
    font-size: 14px;
    font-weight: 500;
    padding: 11px 16px;
    color: #0b1f3a;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    border-bottom: 2px solid #e0e8f0;
    gap: 0;
    margin-bottom: 8px;
}
.stTabs [data-baseweb="tab"] {
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.02em;
    color: #4a6a8a !important;
    padding: 10px 22px;
    border-bottom: 2.5px solid transparent;
    margin-bottom: -2px;
    background: transparent;
}
.stTabs [aria-selected="true"] {
    color: #0078d4 !important;
    border-bottom-color: #0078d4 !important;
}

/* Fields */
.fl { font-size:10.5px; text-transform:uppercase; letter-spacing:0.09em;
      color:#8097b1; font-weight:600; margin-bottom:2px; }
.fv { font-size:15px; color:#0b1f3a !important; font-weight:500; margin-bottom:14px;
      line-height:1.4; }
.fv.muted { color:#7a92aa; font-style:italic; font-weight:400; }
.fl { color:#5a7899 !important; }

/* Badges */
.badge { display:inline-block; padding:3px 11px; border-radius:20px;
         font-size:11.5px; font-weight:600; letter-spacing:0.03em;
         margin-bottom:12px; }
.b-blue   { background:#e5f0fb; color:#0057a8; }
.b-teal   { background:#e2f5f4; color:#0b6e6e; }
.b-green  { background:#e6f4ea; color:#1e6b30; }
.b-orange { background:#fef3e7; color:#c45a00; }
.b-gray   { background:#f0f2f5; color:#4a5a70; }
.b-red    { background:#fdeaea; color:#b91c1c; }

/* Active coverage */
.cov-banner {
    background: #fffbeb;
    border: 1px solid #f0b429;
    border-left: 4px solid #f0b429;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 13.5px;
    color: #5c3d00;
    margin-bottom: 18px;
    line-height: 1.6;
}

/* Section heading */
.sec-title {
    font-size: 13px; font-weight: 600; color: #0b1f3a;
    text-transform: uppercase; letter-spacing: 0.07em;
    margin: 20px 0 10px;
    padding-bottom: 6px;
    border-bottom: 2px solid #d5e3f0;
}

/* Input */
.stTextInput input, .stTextArea textarea {
    border-radius: 7px !important;
    border-color: #c8d8eb !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #0078d4 !important;
    box-shadow: 0 0 0 2.5px rgba(0,120,212,0.12) !important;
}

/* Dataframe */
.stDataFrame { border-radius:10px; overflow:hidden; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility:hidden; }
.viewerBadge_container__1QSob { display:none; }
</style>
"""

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="SOCOTEC Arabia — Zone Manager",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(BRAND_CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────────
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS custom_areas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            area        TEXT NOT NULL,
            city        TEXT,
            province    TEXT,
            inspector   TEXT NOT NULL,
            team_leader TEXT,
            rd6_eng     TEXT,
            rd7_eng     TEXT,
            added_by    TEXT,
            added_date  TEXT,
            notes       TEXT,
            source      TEXT DEFAULT 'custom'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS engineer_coverage (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            original_eng TEXT NOT NULL,
            substitute   TEXT NOT NULL,
            area_filter  TEXT,
            start_date   TEXT NOT NULL,
            end_date     TEXT NOT NULL,
            reason       TEXT,
            created_by   TEXT,
            created_at   TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def today_str():
    return date.today().isoformat()

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def load_custom_areas():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM custom_areas ORDER BY city, area", conn)
    conn.close()
    return df

def save_custom_area(area, city, province, inspector, team_leader,
                     rd6, rd7, added_by, notes, row_id=None):
    conn = get_conn()
    if row_id:
        conn.execute(
            "UPDATE custom_areas SET area=?,city=?,province=?,inspector=?,"
            "team_leader=?,rd6_eng=?,rd7_eng=?,notes=? WHERE id=?",
            (area,city,province,inspector,team_leader,rd6,rd7,notes,row_id)
        )
    else:
        conn.execute(
            "INSERT INTO custom_areas (area,city,province,inspector,team_leader,"
            "rd6_eng,rd7_eng,added_by,added_date,notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (area,city,province,inspector,team_leader,rd6,rd7,
             added_by,today_str(),notes)
        )
    conn.commit()
    conn.close()

def delete_custom_area(row_id):
    conn = get_conn()
    conn.execute("DELETE FROM custom_areas WHERE id=?", (row_id,))
    conn.commit()
    conn.close()

def load_all_coverage():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM engineer_coverage ORDER BY start_date DESC", conn)
    conn.close()
    return df

def load_active_coverage():
    conn = get_conn()
    df = pd.read_sql(
        "SELECT * FROM engineer_coverage WHERE start_date<=? AND end_date>=?",
        conn, params=[today_str(), today_str()]
    )
    conn.close()
    return df

def save_coverage(orig, sub, area_f, sd, ed, reason, by):
    conn = get_conn()
    conn.execute(
        "INSERT INTO engineer_coverage (original_eng,substitute,area_filter,"
        "start_date,end_date,reason,created_by,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (orig, sub, area_f or None, str(sd), str(ed), reason, by, now_str())
    )
    conn.commit()
    conn.close()

def delete_coverage(row_id):
    conn = get_conn()
    conn.execute("DELETE FROM engineer_coverage WHERE id=?", (row_id,))
    conn.commit()
    conn.close()

@st.cache_data(ttl=300)
def load_zone_data():
    dfs = []
    if Path(ZONE_RIYADH).exists():
        try:
            df = pd.read_excel(ZONE_RIYADH, sheet_name=0, dtype=str)
            area_col = "Area" if "Area" in df.columns else df.columns[0]
            df = df.dropna(subset=[area_col]).rename(columns={
                area_col:"area","Inspector":"inspector","Email":"email",
                "UserID":"user_id","Team Leader":"team_leader",
                "RD6 Engineer":"rd6_eng","RD7 Engineer":"rd7_eng"
            })
            df["city"]="Riyadh - ALL"; df["province"]="Riyadh Province"
            df["source"]="riyadh"
            dfs.append(df)
        except: pass

    if Path(ZONE_IDI).exists():
        try:
            df = pd.read_excel(ZONE_IDI, sheet_name=0, dtype=str)
            col0 = df.columns[0]
            df = df.dropna(subset=[col0]).rename(columns={
                col0:"area","City":"city","Provincy":"province",
                "Inspector Engineer":"inspector","Team Leader":"team_leader",
                "RD6 Engineer":"rd6_eng","RD7 Engineer":"rd7_eng"
            })
            df["source"]="idi"
            dfs.append(df)
        except: pass

    custom = load_custom_areas()
    if not custom.empty:
        custom["source"]="custom"
        dfs.append(custom)

    if not dfs:
        return pd.DataFrame()

    out = pd.concat(dfs, ignore_index=True)
    for col in ["area","city","province","inspector","team_leader",
                "rd6_eng","rd7_eng","email","user_id","source"]:
        if col not in out.columns:
            out[col] = ""
        out[col] = out[col].fillna("").astype(str).str.strip()
    return out

def all_engineer_names(zone_df):
    names = set()
    for col in ["inspector","team_leader","rd6_eng","rd7_eng"]:
        if col in zone_df.columns:
            names.update(zone_df[col].dropna().str.strip().tolist())
    return sorted(n for n in names if n and n != "nan")

# ─────────────────────────────────────────────
#  UI HELPERS
# ─────────────────────────────────────────────
def logo_img(height=34):
    if Path(LOGO_PATH).exists():
        with open(LOGO_PATH,"rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return (f'<img src="data:image/jpeg;base64,{b64}" '
                f'height="{height}" style="object-fit:contain;">')
    return '<b style="color:#0078d4;font-size:18px;">SOCOTEC</b>'

def page_header(title, sub=""):
    s = f'<div class="sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="soco-header"><h2>{title}</h2>{s}</div>',
        unsafe_allow_html=True
    )

def fld(label, value, badge=None):
    val = str(value) if value and str(value) not in ("nan","0","") else ""
    st.markdown(f'<div class="fl">{label}</div>', unsafe_allow_html=True)
    if badge and val:
        st.markdown(f'<span class="badge {badge}">{val}</span>', unsafe_allow_html=True)
    elif val:
        st.markdown(f'<div class="fv">{val}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="fv muted">—</div>', unsafe_allow_html=True)

def sec(text):
    st.markdown(f'<div class="sec-title">{text}</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"""<div style="padding:14px 0 12px;border-bottom:1px solid #162f4f;
                        margin-bottom:16px;">
              {logo_img(30)}
              <div style="font-size:9.5px;letter-spacing:0.14em;text-transform:uppercase;
                          color:#3a6488;margin-top:5px;font-weight:600;">
                IDI Zone Manager &nbsp;·&nbsp; SOCOTEC Arabia
              </div>
            </div>""",
        unsafe_allow_html=True
    )

    user_name = st.text_input("Name", placeholder="Your full name")
    if not user_name:
        st.warning("Enter your name to continue")
        st.stop()

    user_role = st.selectbox(
        "Access level",
        ["Coordinator", "Team Leader"],
        help="Team Leaders can manage coverage rules"
    )

    st.markdown("<hr>", unsafe_allow_html=True)

    # City filter — populated from zone data after load
    city_filter = st.text_input(
        "Filter by city",
        placeholder="e.g. Riyadh, Jubail…",
        key="sidebar_city"
    )

    st.markdown("<hr>", unsafe_allow_html=True)

    nav_opts = ["Zone Directory", "Area Manager"]
    if user_role == "Team Leader":
        nav_opts.append("Coverage Manager")

    page = st.radio("", nav_opts, label_visibility="collapsed")

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown(
        f'<div style="font-size:11px;color:#3a6080;margin-top:6px;line-height:1.7;">'
        f'Signed in · <b style="color:#7eb8f7">{user_name}</b><br>'
        f'<span style="color:#2a5a80">{user_role}</span></div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div style="margin-top:24px;padding-top:14px;border-top:1px solid #162f4f;">'
        '<div style="font-size:9px;text-transform:uppercase;letter-spacing:0.12em;'
        'color:#1e4060;font-weight:600;margin-bottom:5px;">Built by</div>'
        '<div style="font-size:12.5px;color:#6aaad4;font-weight:600;'
        'letter-spacing:0.01em;">Mohamed Mossad</div>'
        '<div style="font-size:10px;color:#2a5070;margin-top:2px;">'
        'SOCOTEC Arabia</div>'
        '</div>',
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────────
#  LOAD DATA
# ─────────────────────────────────────────────
zone_df    = load_zone_data()
active_cov = load_active_coverage()
eng_names  = all_engineer_names(zone_df) if not zone_df.empty else []

# ═══════════════════════════════════════════
#  PAGE 1 — ZONE DIRECTORY
# ═══════════════════════════════════════════
if page == "Zone Directory":
    page_header(
        "Zone Directory",
        f"{len(zone_df):,} areas across {len(eng_names)} engineers"
    )

    if not active_cov.empty:
        lines = "  ·  ".join(
            f"<b>{r['original_eng']}</b> → {r['substitute']}  (until {r['end_date']})"
            for _, r in active_cov.iterrows()
        )
        st.markdown(
            f'<div class="cov-banner">⚠️ Active substitutions today: {lines}</div>',
            unsafe_allow_html=True
        )

    if zone_df.empty:
        st.info("No zone data found. Add Riyadh_Zone_Eng_Log.xlsx and "
                "IDI_Zone_Eng_Log.xlsx to the app folder, then refresh.")
        st.stop()

    # Search + source filter
    c1, c2 = st.columns([4, 1])
    with c1:
        q = st.text_input("", placeholder="Search area, city, engineer, province…",
                          label_visibility="collapsed", key="dir_search")
    with c2:
        src_opts = ["All"] + sorted(zone_df["source"].unique())
        src = st.selectbox("", src_opts, label_visibility="collapsed", key="dir_src")

    filtered = zone_df.copy()
    if src != "All":
        filtered = filtered[filtered["source"] == src]
    # Apply sidebar city filter
    if city_filter and city_filter.strip():
        filtered = filtered[
            filtered["city"].str.contains(city_filter.strip(), case=False, na=False)
        ]
    if q:
        mask = filtered.apply(
            lambda r: r.astype(str).str.contains(q, case=False, na=False).any(), axis=1
        )
        filtered = filtered[mask]

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Matches", len(filtered))
    m2.metric("Riyadh",  len(filtered[filtered["source"]=="riyadh"]))
    m3.metric("Other cities", len(filtered[filtered["source"]=="idi"]))
    m4.metric("Custom",  len(filtered[filtered["source"]=="custom"]))

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # Build coverage substitution map
    cov_map = {}
    if not active_cov.empty:
        for _, cr in active_cov.iterrows():
            cov_map[cr["original_eng"].strip()] = cr["substitute"].strip()

    tab_r, tab_o, tab_c = st.tabs(["Riyadh Areas", "Other Cities", "Custom Entries"])

    def zone_cards(subset):
        if subset.empty:
            st.markdown(
                '<div style="text-align:center;color:#8097b1;padding:32px 0;">No results</div>',
                unsafe_allow_html=True
            )
            return
        for _, row in subset.iterrows():
            insp = row.get("inspector","")
            disp_insp = cov_map.get(insp, insp)
            covered = disp_insp != insp

            area = row.get("area","") or "—"
            city = row.get("city","") or ""

            title = f"{area}"
            if city and city not in ("nan",""):
                title += f"   ·   {city}"

            with st.expander(title):
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    fld("Area / الحي", area)
                    fld("City", city)
                    fld("Province", row.get("province",""))
                with fc2:
                    insp_label = (f"{disp_insp} *(covering {insp})*"
                                  if covered else disp_insp)
                    fld("Inspector Engineer", insp_label,
                        "b-orange" if covered else "b-blue")
                    # UserID — critical for Tawuniya assignment
                    uid = row.get("user_id","")
                    if uid and uid not in ("","nan","0"):
                        fld("User ID (Tawuniya)", uid, "b-gray")
                    if row.get("email","") not in ("","nan"):
                        fld("Email", row.get("email",""))
                    fld("Team Leader", row.get("team_leader",""))
                with fc3:
                    fld("RD6 Engineer", row.get("rd6_eng",""), "b-teal")
                    fld("RD7 Engineer", row.get("rd7_eng",""), "b-gray")
                    src_map = {"riyadh":("Riyadh","b-blue"),
                               "idi":("IDI","b-teal"),
                               "custom":("Custom","b-orange")}
                    sl, sc = src_map.get(row.get("source",""),("—","b-gray"))
                    st.markdown(f'<span class="badge {sc}">{sl}</span>',
                                unsafe_allow_html=True)

    with tab_r:
        zone_cards(filtered[filtered["source"]=="riyadh"])

    with tab_o:
        other = filtered[filtered["source"]=="idi"]
        if not other.empty:
            for prov in sorted(other["province"].dropna().unique()):
                st.markdown(
                    f'<div style="font-size:11px;text-transform:uppercase;'
                    f'letter-spacing:0.1em;color:#8097b1;font-weight:600;'
                    f'margin:18px 0 8px;">{prov}</div>',
                    unsafe_allow_html=True
                )
                zone_cards(other[other["province"]==prov])
        else:
            st.markdown(
                '<div style="text-align:center;color:#8097b1;padding:32px 0;">No results</div>',
                unsafe_allow_html=True
            )

    with tab_c:
        zone_cards(filtered[filtered["source"]=="custom"])

    st.markdown("<hr style='margin:24px 0 16px'>", unsafe_allow_html=True)
    export_df = filtered.drop(columns=["id"] if "id" in filtered.columns else [])
    csv = export_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Export to CSV", csv, "socotec_zones.csv", "text/csv")

# ═══════════════════════════════════════════
#  PAGE 2 — AREA MANAGER
# ═══════════════════════════════════════════
elif page == "Area Manager":
    page_header("Area Manager", "Add, edit, or reassign area-engineer entries")

    custom_df = load_custom_areas()

    # ── Mode toggle: Add vs Edit (Team Leaders can edit, coordinators only add) ──
    can_edit = (user_role == "Team Leader")
    if can_edit:
        mode = st.radio("Action", ["Add new area", "Edit existing entry"],
                        horizontal=True, key="am_mode")
    else:
        mode = "Add new area"
        st.caption("Coordinators can add new areas. Team Leaders can also edit existing entries.")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    col_left, col_right = st.columns([1, 2])

    with col_left:
        if mode == "Add new area":
            sec("New area")
            with st.form("add_area", clear_on_submit=True):
                area_v  = st.text_input("Area name / الحي *", placeholder="e.g. حي النرجس")
                city_v  = st.text_input("City", placeholder="e.g. Riyadh")
                prov_v  = st.text_input("Province", placeholder="e.g. Riyadh Province")
                st.markdown("---")
                insp_v  = st.selectbox("Inspector Engineer *",
                                       [""] + eng_names + ["── type below ──"])
                insp_m  = st.text_input("Or type inspector name",
                                        placeholder="If not in list above")
                tl_v    = st.selectbox("Team Leader", [""] + eng_names)
                rd6_v   = st.selectbox("RD6 Engineer", [""] + eng_names)
                rd7_v   = st.selectbox("RD7 Engineer", [""] + eng_names)
                notes_v = st.text_input("Notes", placeholder="Optional")
                if st.form_submit_button("Save", type="primary", use_container_width=True):
                    final_insp = insp_m.strip() if insp_m.strip() else insp_v
                    if not area_v.strip():
                        st.error("Area name is required.")
                    elif not final_insp or final_insp.startswith("──"):
                        st.error("Inspector is required.")
                    else:
                        save_custom_area(area_v.strip(), city_v.strip(), prov_v.strip(),
                                         final_insp, tl_v, rd6_v, rd7_v, user_name, notes_v)
                        st.success(f"Saved: **{area_v}** → {final_insp}")
                        st.cache_data.clear()
                        st.rerun()

        else:  # Edit existing entry — Team Leader only
            sec("Edit any engineer / area")
            st.caption(
                "Pick any area from the full directory below. "
                "Your edit is saved as an override — the original Excel file is unchanged."
            )

            # Search to find the area quickly
            edit_search = st.text_input(
                "Search area to edit",
                placeholder="Type area name or engineer…",
                key="edit_search"
            )

            # Build full list from ALL sources (Excel + custom)
            all_zones = zone_df.copy() if not zone_df.empty else pd.DataFrame()
            if not all_zones.empty and edit_search:
                mask = all_zones.apply(
                    lambda r: r.astype(str).str.contains(
                        edit_search, case=False, na=False).any(), axis=1
                )
                all_zones = all_zones[mask]

            if all_zones.empty:
                st.info("No matching areas found. Try a different search.")
            else:
                # Show as selectable list
                zone_labels = [
                    f"{r.get('area','?')}  ·  {r.get('city','?')}  —  {r.get('inspector','?')}"
                    for _, r in all_zones.iterrows()
                ]
                sel_idx = st.selectbox(
                    f"{len(all_zones)} areas found — select one to edit",
                    range(len(zone_labels)),
                    format_func=lambda i: zone_labels[i],
                    key="am_edit_sel"
                )
                sel_row = all_zones.iloc[sel_idx]
                # Check if a custom override already exists for this area
                existing = custom_df[
                    custom_df["area"].str.strip() == str(sel_row.get("area","")).strip()
                ]
                row_id = int(existing.iloc[0]["id"]) if not existing.empty else None
                if row_id:
                    st.info("This area already has a custom override. Saving will update it.")

                # Pre-filled edit form — values from selected row (Excel or custom)
                with st.form("edit_area_form"):
                    e_area = st.text_input("Area name *",
                                           value=str(sel_row.get("area","") or ""))
                    e_city = st.text_input("City",
                                           value=str(sel_row.get("city","") or ""))
                    e_prov = st.text_input("Province",
                                           value=str(sel_row.get("province","") or ""))
                    st.markdown("---")
                    cur_insp = str(sel_row.get("inspector","") or "")
                    insp_opts = [""] + sorted(set(eng_names + ([cur_insp] if cur_insp else [])))
                    e_insp_sel = st.selectbox(
                        "Inspector Engineer *", insp_opts,
                        index=insp_opts.index(cur_insp) if cur_insp in insp_opts else 0
                    )
                    e_insp_m = st.text_input("Or type inspector name",
                                             placeholder="Overrides dropdown above")

                    cur_tl   = sel_row.get("team_leader","")
                    cur_rd6  = sel_row.get("rd6_eng","")
                    cur_rd7  = sel_row.get("rd7_eng","")
                    tl_opts  = [""] + sorted(set(eng_names + ([cur_tl]  if cur_tl  else [])))
                    rd6_opts = [""] + sorted(set(eng_names + ([cur_rd6] if cur_rd6 else [])))
                    rd7_opts = [""] + sorted(set(eng_names + ([cur_rd7] if cur_rd7 else [])))

                    e_tl  = st.selectbox("Team Leader",  tl_opts,
                                         index=tl_opts.index(cur_tl)   if cur_tl  in tl_opts  else 0)
                    e_rd6 = st.selectbox("RD6 Engineer", rd6_opts,
                                         index=rd6_opts.index(cur_rd6)  if cur_rd6 in rd6_opts else 0)
                    e_rd7 = st.selectbox("RD7 Engineer", rd7_opts,
                                         index=rd7_opts.index(cur_rd7)  if cur_rd7 in rd7_opts else 0)
                    e_notes = st.text_input("Notes",
                                            value=sel_row.get("notes","") or "")

                    col_s, col_d = st.columns(2)
                    with col_s:
                        btn_label = "Update override" if row_id else "Save as override"
                        if st.form_submit_button(btn_label, type="primary",
                                                  use_container_width=True):
                            final_insp = e_insp_m.strip() if e_insp_m.strip() else e_insp_sel
                            if not e_area.strip():
                                st.error("Area name required.")
                            elif not final_insp:
                                st.error("Inspector required.")
                            else:
                                save_custom_area(
                                    e_area.strip(), e_city.strip(), e_prov.strip(),
                                    final_insp, e_tl, e_rd6, e_rd7,
                                    user_name, e_notes, row_id=row_id
                                )
                                st.success(f"Saved: **{e_area}** → {final_insp}")
                                st.cache_data.clear()
                                st.rerun()
                    with col_d:
                        if row_id:
                            if st.form_submit_button("Remove override", type="secondary",
                                                      use_container_width=True):
                                delete_custom_area(row_id)
                                st.success("Override removed — original Excel data restored.")
                                st.cache_data.clear()
                                st.rerun()

    with col_right:
        sec(f"All custom entries  ({len(custom_df)})")
        if custom_df.empty:
            st.info("No custom entries yet.")
        else:
            srch = st.text_input("", placeholder="Filter entries…",
                                 label_visibility="collapsed", key="am_search")
            disp = custom_df.copy()
            if srch:
                mask = disp.apply(
                    lambda r: r.astype(str).str.contains(srch, case=False, na=False).any(), axis=1
                )
                disp = disp[mask]

            st.markdown(
                f'<div style="color:#8097b1;font-size:12px;margin-bottom:10px;">' 
                f'{len(disp)} entr{"y" if len(disp)==1 else "ies"}</div>',
                unsafe_allow_html=True
            )

            for _, r in disp.iterrows():
                label = f"{r.get('area','?')}  ·  {r.get('city','?')}  —  {r.get('inspector','?')}"
                with st.expander(label):
                    ea, eb = st.columns(2)
                    with ea:
                        fld("Area", r.get("area",""))
                        fld("City", r.get("city",""))
                        fld("Province", r.get("province",""))
                        fld("Added by", r.get("added_by",""))
                        fld("Date", r.get("added_date",""))
                    with eb:
                        fld("Inspector", r.get("inspector",""), "b-blue")
                        fld("Team Leader", r.get("team_leader",""))
                        fld("RD6 Engineer", r.get("rd6_eng",""), "b-teal")
                        fld("RD7 Engineer", r.get("rd7_eng",""), "b-gray")
                        if r.get("notes","") not in ("","nan"):
                            fld("Notes", r.get("notes",""))
                    if can_edit:
                        if st.button("Quick delete", key=f"del_{r['id']}",
                                     type="secondary"):
                            delete_custom_area(r["id"])
                            st.cache_data.clear()
                            st.rerun()

# ═══════════════════════════════════════════
#  PAGE 3 — COVERAGE MANAGER (Team Leader)
# ═══════════════════════════════════════════
elif page == "Coverage Manager":
    page_header("Coverage Manager",
                "Set temporary substitutions for leave and vacation")

    if not active_cov.empty:
        lines = "  ·  ".join(
            f"<b>{r['original_eng']}</b> → {r['substitute']}  (until {r['end_date']})"
            for _, r in active_cov.iterrows()
        )
        st.markdown(
            f'<div class="cov-banner">⚠️  <b>{len(active_cov)} active rule(s) today.</b>'
            f'  Substitutes appear automatically in the Zone Directory.<br>{lines}</div>',
            unsafe_allow_html=True
        )
    else:
        st.success("No active coverage rules today — all engineers assigned normally.")

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    col_f, col_h = st.columns([1, 2])

    with col_f:
        sec("New coverage rule")
        with st.form("cov_form"):
            orig = st.selectbox("Engineer going on leave *", [""] + eng_names)
            sub  = st.selectbox("Substitute engineer *",     [""] + eng_names)
            af   = st.text_input("Limit to specific area (optional)",
                                 placeholder="Blank = all areas")
            d1, d2 = st.columns(2)
            with d1:
                sd = st.date_input("From", value=date.today())
            with d2:
                ed = st.date_input("To",   value=date.today() + timedelta(days=6))
            rsn = st.text_input("Reason",
                                placeholder="Annual leave, sick leave…")
            if st.form_submit_button("Save rule", type="primary",
                                     use_container_width=True):
                if not orig or not sub:
                    st.error("Both engineers required.")
                elif orig == sub:
                    st.error("Cannot substitute with same engineer.")
                elif ed < sd:
                    st.error("End date must be after start date.")
                else:
                    save_coverage(orig, sub, af, sd, ed, rsn, user_name)
                    st.success(f"Rule saved: **{sub}** covers **{orig}**")
                    st.rerun()

    with col_h:
        sec("Coverage history")
        all_cov = load_all_coverage()
        if all_cov.empty:
            st.info("No rules created yet.")
        else:
            for _, r in all_cov.iterrows():
                s, e, t = r["start_date"], r["end_date"], today_str()
                if e < t:   st_lbl, st_cls = "Expired",  "b-gray"
                elif s > t: st_lbl, st_cls = "Upcoming", "b-blue"
                else:       st_lbl, st_cls = "Active",   "b-green"

                af_note = f" · {r['area_filter']}" if r.get("area_filter") else " · all areas"
                with st.expander(
                    f"{r['original_eng']}  →  {r['substitute']}"
                    f"   [{r['start_date']} – {r['end_date']}]"
                ):
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        fld("Original engineer", r["original_eng"])
                        fld("Substitute",        r["substitute"])
                        fld("Area scope",
                            r["area_filter"] if r.get("area_filter") else "All areas")
                    with rc2:
                        fld("Period",
                            f"{r['start_date']}  →  {r['end_date']}")
                        fld("Reason", r.get("reason",""))
                        fld("Set by", r.get("created_by",""))
                        st.markdown(
                            f'<span class="badge {st_cls}">{st_lbl}</span>',
                            unsafe_allow_html=True
                        )
                    if st.button("Remove", key=f"rcov_{r['id']}", type="secondary"):
                        delete_coverage(r["id"])
                        st.rerun()

    st.markdown("<hr style='margin:24px 0 16px'>", unsafe_allow_html=True)
    sec("Engineer → area reference")
    st.caption("From the loaded Excel files. To permanently change assignments, "
               "update the source files and refresh.")
    if not zone_df.empty:
        ef = st.selectbox("Filter by engineer",
                          ["All"] + eng_names, key="cov_ref")
        ref = zone_df.copy()
        if ef != "All":
            ref = ref[ref["inspector"].str.strip() == ef]
        show = [c for c in ["area","city","province","inspector","team_leader"]
                if c in ref.columns]
        st.dataframe(ref[show].reset_index(drop=True),
                     use_container_width=True, hide_index=True, height=300)
