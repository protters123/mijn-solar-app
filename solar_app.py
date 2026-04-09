import streamlit as st
import requests
import time
import pandas as pd
import io
import os
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO + WEERSTATION ☀️🌦️
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbx5aBd074ppyMn-gj0OFY1JeU_WmhmM1m0WYvIiv_4RBTYmq-44BFdIVgi0nOZBf5Z8/exec" 

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek & Weer", page_icon="☀️", layout="centered")

# --- STYLING ---
st.markdown("""
    <style>
    @keyframes blinker { 50% { opacity: 0; } }
    .stroom-teken { animation: blinker 1.5s linear infinite; color: #FFD700; font-size: 1.5rem; margin-right: 5px; }
    .weather-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #ffaa00; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
vandaag_iso = nu_lokaal.strftime('%Y-%m-%d')
vandaag_nl = nu_lokaal.strftime('%d-%m-%Y')

# --- SMART WEATHER FUNCTION ---
@st.cache_data(ttl=900)
def get_weather_cached(date_str):
    try:
        url = "https://wttr.in/Borgloon?format=%t|%C|%h&m&lang=nl"
        r = requests.get(url, timeout=10)
        r.encoding = 'utf-8' 
        if r.status_code == 200 and "|" in r.text:
            parts = r.text.split('|')
            return parts[0].strip(), parts[1].strip(), f"💧 Vochtigheid: {parts[2].strip()}"
        return "14°C", "Licht Bewolkt", "💧 Vochtigheid: 65%"
    except Exception:
        return "N/A", "Weerdata niet bereikbaar", ""

# --- DATA FUNCTIES ---
def laad_geheugen_uit_sheet(df):
    """Haalt de piek van vandaag uit de ingeladen dataframe"""
    try:
        if not df.empty:
            # Zoek of vandaag al in de lijst staat
            vandaag_data = df[df['Datum'] == vandaag_nl]
            if not vandaag_data.empty:
                s = float(vandaag_data.iloc[-1]['Symo'])
                g = float(vandaag_data.iloc[-1]['Galvo'])
                t = float(vandaag_data.iloc[-1]['Totaal'])
                return s, g, t
    except: pass
    return 0.0, 0.0, 0.0

def sla_naar_sheets(s, g, t):
    """Stuurt data naar Google Apps Script met foutmelding op scherm"""
    try:
        payload = {"datum": vandaag_nl, "symo": s, "galvo": g, "totaal": t}
        r = requests.post(WEBAPP_URL, json=payload, timeout=10)
        if r.status_code != 200:
            st.error(f"Fout bij opslaan: HTTP {r.status_code}")
    except Exception as e:
        st.error(f"Verbindingsfout naar Sheets: {e}")

def fetch_fronius_data(url):
    try:
        r = requests.get(url, timeout=2).json()
        # Voeg round() toe om alleen hele getallen te krijgen
        power = round(abs(float(r.get('active_power_w', 0))))
        return power, "🟢"
    except:
        return 0.0, "🔴"

# --- DATA OPHALEN (HISTORIEK & PEAK) ---
historical_max = 3729.0
table_df = pd.DataFrame()
try:
    res = requests.get(CSV_URL, timeout=10)
    if res.status_code == 200:
        df = pd.read_csv(io.StringIO(res.text))
        if not df.empty:
            # Hernoem kolommen voor consistentie
            df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag'][:len(df.columns)]
            historical_max = pd.to_numeric(df['Totaal'], errors='coerce').max()
            table_df = df
except:
    st.warning("Kon historiek niet laden uit Google Sheets.")

# --- INITIALISATIE SESSION STATE ---
if 'p_total_peak' not in st.session_state:
    # Bij eerste run: laad piek van vandaag uit de sheet data
    s_p, g_p, t_p = laad_geheugen_uit_sheet(table_df)
    st.session_state.p_symo_peak = s_p
    st.session_state.p_galvo_peak = g_p
    st.session_state.p_total_peak = t_p

# --- LIVE DATA VERWERKING ---
val_s, icon_s = fetch_fronius_data(URL_1)
val_g, icon_g = fetch_fronius_data(URL_2)
val_t = val_s + val_g

# Update pieken als de huidige opbrengst hoger is
if val_t > st.session_state.p_total_peak:
    # Werk de pieken in de sessie bij
    st.session_state.p_total_peak = val_t
    st.session_state.p_symo_peak = max(val_s, st.session_state.p_symo_peak)
    st.session_state.p_galvo_peak = max(val_g, st.session_state.p_galvo_peak)
    
    # Sla het volledige pakket op (Symo + Galvo + Totaal)
    sla_naar_sheets(
        round(st.session_state.p_symo_peak), 
        round(st.session_state.p_galvo_peak), 
        round(st.session_state.p_total_peak)
    )

# --- UI DASHBOARD ---
st.title("☀️ Solar Dashboard")

temp, desc, hum = get_weather_cached(vandaag_iso)
st.markdown(f"""
    <div class="weather-card">
        <h4 style='margin:0;'>Lokaal Weer (Borgloon)</h4>
        <span style='font-size: 1.2rem;'><b>{temp}</b> | {desc} | {hum}</span>
    </div>
""", unsafe_allow_html=True)

st.write(f"⏰ {nu_lokaal.strftime('%H:%M')} | {vandaag_nl}")
st.markdown(f"## Live: <span class='stroom-teken'>⚡</span> {val_t:,.0f} W", unsafe_allow_html=True)

st.metric("🏆 All-time Record", f"{max(historical_max, st.session_state.p_total_peak):,.0f} W")
st.divider()

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"### {icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
    st.metric("Piek", f"{st.session_state.p_symo_peak:,.0f} W")
with c2:
    st.markdown("### 📊 Dag")
    st.metric("Piek", f"{st.session_state.p_total_peak:,.0f} W")
with c3:
    st.markdown(f"### {icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")
    st.metric("Piek", f"{st.session_state.p_galvo_peak:,.0f} W")

st.divider()
st.subheader("📅 Historiek") 
if not table_df.empty:
    st.dataframe(table_df.iloc[::-1], use_container_width=True, height=250)

# Ververs elke 5 seconden (Streamlit Cloud is trager dan lokaal)
time.sleep(5)
st.rerun()
