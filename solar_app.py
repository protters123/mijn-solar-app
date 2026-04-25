import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO v14.1 - REALTIME UPDATE
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzl6V4knhaZnB7zgt5kvFkgTCph3Y-3S4KDHJEPzaaU1gqvTIfokzIiFUxDfhiBlIxW/exec"

PUBLIEK_IP = "94.110.235.108"
URL_1 = f"http://{PUBLIEK_IP}:8080/api/v1/data" 
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek PRO", page_icon="⚡☀️⚡", layout="centered")

tz = pytz.timezone('Europe/Brussels')

# --- INITIALISATIE ---
if 'initialized' not in st.session_state:
    st.session_state.p_total_peak = 0.0
    st.session_state.p_symo_peak = 0.0
    st.session_state.p_galvo_peak = 0.0
    st.session_state.start_kwh_dag = None
    st.session_state.last_sync_time = "Nog geen sync"
    st.session_state.last_sheet_update = 0
    st.session_state.initialized = True

# ====================== FUNCTIES ======================
@st.cache_data(ttl=60)
def load_historical_data(url):
    try:
        return pd.read_csv(f"{url}&ts={int(time.time()/60)}", header=0, decimal=",")
    except: return None

def fetch_hw_data(url):
    try:
        r = requests.get(url, timeout=2.0).json()
        power = round(abs(float(r.get('active_power_w', 0))))
        kwh = float(r.get('total_power_export_kwh') or 0)
        if kwh == 0:
            kwh = (float(r.get('total_power_export_t1_kwh') or 0) + 
                   float(r.get('total_power_export_t2_kwh') or 0))
        return (power if power >= 5 else 0), kwh, "🟢"
    except: return 0, 0, "🔴"

def sla_naar_sheets(datum, s_peak, g_peak, t_peak, oogst, start_kwh, kwh_nu):
    nu_ts = time.time()
    if (nu_ts - st.session_state.last_sheet_update > 30):
        try:
            payload = {"datum": datum, "symo": int(s_peak), "galvo": int(g_peak), "totaal": int(t_peak), 
                       "oogst": float(oogst), "start_kwh": float(start_kwh), "kwh_nu": float(kwh_nu), "actie": "update"}
            requests.post(WEBAPP_URL, json=payload, timeout=5)
            st.session_state.last_sheet_update = nu_ts
            st.session_state.last_sync_time = datetime.now(tz).strftime('%H:%M:%S')
        except: pass

@st.cache_data(ttl=3600)
def get_weather_data():
    try:
        r = requests.get("https://wttr.in|%C|%h&lang=nl", timeout=5)
        p = r.text.strip().split('|')
        return p[0], p[1], p[2]
    except: return "12°C", "Helder", "80%"

# ====================== UI & LOOP ======================
st.title("⚡☀️⚡ Solar Piek PRO")

# Weerstatistieken (verversen minder vaak)
w_temp, w_cond, w_hum = get_weather_data()
cw1, cw2, cw3 = st.columns(3)
cw1.metric("🌡️ Temp", w_temp)
cw2.metric("☁️ Lucht", w_cond)
cw3.metric("💧 Vocht", w_hum)

st.divider()

# Dit fragment ververst elke seconde
@st.fragment(run_every=1)
def update_live_data():
    nu = datetime.now(tz)
    vandaag_nl = nu.strftime('%d-%m-%Y')
    
    val_s, kwh_s, dot_s = fetch_hw_data(URL_1)
    val_g, kwh_g, dot_g = fetch_hw_data(URL_2)
    val_t, kwh_nu = val_s + val_g, kwh_s + kwh_g

    # Startwaarde bepalen
    if st.session_state.start_kwh_dag is None or st.session_state.start_kwh_dag == 0:
        st.session_state.start_kwh_dag = kwh_nu

    oogst_vandaag = round(max(0.0, kwh_nu - st.session_state.start_kwh_dag), 1)
    
    # Peaks bijwerken
    st.session_state.p_symo_peak = max(st.session_state.p_symo_peak, val_s)
    st.session_state.p_galvo_peak = max(st.session_state.p_galvo_peak, val_g)
    st.session_state.p_total_peak = max(st.session_state.p_total_peak, val_t)

    # UI Elementen
    st.markdown(f"<h1 style='text-align:center;color:#FFB300; font-size: 60px;'>⚡ {val_t:,.0f} Watt</h1>", unsafe_allow_html=True)
    st.progress(min(val_t / 8000, 1.0))
    st.caption(f"⏱️ Realtime update elke seconde | Sync: {st.session_state.last_sync_time}")

    c_oogst, c_peak = st.columns(2)
    c_oogst.metric("⚡ Oogst vandaag", f"{oogst_vandaag:.1f} kWh")
    c_peak.metric("🏆 Dag Piek", f"{st.session_state.p_total_peak:,.0f} W")

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric(f"{dot_s} Symo", f"{val_s} W", f"Piek: {st.session_state.p_symo_peak:,.0f} W")
    c2.metric(f"{dot_g} Galvo", f"{val_g} W", f"Piek: {st.session_state.p_galvo_peak:,.0f} W")
    c3.metric("☀️ Totaal", f"{val_t} W")

    # Data opslaan
    if kwh_nu > 0:
        sla_naar_sheets(vandaag_nl, st.session_state.p_symo_peak, st.session_state.p_galvo_peak, st.session_state.p_total_peak, oogst_vandaag, st.session_state.start_kwh_dag, kwh_nu)

update_live_data()

# Historiek buiten het fragment (hoeft niet elke seconde)
with st.expander("☀️⚡ Maandoverzicht & Historiek"):
    df_raw = load_historical_data(CSV_URL)
    if df_raw is not None:
        st.dataframe(df_raw.tail(10), use_container_width=True)
