import streamlit as st
import requests
import time
import pandas as pd
import io
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO + WEERSTATION ☀️🌦️
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbwqIAlRlPVEIEh5qP48xVbzW36rJA1f1EQPCcoqce5O2D7R_qhrT83F1mHt2AHpS5_1/exec" 

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek & Weer", page_icon="☀️", layout="centered")

# --- TIJD & DATUM ---
tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
vandaag_iso = nu_lokaal.strftime('%Y-%m-%d')
vandaag_nl = nu_lokaal.strftime('%d-%m-%Y')

# --- DATA FUNCTIES ---
def sla_naar_sheets(s, g, t):
    """Stuurt data naar Google Apps Script"""
    try:
        payload = {"datum": vandaag_nl, "symo": s, "galvo": g, "totaal": t}
        r = requests.post(WEBAPP_URL, json=payload, timeout=10)
        return r.status_code == 200
    except:
        return False

def fetch_fronius_data(url):
    try:
        r = requests.get(url, timeout=2).json()
        power = round(abs(float(r.get('active_power_w', 0))))
        return power, "🟢"
    except:
        return 0, "🔴"

def laad_geheugen_uit_sheet(df):
    try:
        if not df.empty:
            vandaag_data = df[df['Datum'] == vandaag_nl]
            if not vandaag_data.empty:
                s = float(vandaag_data.iloc[-1]['Symo'])
                g = float(vandaag_data.iloc[-1]['Galvo'])
                t = float(vandaag_data.iloc[-1]['Totaal'])
                return s, g, t
    except: pass
    return 0.0, 0.0, 0.0

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
    except:
        return "N/A", "Weerdata niet bereikbaar", ""

# --- DATA OPHALEN UIT SHEET ---
historical_max = 3729.0
table_df = pd.DataFrame()
try:
    res = requests.get(CSV_URL, timeout=10)
    if res.status_code == 200:
        df = pd.read_csv(io.StringIO(res.text))
        if not df.empty:
            df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag'][:len(df.columns)]
            historical_max = pd.to_numeric(df['Totaal'], errors='coerce').max()
            table_df = df
except: pass

# --- INITIALISATIE SESSION STATE ---
if 'p_total_peak' not in st.session_state:
    s_p, g_p, t_p = laad_geheugen_uit_sheet(table_df)
    st.session_state.p_symo_peak = s_p
    st.session_state.p_galvo_peak = g_p
    st.session_state.p_total_peak = t_p
    st.session_state.laatste_opslag_datum = ""

# --- LIVE DATA VERWERKING ---
val_s, icon_s = fetch_fronius_data(URL_1)
val_g, icon_g = fetch_fronius_data(URL_2)
val_t = val_s + val_g

# Update pieken in geheugen
if val_t > st.session_state.p_total_peak:
    st.session_state.p_total_peak = val_t
    st.session_state.p_symo_peak = max(val_s, st.session_state.p_symo_peak)
    st.session_state.p_galvo_peak = max(val_g, st.session_state.p_galvo_peak)

# --- OPSLAG LOGICA (23:00) ---
huidige_tijd = nu_lokaal.strftime("%H:%M")
if huidige_tijd >= "23:00" and st.session_state.laatste_opslag_datum != vandaag_iso:
    if sla_naar_sheets(round(st.session_state.p_symo_peak), round(st.session_state.p_galvo_peak), round(st.session_state.p_total_peak)):
        st.session_state.laatste_opslag_datum = vandaag_iso
        st.toast("✅ Dagtotalen opgeslagen!", icon="💾")

# --- UI DASHBOARD ---
st.title("☀️ Solar Dashboard")

temp, desc, hum = get_weather_cached(vandaag_iso)
st.markdown(f'<div style="background:#f0f2f6;padding:15px;border-radius:10px;border-left:5px solid #ffaa00;margin-bottom:20px;">'
            f'<h4 style="margin:0;">Lokaal Weer (Borgloon)</h4>'
            f'<span><b>{temp}</b> | {desc} | {hum}</span></div>', unsafe_allow_html=True)

st.write(f"⏰ {nu_lokaal.strftime('%H:%M')} | {vandaag_nl}")
st.markdown(f"## Live: ⚡ {val_t:,.0f} W")

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

time.sleep(2)
st.rerun()
