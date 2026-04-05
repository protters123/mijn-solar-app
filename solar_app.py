import streamlit as st
import requests
import time
import pandas as pd
import io
import os
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO - VOLLEDIG HERSTEL ☀️
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbw2FVnk85VhZqhr_QL7e-nN_KRVSxiVVVrDrkOdYQYK5QPDa-wWe9bUaocstvH0mrsQ/exec"

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- TIJD EN GEHEUGEN ---
tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
CACHE_FILE = "dagpiek_geheugen.txt"
ARCHIVE_LOG = "laatst_gearchiveerd.txt"

# --- WEER-ICOON BEPALEN ---
def get_weather_icon(code):
    if code == 0: return "☀️"
    if code in [1, 2, 3]: return "🌤️"
    if code in [45, 48]: return "🌫️"
    if code in [51, 53, 55, 61, 63, 65, 80, 81, 82]: return "🌧️"
    if code in [71, 73, 75, 77, 85, 86]: return "❄️"
    if code in [95, 96, 99]: return "⛈️"
    return "☁️"

# --- DATA LADEN ---
def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

# Haal tabel en record op
historical_max = 3729.0
table_df = pd.DataFrame()
try:
    res = requests.get(CSV_URL, timeout=5)
    if res.status_code == 200:
        df = pd.read_csv(io.StringIO(res.text))
        historical_max = pd.to_numeric(df.iloc[:, 3], errors='coerce').max()
        table_df = df
except: pass

# Haal weer op
weather_data = None
try:
    w_res = requests.get("https://open-meteo.com", timeout=2).json()
    weather_data = w_res
except: pass

# Live data omvormers
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# --- GEHEUGEN UPDATEN ---
if 'p_symo_peak' not in st.session_state:
    st.session_state.p_symo_peak = 0.0
    st.session_state.p_galvo_peak = 0.0

st.session_state.p_symo_peak = max(val_s, st.session_state.p_symo_peak)
st.session_state.p_galvo_peak = max(val_g, st.session_state.p_galvo_peak)

# --- UI DASHBOARD ---
st.title("☀️ Solar Piek Pro")

# Weer-balk
if weather_data:
    w_icon = get_weather_icon(weather_data['current_weather']['weathercode'])
    w1, w2, w3 = st.columns(3)
    w1.metric(f"{w_icon} Nu", f"{weather_data['current_weather']['temperature']}°C")
    w2.metric("🌡️ Max Today", f"{weather_data['daily']['temperature_2m_max'][0]}°C")
    w3.metric("⛱️ UV Index", f"{weather_data['daily']['uv_index_max'][0]}")
    st.divider()

st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
st.metric("🏆 All-time Record", f"{max(historical_max, val_t):,.0f} W")
st.divider()

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"### {icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
    st.caption(f"Piek: {st.session_state.p_symo_peak:,.0f} W")
with c2:
    st.markdown(f"### {icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")
    st.caption(f"Piek: {st.session_state.p_galvo_peak:,.0f} W")

st.divider()

# --- TABEL ---
st.subheader("💚 Maandoverzicht") 
if not table_df.empty:
    st.table(table_df.iloc[::-1].head(15))
else:
    st.warning("Data wordt geladen...")

st.caption(f"Update: {nu_lokaal.strftime('%H:%M:%S')} | Auto-log: 23:00")
time.sleep(2)
st.rerun()
