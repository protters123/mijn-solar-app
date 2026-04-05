import streamlit as st
import requests
import time
import pandas as pd
import io
import os
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO - DEFINITIEVE VERSIE ☀️
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://google.com"

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- TIJDZONE & GEHEUGEN ---
tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
CACHE_FILE = "dagpiek_geheugen.txt"

# --- WEER INTERPRETATIE (WMO CODES) ---
def get_weather_info(code):
    mapping = {
        0: ("Onbewolkt", "☀️"), 1: ("Licht bewolkt", "🌤️"), 2: ("Half bewolkt", "⛅"), 3: ("Bewolkt", "☁️"),
        45: ("Mistig", "🌫️"), 48: ("Rijpende mist", "🌫️"),
        51: ("Lichte motregen", "🌦️"), 53: ("Matige motregen", "🌦️"), 55: ("Dichte motregen", "🌦️"),
        61: ("Lichte regen", "🌧️"), 63: ("Matige regen", "🌧️"), 65: ("Zware regen", "🌧️"),
        95: ("Onweer", "⚡")
    }
    return mapping.get(code, ("Onbekend", "🌡️"))

@st.cache_data(ttl=3600)
def get_weather_forecast():
    try:
        # Locatie: Tongeren-Borgloon
        url = "https://open-meteo.com"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()["daily"]
        return None
    except:
        return None

def laad_dagpiek():
    vandaag = nu_lokaal.strftime('%Y-%m-%d')
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                content = f.read().strip()
                if content and content.split(",")[0] == vandaag:
                    parts = content.split(",")
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
    st.session_state.p_symo_peak, st.session_state.p_galvo_peak = s_start, g_start

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

# --- LIVE DATA ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

if val_s > st.session_state.p_symo_peak or val_g > st.session_state.p_galvo_peak:
    st.session_state.p_symo_peak = max(val_s, st.session_state.p_symo_peak)
    st.session_state.p_galvo_peak = max(val_g, st.session_state.p_galvo_peak)
    sla_dagpiek_op(st.session_state.p_symo_peak, st.session_state.p_galvo_peak)

# --- UI DASHBOARD ---
st.title("☀️ Solar Piek Pro") 

# --- GECORRIGEERDE WEER SECTIE ---
forecast = get_weather_forecast()
if forecast:
    # Cruciaal: We pakken index [0] voor vandaag
    desc_v, icon_v = get_weather_info(forecast['weather_code'][0])
    
    st.subheader(f"{icon_v} {desc_v} in Tongeren")
    
    w1, w2 = st.columns(2)
    with w1:
        st.metric("Temperatuur", f"{forecast['temperature_2m_max'][0]}°C")
    with w2:
        st.metric("Zonnestraling", f"{forecast['shortwave_radiation_sum'][0]} MJ/m²")
else:
    st.error("Weergegevens tijdelijk niet bereikbaar...")

st.divider()

st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
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

st.caption(f"Update: {nu_lokaal.strftime('%H:%M:%S')}")
time.sleep(2)
st.rerun()
