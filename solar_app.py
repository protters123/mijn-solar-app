import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - DE DEFINITIEVE FIX ☀️
# ==========================================

# 1. Google Sheet Configuratie (GEFIXTE URL)
SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
SHEET_NAME = "Historiek" 
CSV_URL = f"https://google.com{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# 2. Inverter Gegevens
PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- Records initialiseren ---
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

# --- Dashboard UI ---
st.title("💚 Solar Piek Pro")
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
st.metric("🏆 All-time Record", f"{st.session_state.p_total:,.0f} W")

st.divider()

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"### {icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
with c2:
    st.markdown(f"### {icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")

st.divider()

# --- De Grafiek Sectie ---
st.subheader("📊 Maandoverzicht")
try:
    # Data ophalen uit de sheet via de correcte CSV_URL
    df = pd.read_csv(CSV_URL)
    
    # We gebruiken de kolomnamen 'Datum' en 'Totaal' uit jouw screenshot
    if 'Datum' in df.columns and 'Totaal' in df.columns:
        chart_df = pd.DataFrame({
            'Dag': df['Datum'].astype(str),
            'Watt': pd.to_numeric(df['Totaal'], errors='coerce')
        }).dropna()
        
        # De balkgrafiek tekenen
        st.bar_chart(data=chart_df, x='Dag', y='Watt')
    else:
        st.warning(f"Kolommen niet gevonden. Ik zie wel: {df.columns.tolist()}")
except Exception as e:
    st.error(f"Kan geen verbinding maken met de sheet: {e}")

st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')} | 2 sec interval")

# Refresh de pagina
time.sleep(2)
st.rerun()
