import streamlit as st
import requests
import time
import pandas as pd
import io
import os
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO - VOLLEDIGE VERSIE ⚡🌦️
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

# Jouw werkende Google Script URL
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbyIBhDGzmQQvokyzBjYT0Nt8qiRFKtElxMCrhelxfPOLNF2NNbAgOP3PAGTSEQEsMmq/exec" 

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek", page_icon="☀️", layout="centered")

# --- CSS VOOR ANIMATIE ---
st.markdown("""
    <style>
    @keyframes blinker {
        50% { opacity: 0; }
    }
    .stroom-teken {
        animation: blinker 1.5s linear infinite;
        color: #FFD700;
        font-size: 1.5rem;
        margin-right: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# --- TIJDZONE & GEHEUGEN ---
tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
vandaag_iso = nu_lokaal.strftime('%Y-%m-%d')
vandaag_nl = nu_lokaal.strftime('%d-%m-%Y')

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
        url = "https://open-meteo.com"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()["daily"]
        return None
    except:
        return None

def laad_dagpiek():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    parts = content.split(",")
                    if parts[0] == vandaag_iso:
                        return float(parts[1]), float(parts[2])
        except: pass
    return 0.0, 0.0

def sla_dagpiek_op(s, g):
    with open(CACHE_FILE, "w") as f:
        f.write(f"{vandaag_iso},{s},{g}")

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

# --- AUTO-ARCHIVEREN OM 20:30 ---
target_uur = 20
target_min = 30

if nu_lokaal.hour == target_uur and nu_lokaal.minute == target_min:
    laatst_datum = ""
    if os.path.exists(ARCHIVE_LOG):
        try:
            with open(ARCHIVE_LOG, "r") as f: laatst_datum = f.read().strip()
        except: pass
    
    if laatst_datum != vandaag_iso:
        params = {"symo": int(st.session_state.p_symo_peak), "galvo": int(st.session_state.p_galvo_peak)}
        try:
            r = requests.get(WEBAPP_URL, params=params, timeout=15)
            if r.status_code == 200:
                with open(ARCHIVE_LOG, "w") as f: f.write(vandaag_iso)
                st.balloons()
                st.toast("🚀 Dagpiek gearchiveerd!")
        except: pass

# --- UI DASHBOARD ---
st.title("☀️ Solar Piek") 
st.write(f"⏰ App-tijd: {nu_lokaal.strftime('%H:%M')} ({vandaag_nl})")

# Weerbericht ophalen en verwerken
forecast = get_weather_forecast()
if forecast:
    # We pakken de eerste dag [0] uit de resultaten
    w_tekst, w_icoon = vertaal_weer(forecast['weather_code'][0])
    t_max = forecast['temperature_2m_max'][0]
    z_straling = forecast['shortwave_radiation_sum'][0]
    
    st.info(f"**Weerbericht Tongeren:** {w_icoon} {w_tekst} | 🌡️ {t_max}°C | ☀️ {z_straling} MJ/m²")

# De rest van je dashboard (Totaal Live met bliksem, etc.)
st.markdown(f"### 📊 Totaal Live: <span class='stroom-teken'>⚡</span> {val_t:,.0f} W", unsafe_allow_html=True)

# Geanimeerd bliksemteken voor Totaal Live
st.markdown(f"### 📊 Totaal Live: <span class='stroom-teken'>⚡</span> {val_t:,.0f} W", unsafe_allow_html=True)

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
