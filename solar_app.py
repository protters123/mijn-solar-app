import streamlit as st
import requests
import time
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# SOLAR PIEK PRO - SIMPELE GRAFIEK FIX
# ==========================================
PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"
SHEET_URL = "https://google.com"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- RECORDS UIT SECRETS ---
if 'p_total' not in st.session_state:
    st.session_state.p_symo = st.secrets.get("symo_piek", 3711.0)
    st.session_state.p_galvo = st.secrets.get("galvo_piek", 6.0)
    st.session_state.p_total = st.secrets.get("totaal_piek", 3717.0)

# Verbinding maken
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

# Update records
if val_s > st.session_state.p_symo: st.session_state.p_symo = val_s
if val_g > st.session_state.p_galvo: st.session_state.p_galvo = val_g
if val_t > st.session_state.p_total: 
    st.session_state.p_total = val_t
    st.balloons()

# --- DISPLAY ---
st.title("☀️ Solar Piek Pro")
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
st.metric("🏆 All-time Record", f"{st.session_state.p_total:,.0f} W")

st.divider()

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"### {icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
    st.caption(f"Record: {st.session_state.p_symo} W")
with c2:
    st.markdown(f"### {icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")
    st.caption(f"Record: {st.session_state.p_galvo} W")

st.divider()

# --- GRAFIEK SECTIE (VERSIMPELD) ---
st.subheader("📅 Maandoverzicht Hoogste Pieken")
try:
    # We lezen simpelweg de hele sheet in
    df = conn.read(spreadsheet=SHEET_URL, ttl=0)
    if not df.empty:
        # We pakken de eerste en laatste kolom voor de balkjes
        chart_data = df.iloc[:, [0, -1]]
        chart_data.columns = ['Datum', 'Piek']
        st.bar_chart(data=chart_data, x='Datum', y='Piek')
    else:
        st.info("Nog geen data in de Google Sheet gevonden.")
except Exception as e:
    st.caption("Verbinding maken met Google Sheets...")

st.caption(f"Check: {datetime.now().strftime('%H:%M:%S')} | 2 sec interval")
time.sleep(2)
st.rerun()
