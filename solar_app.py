import streamlit as st
import requests
import time
import pandas as pd
import io
import os
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO - WEATHER EDITION ☀️🌡️
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://google.com"

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

# Locatie instellen (Tongeren/Borgloon regio op basis van jouw IP/Locatie)
LAT, LON = 50.78, 5.46 

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- WEER FUNCTIE ---
def get_weather():
    try:
        url = f"https://open-meteo.com{LAT}&longitude={LON}&current=temperature_2m,weather_code&daily=weather_code,temperature_2m_max&timezone=Europe%2FBerlin&forecast_days=1"
        r = requests.get(url, timeout=3).json()
        temp = r['current']['temperature_2m']
        code = r['current']['weather_code']
        max_temp = r['daily']['temperature_2m_max'][0]
        
        # Weercode naar Icoon mapping
        icons = {0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️", 45: "🌫️", 51: "🌦️", 61: "🌧️", 71: "❄️", 95: "⚡"}
        icoon = icons.get(code, "☁️")
        return temp, icoon, max_temp
    except:
        return "--", "🌡️", "--"

# --- TIJDZONE & GEHEUGEN ---
tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
CACHE_FILE = "dagpiek_geheugen.txt"
ARCHIVE_LOG = "laatst_gearchiveerd.txt"

def laad_dagpiek():
    vandaag = nu_lokaal.strftime('%Y-%m-%d')
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    parts = content.split(",")
                    if parts[0] == vandaag:
                        return float(parts[1]), float(parts[2])
        except: pass
    return 0.0, 0.0

def sla_dagpiek_op(s, g):
    vandaag = nu_lokaal.strftime('%Y-%m-%d')
    with open(CACHE_FILE, "w") as f:
        f.write(f"{vandaag},{s},{g}")

# --- INITIALISEREN ---
if 'p_symo_peak' not in st.session_state:
    s_start, g_start = laad_dagpiek()
    st.session_state.p_symo_peak = s_start
    st.session_state.p_galvo_peak = g_start
if 'record_celebrated' not in st.session_state:
    st.session_state.record_celebrated = False

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

# --- DATA LADEN ---
curr_temp, weather_icon, daily_max = get_weather()
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# Update Dagpieken
if val_s > st.session_state.p_symo_peak or val_g > st.session_state.p_galvo_peak:
    st.session_state.p_symo_peak = max(val_s, st.session_state.p_symo_peak)
    st.session_state.p_galvo_peak = max(val_g, st.session_state.p_galvo_peak)
    sla_dagpiek_op(st.session_state.p_symo_peak, st.session_state.p_galvo_peak)

# --- UI DASHBOARD ---
st.title("☀️ Solar Piek Pro")

# Weer Header
c_w1, c_w2 = st.columns(2)
c_w1.metric("Buitentemperatuur", f"{weather_icon} {curr_temp}°C")
c_w2.metric("Verwacht Max", f"🌡️ {daily_max}°C")

st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")

# Historisch Record
historical_max = 3729.0
try:
    res = requests.get(CSV_URL, timeout=5)
    if res.status_code == 200:
        df = pd.read_csv(io.StringIO(res.text))
        historical_max = pd.to_numeric(df.iloc[:, 3], errors='coerce').max()
except: pass

st.metric("🏆 All-time Record", f"{max(historical_max, val_t):,.0f} W")

st.divider()

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"### {icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
    st.metric("Piek Vandaag", f"{st.session_state.p_symo_peak:,.0f} W")
with c2:
    st.markdown(f"### {icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")
    st.metric("Piek Vandaag", f"{st.session_state.p_galvo_peak:,.0f} W")

st.divider()
st.subheader("💚 Maandoverzicht") 
# ... (Tabel logica blijft gelijk)

st.caption(f"Update: {nu_lokaal.strftime('%H:%M:%S')} | Locatie: Tongeren-Borgloon")
time.sleep(10) # Iets langer wachten om weer-API niet te overbelasten
st.rerun()
