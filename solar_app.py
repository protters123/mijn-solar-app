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
ARCHIVE_LOG = "laatst_gearchiveerd.txt"

# --- WEER INTERPRETATIE FUNCTIE ---
def get_weather_info(code):
    # WMO Weather interpretation codes (WW)
    mapping = {
        0: ("Onbewolkt", "☀️"), 1: ("Licht bewolkt", "🌤️"), 2: ("Half bewolkt", "⛅"), 3: ("Bewolkt", "☁️"),
        45: ("Mistig", "🌫️"), 48: ("Rijpende mist", "🌫️"),
        51: ("Lichte motregen", "🌦️"), 53: ("Matige motregen", "🌦️"), 55: ("Dichte motregen", "🌦️"),
        61: ("Lichte regen", "🌧️"), 63: ("Matige regen", "🌧️"), 65: ("Zware regen", "🌧️"),
        71: ("Lichte sneeuwval", "❄️"), 73: ("Matige sneeuwval", "❄️"), 75: ("Zware sneeuwval", "❄️"),
        77: ("Sneeuwkorrels", "❄️"),
        80: ("Lichte regenbuien", "🌦️"), 81: ("Matige regenbuien", "🌧️"), 82: ("Zware regenbuien", "⛈️"),
        95: ("Onweer", "⚡"), 96: ("Onweer met hagel", "⛈️"), 99: ("Zwaar onweer", "⛈️")
    }
    return mapping.get(code, ("Onbekend", "🌡️"))

@st.cache_data(ttl=3600)
def get_weather_forecast():
    try:
        # We vragen nu ook de 'weather_code' op voor de iconen
        url = "https://open-meteo.com"
        r = requests.get(url, timeout=5)
        return r.json()["daily"] if r.status_code == 200 else None
    except: return None

def laad_dagpiek():
    vandaag = nu_lokaal.strftime('%Y-%m-%d')
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    parts = content.split(",")
                    if parts[0] == vandaag: return float(parts[1]), float(parts[2])
        except: pass
    return 0.0, 0.0

def sla_dagpiek_op(s, g):
    vandaag = nu_lokaal.strftime('%Y-%m-%d')
    with open(CACHE_FILE, "w") as f: f.write(f"{vandaag},{s},{g}")

# --- INITIALISEREN ---
if 'p_symo_peak' not in st.session_state:
    s_start, g_start = laad_dagpiek()
    st.session_state.p_symo_peak, st.session_state.p_galvo_peak = s_start, g_start

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

# --- DATA LADEN ---
historical_max = 3729.0
table_df = pd.DataFrame()
try:
    res = requests.get(CSV_URL, timeout=10)
    if res.status_code == 200:
        df = pd.read_csv(io.StringIO(res.text))
        historical_max = pd.to_numeric(df.iloc[:, 3], errors='coerce').max() if not df.empty else 3729.0
        table_df = df
except: pass

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

# --- WEER SECTIE (DYNAMISCH) ---
forecast = get_weather_forecast()
if forecast:
    desc_v, icon_v = get_weather_info(forecast['weather_code'][0])
    desc_m, icon_m = get_weather_info(forecast['weather_code'][1])
    
    st.markdown(f"### {icon_v} {desc_v} in Tongeren")
    
    w1, w2 = st.columns(2)
    with w1:
        st.metric("Vandaag", f"{forecast['temperature_2m_max'][0]}°C", f"{forecast['shortwave_radiation_sum'][0]} MJ/m² Zon")
    with w2:
        st.metric(f"Morgen {icon_m}", f"{forecast['temperature_2m_max'][1]}°C", f"{desc_m}")
else:
    st.error("Weergegevens niet beschikbaar")

st.divider()

st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
current_all_time = max(historical_max, val_t)
st.metric("🏆 All-time Record", f"{current_all_time:,.0f} W")

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

# --- TABEL ---
st.subheader("💚 Maandoverzicht") 
if not table_df.empty:
    st.table(table_df.iloc[::-1].head(15))

st.caption(f"Laatste update: {nu_lokaal.strftime('%H:%M:%S')}")
time.sleep(2)
st.rerun()
