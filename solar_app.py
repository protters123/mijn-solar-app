import streamlit as st
import requests
import time
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# SOLAR PIEK PRO - HISTORIEK FIX
# ==========================================
PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

# JOUW GOOGLE SHEET LINK
SHEET_URL = "https://google.com"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- RECORDS LADEN ---
if 'p_symo' not in st.session_state:
    st.session_state.p_symo = st.secrets.get("symo_piek", 3740.0)
    st.session_state.p_galvo = st.secrets.get("galvo_piek", 0.0)
    st.session_state.p_total = st.secrets.get("totaal_piek", 3740.0)

conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

# --- DATA ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# Records updaten
if val_s > st.session_state.p_symo: st.session_state.p_symo = val_s
if val_g > st.session_state.p_galvo: st.session_state.p_galvo = val_g
if val_t > st.session_state.p_total: 
    st.session_state.p_total = val_t
    st.balloons()

# --- DISPLAY ---
st.title("☀️ Solar Piek Pro")
st.metric("🏆 All-time Record", f"{st.session_state.p_total:,.0f} W", delta=f"{val_t - st.session_state.p_total:,.0f} W")

c1, c2 = st.columns(2)
with c1:
    st.subheader(f"{icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
with c2:
    st.subheader(f"{icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")

st.divider()

# --- MAANDOVERZICHT ---
st.subheader("📅 Maandoverzicht")
try:
    df_hist = conn.read(spreadsheet=SHEET_URL, worksheet="Historiek", ttl=0)
    if not df_hist.empty:
        # We pakken de kolom met de datum en de laatste kolom voor de grafiek
        df_hist['Datum'] = pd.to_datetime(df_hist['Datum']).dt.date
        st.bar_chart(data=df_hist, x='Datum', y=df_hist.columns[-1])
    else:
        st.info("Vul een datum en piek in het tabblad 'Historiek' in.")
except Exception:
    st.caption("Wacht op data in Google Sheets...")

st.caption(f"Check: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(2)
st.rerun()
