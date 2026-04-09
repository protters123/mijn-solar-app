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
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbwcyMXGSjPmp-UMoLBwtVmlTDt4DkwxgybwFa6XhkKu6Xi5etot-9tsD5ELEhT9AaOG/exec" 

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
def sla_naar_sheets(s, g, t, oogst):
    """Verzendt de pieken en de dagopbrengst naar Google Sheets"""
    try:
        payload = {"datum": vandaag_nl, "symo": s, "galvo": g, "totaal": t, "oogst": oogst}
        r = requests.post(WEBAPP_URL, json=payload, timeout=10)
        return r.status_code == 200
    except:
        return False

def fetch_hw_data(url):
    """Haalt wattage en dag-energie op van HomeWizard meter"""
    try:
        r = requests.get(url, timeout=2).json()
        power = round(abs(float(r.get('active_power_w', 0))))
        kwh_totaal = float(r.get('total_power_export_t1_kwh', 0)) + float(r.get('total_power_export_t2_kwh', 0))
        return power, kwh_totaal, "🟢"
    except:
        return 0, 0.0, "🔴"

def laad_geheugen_uit_sheet():
    try:
        res = requests.get(CSV_URL, timeout=10)
        if res.status_code == 200:
            df = pd.read_csv(io.StringIO(res.text))
            df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst'][:len(df.columns)]
            vandaag_data = df[df['Datum'] == vandaag_nl]
            if not vandaag_data.empty:
                return (
                    float(vandaag_data['Symo'].max()), 
                    float(vandaag_data['Galvo'].max()), 
                    float(vandaag_data['Totaal'].max())
                )
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

# --- DATA OPHALEN VOOR HISTORIEK ---
historical_max = 3729.0
table_df = pd.DataFrame()
try:
    res = requests.get(CSV_URL, timeout=5)
    if res.status_code == 200:
        table_df = pd.read_csv(io.StringIO(res.text))
        table_df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag'][:len(table_df.columns)]
        historical_max = pd.to_numeric(table_df['Totaal'], errors='coerce').max()
except: pass

# --- INITIALISATIE & RESET LOGICA ---
if 'huidige_datum' not in st.session_state:
    st.session_state.huidige_datum = vandaag_iso

if st.session_state.huidige_datum != vandaag_iso:
    st.session_state.p_symo_peak = 0.0
    st.session_state.p_galvo_peak = 0.0
    st.session_state.p_total_peak = 0.0
    st.session_state.start_kwh_dag = None
    st.session_state.huidige_datum = vandaag_iso
    st.rerun()

if 'p_total_peak' not in st.session_state or st.session_state.p_total_peak == 0:
    s_p, g_p, t_p = laad_geheugen_uit_sheet()
    st.session_state.p_symo_peak, st.session_state.p_galvo_peak, st.session_state.p_total_peak = s_p, g_p, t_p

# --- LIVE DATA VERWERKING ---
val_s, kwh_s, icon_s = fetch_hw_data(URL_1)
val_g, kwh_g, icon_g = fetch_hw_data(URL_2)
val_t = val_s + val_g

if 'start_kwh_dag' not in st.session_state or st.session_state.start_kwh_dag is None:
    st.session_state.start_kwh_dag = kwh_s + kwh_g

oogst_vandaag = round((kwh_s + kwh_g) - st.session_state.start_kwh_dag, 2)

if val_t > st.session_state.p_total_peak:
    st.session_state.p_total_peak = val_t
    st.session_state.p_symo_peak = max(val_s, st.session_state.p_symo_peak)
    st.session_state.p_galvo_peak = max(val_g, st.session_state.p_galvo_peak)

# --- AVOND OPSLAG LOGICA ---
huidige_tijd = nu_lokaal.strftime("%H:%M")
if huidige_tijd >= "23:00" and st.session_state.get('laatste_opslag_datum') != vandaag_iso:
    if st.session_state.p_total_peak > 0:
        if sla_naar_sheets(st.session_state.p_symo_peak, st.session_state.p_galvo_peak, st.session_state.p_total_peak, oogst_vandaag):
            st.session_state.laatste_opslag_datum = vandaag_iso
            st.toast("✅ Dagtotalen opgeslagen!", icon="💾")

# --- UI DASHBOARD ---
st.title("☀️ Solar Dashboard")
temp, desc, hum = get_weather_cached(vandaag_iso)
st.markdown(f'<div style="background:#f0f2f6;padding:15px;border-radius:10px;border-left:5px solid #ffaa00;margin-bottom:20px;"><b>{temp}</b> | {desc} | {hum}</div>', unsafe_allow_html=True)

st.write(f"⏰ {nu_lokaal.strftime('%H:%M')} | {vandaag_nl}")
st.markdown(f"## Live: ⚡ {val_t:,.0f} W")
st.markdown(f"### Oogst vandaag: 📈 {oogst_vandaag} kWh")

st.metric("🏆 All-time Record", f"{max(historical_max, st.session_state.p_total_peak):,.0f} W")
st.divider()

# Aangepaste volgorde: Symo | Galvo | Totaal
c1, c2, c3 = st.columns(3)
with c1:
    st.metric(f"{icon_s} Symo", f"{val_s} W", f"Piek: {st.session_state.p_symo_peak} W")
with c2:
    st.metric(f"{icon_g} Galvo", f"{val_g} W", f"Piek: {st.session_state.p_galvo_peak} W")
with c3:
    st.metric("📊 Totaal", f"{val_t} W", f"Piek: {st.session_state.p_total_peak} W")

st.divider()
st.subheader("☀️ Historiek") 
if not table_df.empty:
    st.dataframe(table_df.iloc[::-1], use_container_width=True, height=250)

if st.button("💾 Sla nu op (Back-up)"):
    if sla_naar_sheets(st.session_state.p_symo_peak, st.session_state.p_galvo_peak, st.session_state.p_total_peak, oogst_vandaag):
        st.success(f"Opgeslagen! Oogst: {oogst_vandaag} kWh")
        time.sleep(1)
        st.rerun()

time.sleep(5)
st.rerun()
