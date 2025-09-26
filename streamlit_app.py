import datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

# ---------------------------------
# Config
# ---------------------------------
st.set_page_config(
    page_title="LadyAlexis Sleep Persuasion Tracker",
    page_icon="🕰️",
    layout="centered",
)

st.markdown(
    """
    <style>
      .big {font-size:2.25rem;font-weight:800}
      .pill {display:inline-block;padding:.35rem .75rem;border-radius:999px;background:#f1f1f1;margin-right:.5rem}
      .legend {display:flex;gap:.5rem;flex-wrap:wrap}
      .tag {border-radius:999px;padding:.2rem .6rem;font-size:.85rem;border:1px solid rgba(0,0,0,.06)}
      .g {background:#065f46;color:#ecfdf5;}
      .y {background:#92400e;color:#fffbeb;}
      .o {background:#7c2d12;color:#fff7ed;}
      .r {background:#7f1d1d;color:#fef2f2;}
      .dataframe td {color: inherit !important;}
      footer {visibility:hidden}
    </style>
    """,
    unsafe_allow_html=True,
)

# ================================
# 🔗 SET THIS: your Google Sheets public CSV URL (read-only)
# ================================
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQMSMnUIvKqWIyjkIviWx9u8J8zel5XPQU1ahs169tMPZe_XgfLwTomhBKPzqDMi6B3f59yXjgTfwF7/pub?output=csv"
REFRESH_EVERY_SECONDS = 300

IST = ZoneInfo("Asia/Kolkata")
DC = ZoneInfo("America/New_York")

@st.cache_data(ttl=REFRESH_EVERY_SECONDS, show_spinner=True)
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip().str.lower()

    for col in ["date","start","slept","duration_min","note"]:
        if col not in df.columns:
            df[col] = None

    df = df[["date","start","slept","duration_min","note"]]
    df = df.replace({"": pd.NA, "None": pd.NA, "none": pd.NA, "NaN": pd.NA, "nan": pd.NA})
    df["duration_min"] = pd.to_numeric(df["duration_min"], errors="coerce")

    def compute_minutes(row):
        if pd.notna(row["duration_min"]):
            return int(row["duration_min"])
        try:
            d = pd.to_datetime(row["date"], errors="coerce").date()
            s = pd.to_datetime(row["start"], errors="coerce").time()
            sl = pd.to_datetime(row["slept"], errors="coerce").time()
            start_dt = dt.datetime.combine(d, s).replace(tzinfo=IST)
            slept_dt = dt.datetime.combine(d, sl).replace(tzinfo=IST)
            if slept_dt < start_dt:
                slept_dt += dt.timedelta(days=1)
            return int((slept_dt - start_dt).total_seconds() // 60)
        except Exception:
            return pd.NA

    df["duration_min"] = df.apply(compute_minutes, axis=1)

    def to_dc_strings(row):
        try:
            d = pd.to_datetime(row["date"], errors="coerce").date()
            s_t = pd.to_datetime(row["start"], errors="coerce").time()
            sl_t = pd.to_datetime(row["slept"], errors="coerce").time()
            s_dt_ist = dt.datetime.combine(d, s_t).replace(tzinfo=IST)
            sl_dt_ist = dt.datetime.combine(d, sl_t).replace(tzinfo=IST)
            if sl_dt_ist < s_dt_ist:
                sl_dt_ist += dt.timedelta(days=1)
            return (
                s_dt_ist.astimezone(DC).strftime("%Y-%m-%d %I:%M %p"),
                sl_dt_ist.astimezone(DC).strftime("%Y-%m-%d %I:%M %p"),
            )
        except Exception:
            return (None, None)

    dc_pairs = df.apply(to_dc_strings, axis=1, result_type="expand")
    df["start_dc"], df["slept_dc"] = dc_pairs[0], dc_pairs[1]
    df["_sort"] = pd.to_datetime(df["start_dc"], errors="coerce")
    df = df.sort_values("_sort").drop(columns=["_sort"])
    df["duration_min"] = pd.to_numeric(df["duration_min"], errors="coerce").astype("Int64")
    return df

if "YOUR_SHEET_ID" in SHEET_CSV_URL:
    st.error("Set SHEET_CSV_URL in the code to your published Google Sheets CSV link.")
    st.stop()

st.markdown("<div class='big'>ladyAlexis Sleep Persuasion Tracker</div>", unsafe_allow_html=True)
st.caption("Times are shown in EST time (converted from IST).")

try:
    df = load_data(SHEET_CSV_URL)
except Exception as e:
    st.error(f"Couldn't load CSV: {e}")
    st.stop()

if df.empty:
    st.info("No rows to display yet. Add rows in your Google Sheet.")
    st.stop()

# Metrics
durations = df["duration_min"].dropna().astype(int)
colA, colB, colC, colD = st.columns(4)
with colA:
    avg = int(durations.mean()) if len(durations) else 0
    st.metric("Average time", f"{avg} min")
with colB:
    latest = int(durations.iloc[-1]) if len(durations) else 0
    st.metric("Latest", f"{latest} min")
with colC:
    best = int(durations.min()) if len(durations) else 0
    st.metric("Fastest", f"{best} min")
with colD:
    worst = int(durations.max()) if len(durations) else 0
    st.metric("Slowest", f"{worst} min")

# Legend
st.markdown(
    """
    <div class='legend'>
      <span class='tag g'>✅ &lt; 20 min (great)</span>
      <span class='tag y'>🟡 20–45 min (ok)</span>
      <span class='tag o'>🟠 45–60 min (tough)</span>
      <span class='tag r'>🟥 &gt; 60 min (needs work)</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# Trend chart
chart_df = df[["start_dc", "duration_min"]].copy()
chart_df["start_dc"] = pd.to_datetime(chart_df["start_dc"], errors="coerce")
chart_df = chart_df.dropna(subset=["start_dc", "duration_min"]).set_index("start_dc").sort_index()
if not chart_df.empty:
    st.subheader("Trend (Washington time)")
    st.line_chart(chart_df)

# Styled table
view_df = df[["start_dc", "slept_dc", "duration_min", "note"]].rename(
    columns={
        "start_dc": "Start (DC)",
        "slept_dc": "Slept (DC)",
        "duration_min": "Minutes",
        "note": "Note",
    }
)

# Custom style with dark‑mode friendly colors
def color_minutes(vals):
    styles = []
    for v in vals:
        try:
            x = int(v)
        except Exception:
            styles.append("")
            continue
        if x < 20:
            styles.append("background-color:#065f46;color:#ecfdf5;")
        elif 20 <= x <= 45:
            styles.append("background-color:#92400e;color:#fffbeb;")
        elif 45 < x <= 60:
            styles.append("background-color:#7c2d12;color:#fff7ed;")
        else:
            styles.append("background-color:#7f1d1d;color:#fef2f2;")
    return styles

styled = view_df.style.apply(color_minutes, subset=["Minutes"]).format(precision=0, na_rep="–")

st.subheader("Entries (converted to Washington time)")
st.dataframe(styled, hide_index=True, use_container_width=True)


if st.button("Refresh now"):
    load_data.clear()
    st.rerun()
