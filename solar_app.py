import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - VOLLEDIG WERKEND ☀️
# ==========================================

# 1. Google Sheet Configuratie (Gecorrigeerd op basis van je afbeelding)
SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
SHEET_NAME = "Historiek"  # Dit was de boosdoener!
CSV_URL = f"https://google.com{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# 2. Inverter IPs
PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- Records laden ---
if 'p_total' not in st.session_state:
    st.session_state.p_symo = st.secrets.get("symo_piek", 3711.0)
    st.session_state.p_galvo = st.secrets.get("galvo_piek", 6.0)
    st.session_state.p_total = st.secrets.get("totaal_piek", 3717.0)

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        val = abs(float(r['active_power_w']))
        return val, "🟢"
    except: return 0.0, "🔴"

# --- Live Data ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

if val_t > st.session_state.p_total: 
    st.session_state.p_total = val_t
    st.balloons()

# --- Display ---
st.title("💚 Solar Piek Pro")
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
st.metric("🏆 All-time Record", f"{st.session_state.p_total:,.0f} W")

st.divider()

# --- Grafiek Sectie ---
st.subheader("📊 Historiek Overzicht")
try:
    # We lezen de CSV in
    df = pd.read_csv(CSV_URL)
    
    if not df.empty:
        # We koppelen de kolommen 'Datum' en 'Totaal' uit jouw screenshot
        chart_data = pd.DataFrame({
            'Dag': df['Datum'].astype(str),
            'Watt': pd.to_numeric(df['Totaal'], errors='coerce')
        }).dropna()
        
        st.bar_chart(data=chart_data, x='Dag', y='Watt')
    else:
        st.info("De sheet is leeg.")
except Exception as e:
    st.error(f"Kan sheet niet laden. Check of 'Delen' op 'Iedereen met de link' staat.")

st.caption(f"Laatste update: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(2)
st.rerun()
