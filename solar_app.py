import streamlit as st
import requests
import time
import pandas as pd
import io
import os
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO - CLEAN UI & REPAIRED WEATHER
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://google.com" 

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek", page_icon="☀️", layout="centered")

# --- CSS VOOR EEN STRAKKE LAY-OUT ---
st.markdown("""
    <style>
    @keyframes blinker { 50% { opacity: 0; } }
    .stroom-teken { animation: blinker 1.5s linear infinite; color: #FFD700; font-size: 1.2rem; }
    .status-bar { 
        background: #f8f9fb; 
        padding: 10px 20px; 
        border-radius: 8px; 
        border: 1px solid #ddd;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- TIJDZONE ---
tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
vandaag_iso = nu_lokaal.strftime('%Y-%m-%d')
vandaag_nl = nu_lokaal.strftime('%d-%m-%Y')

# --- WEER & DATA ---
def get_weather_simple():
    try:
        # 'format=3' geeft 1 korte regel tekst zonder rommel
        r = requests.get("https://wttr.in", timeout=2)
        return r.text.strip()
    except:
        return "☀️ Weerbericht"

def fetch_fronius_data(url):
    try:
        r = requests.get(url, timeout=2).json()
        power = abs(float(r.get('active_power_w', 0)))
        energy = float(r.get('energy_today_wh', 0)) / 1000.0
        return power, energy, "🟢"
    except:
        return 0.0, 0.0, "🔴"

# --- DATA OPHALEN ---
val_s, kwh_s, icon_s = fetch_fronius_data(URL_1)
val_g, kwh_g, icon_g = fetch_fronius_data(URL_2)
val_t, kwh_t = val_s + val_g, kwh_s + kwh_g

# --- UI OPBOUW ---
st.title("☀️ Solar Piek") 

# STATUS BALK (WEER + TIJD)
weather = get_weather_simple()
st.markdown(f"""
    <div class='status-bar'>
        <span>🌍 <b>{weather}</b></span>
        <span>⏰ <b>{nu_lokaal.strftime('%H:%M')}</b> ({vandaag_nl})</span>
    </div>
""", unsafe_allow_html=True)

# DASHBOARD STATS
c_live, c_oogst = st.columns(2)
with c_live:
    st.markdown(f"### Live: <span class='stroom-teken'>⚡</span> {val_t:,.0f} W", unsafe_allow_html=True)
with c_oogst:
    st.markdown(f"### Dag-oogst: 🍯 {kwh_t:,.2f} kWh")

st.divider()

# LIVE TABEL
st.subheader("📊 Actuele Details")
oogst_data = {
    "Inverter": [f"{icon_s} Symo", f"{icon_g} Galvo", "✨ Totaal"],
    "Live (W)": [f"{val_s:,.0f}", f"{val_g:,.0f}", f"{val_t:,.0f}"],
    "Oogst/dag (kWh)": [f"{kwh_s:.2f}", f"{kwh_g:.2f}", f"{kwh_t:.2f}"]
}
st.table(pd.DataFrame(oogst_data))

# HISTORIE LADEN
table_df = pd.DataFrame()
try:
    res = requests.get(CSV_URL, timeout=10)
    if res.status_code == 200:
        df = pd.read_csv(io.StringIO(res.text))
        if not df.empty:
            while len(df.columns) < 5: df[f'Extra_{len(df.columns)}'] = ""
            df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag']
            table_df = df
except: pass

st.divider()

# JAAROVERZICHT
st.subheader("📅 Jaaroverzicht (Historie)") 
if not table_df.empty:
    st.dataframe(table_df.iloc[::-1], use_container_width=True, height=350)

st.caption(f"Laatste update: {nu_lokaal.strftime('%H:%M:%S')}")
time.sleep(2)
st.rerun()
