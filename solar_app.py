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
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
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
    mapping = {
        0: ("Onbewolkt", "☀️"), 1: ("Licht bewolkt", "🌤️"), 2: ("Half bewolkt", "⛅"), 3: ("Bewolkt", "☁️"),
        45: ("Mistig", "🌫️"), 48: ("Rijpende mist", "🌫️"),
        51: ("Lichte motregen", "🌦️"), 53: ("Matige motregen", "🌦️"), 55: ("Dichte motregen", "🌦️"),
        61: ("Lichte regen", "🌧️"), 63: ("Matige regen", "🌧️"), 65: ("Zware regen", "🌧️"),
        71: ("Lichte sneeuwval", "❄️"), 80: ("Lichte regenbuien", "🌦️"),
        95: ("Onweer", "⚡"), 96: ("Onweer met hagel", "⛈️")
    }
    return mapping.get(code, ("Onbekend", "🌡️"))

@st.cache_data(ttl=3600)
def get_weather_forecast(lat=50.78, lon=5.41):
    try:
        url = f"https://open-meteo.com{lat}&longitude={lon}&daily=weather_code,temperature_2m_max,shortwave_radiation_sum&timezone=Europe%2FBerlin"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()["daily"]
        return None
    except: return None

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
historical_max = 3729.0
table_df = pd.DataFrame()
try:
    res = requests.get(CSV_URL, timeout=10)
    if res.status_code == 200:
        df = pd.read_csv(io.StringIO(res.text))
        if not df.empty:
            historical_max = pd.to_numeric(df.iloc[:, 3], errors='coerce').max()
            table_df = df
except: pass

# --- LIVE DATA OPHALEN ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# Update Dagpieken
update_cache = False
if val_s > st.session_state.p_symo_peak:
    st.session_state.p_symo_peak = val_s
    update_cache = True
if val_g > st.session_state.p_galvo_peak:
    st.session_state.p_galvo_peak = val_g
    update_cache = True
if update_cache:
    sla_dagpiek_op(st.session_state.p_symo_peak, st.session_state.p_galvo_peak)

# --- UI DASHBOARD ---
st.title("☀️ Solar Piek Pro") 

# --- WEER APP SECTIE (BOVENAAN) ---
forecast = get_weather_forecast()
if forecast:
    # We halen specifiek de data van vandaag op (index 0)
    weer_tekst, weer_icoon = get_weather_info(forecast['weather_code'][0])
    
    st.info(f"**Weer in Tongeren:** {weer_icoon} {weer_tekst} | 🌡️ {forecast['temperature_2m_max'][0]}°C | ☀️ {forecast['shortwave_radiation_sum'][0]} MJ/m²")
    
    if forecast['shortwave_radiation_sum'][0] > 20:
        st.warning("🚀 **RECORDWEER GEALERTEERD:** Extreem veel zonnestraling vandaag!")
else:
    st.error("Weergegevens konden niet worden opgehaald.")

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

# --- TABEL SECTIE ---
st.subheader("💚 Maandoverzicht") 
if not table_df.empty:
    st.table(table_df.iloc[::-1].head(15))

st.caption(f"Update: {nu_lokaal.strftime('%H:%M:%S')} | Locatie: Tongeren-Borgloon")
time.sleep(2)
st.rerun()
