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
# Pas deze WEBAPP_URL aan naar de URL van je Google Apps Script
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxwClGZryn1ZbtLWqAQs5LF98WVm0ANb5rOyjgbYG9xQXHEjfgWG5RUbfXGXf8B4Xbb/exec" 

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek", page_icon="☀️", layout="centered")

# --- TIJDZONE & GEHEUGEN ---
tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
CACHE_FILE = "dagpiek_geheugen.txt"
ARCHIVE_LOG = "laatst_gearchiveerd.txt"

# --- WEER INTERPRETATIE ---
def vertaal_weer(code):
    mapping = {
        0: ("Onbewolkt", "☀️"), 1: ("Licht bewolkt", "🌤️"), 2: ("Half bewolkt", "⛅"), 
        3: ("Bewolkt", "☁️"), 45: ("Mistig", "🌫️"), 51: ("Lichte regen", "🌧️"),
        61: ("Regen", "🌧️"), 80: ("Regenbuien", "🌧️"), 95: ("Onweer", "⛈️")
    }
    return mapping.get(code, ("Variabel", "🌡️"))

@st.cache_data(ttl=3600)
def get_weather_forecast():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=50.7805&longitude=5.4648&daily=weather_code,temperature_2m_max,shortwave_radiation_sum&timezone=Europe%2FBerlin&forecast_days=1"
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
    st.session_state.p_symo_peak, st.session_state.p_galvo_peak = s_start, g_start

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

# --- LIVE DATA OPHALEN ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# Update Dagpieken
if val_s > st.session_state.p_symo_peak or val_g > st.session_state.p_galvo_peak:
    st.session_state.p_symo_peak = max(val_s, st.session_state.p_symo_peak)
    st.session_state.p_galvo_peak = max(val_g, st.session_state.p_galvo_peak)
    sla_dagpiek_op(st.session_state.p_symo_peak, st.session_state.p_galvo_peak)

# --- AUTO-ARCHIVEREN OM 23:00 ---
# --- AUTO-ARCHIVEREN OM 23:00 ---
vandaag = nu_lokaal.strftime('%Y-%m-%d')

# De check op 23:00 uur lokale tijd
if nu_lokaal.hour == 23:
    laatst_datum = ""
    if os.path.exists(ARCHIVE_LOG):
        try:
            with open(ARCHIVE_LOG, "r") as f: laatst_datum = f.read().strip()
        except: pass
    
    # Alleen archiveren als we dat vandaag nog niet gedaan hebben
    if laatst_datum != vandaag:
        params = {
            "symo": int(st.session_state.p_symo_peak), 
            "galvo": int(st.session_state.p_galvo_peak)
        }
        try:
            r = requests.get(WEBAPP_URL, params=params, timeout=15)
            if r.status_code == 200:
                with open(ARCHIVE_LOG, "w") as f: f.write(vandaag)
                st.toast("🚀 Dagpiek automatisch gearchiveerd!")
        except: pass


# --- UI DASHBOARD ---
st.title("☀️ Solar Piek") 

forecast = get_weather_forecast()
if forecast:
    w_tekst, w_icoon = vertaal_weer(forecast['weather_code'][0])
    t_max = forecast['temperature_2m_max'][0]
    z_straling = forecast['shortwave_radiation_sum'][0]
    st.info(f"**Weerbericht Tongeren:** {w_icoon} {w_tekst} | 🌡️ {t_max}°C | ☀️ {z_straling} MJ/m²")

st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")

# --- DATA LADEN UIT SHEET ---
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
if not table_df.empty:
    st.table(table_df.iloc[::-1].head(15))

st.caption(f"Update: {nu_lokaal.strftime('%H:%M:%S')} | Locatie: Tongeren-Borgloon")
time.sleep(2)
st.rerun()
