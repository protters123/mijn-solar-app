import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO v13.9 - MONTH SORT UPDATE
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzl6V4knhaZnB7zgt5kvFkgTCph3Y-3S4KDHJEPzaaU1gqvTIfokzIiFUxDfhiBlIxW/exec"

PUBLIEK_IP = "94.110.235.108"
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"
# Nieuwe URL voor MPPT data van de Symo (DeviceId 1)
URL_SYMO_MPPT = f"http://{PUBLIEK_IP}:8081/solar_api/v1/GetInverterRealtimeData.cgi?Scope=Device&DeviceId=1&DataCollection=CommonInverterData"

st.set_page_config(page_title="Solar Piek PRO", page_icon="⚡☀️⚡", layout="centered")

tz = pytz.timezone('Europe/Brussels')
nu = datetime.now(tz)
vandaag_nl = nu.strftime('%d-%m-%Y')
huidige_maand_jaar = nu.strftime('%m-%Y') 
vandaag_iso = nu.strftime('%Y-%m-%d')

# --- INITIALISATIE ---
if 'initialized' not in st.session_state or st.session_state.huidige_datum != vandaag_iso:
    st.session_state.huidige_datum = vandaag_iso
    st.session_state.p_total_peak = 0.0
    st.session_state.p_symo_peak = 0.0
    st.session_state.p_galvo_peak = 0.0
    st.session_state.p_mppt1 = 0.0  # Extra state voor MPPT 1
    st.session_state.p_mppt2 = 0.0  # Extra state voor MPPT 2
    st.session_state.start_kwh_dag = None
    st.session_state.last_sync_time = "Nog geen sync"
    st.session_state.last_sheet_update = 0
    st.session_state.initialized = True

# Functie om MPPT data op te halen
def get_mppt_data():
    try:
        res = requests.get(URL_SYMO_MPPT, timeout=5).json()
        d = res['Body']['Data']
        # MPPT 1: Spanning * Stroom
        p1 = d.get('UDC', {}).get('Value', 0) * d.get('IDC', {}).get('Value', 0)
        # MPPT 2: Spanning * Stroom
        p2 = d.get('UDC_2', {}).get('Value', 0) * d.get('IDC_2', {}).get('Value', 0)
        return round(p1, 1), round(p2, 1)
    except:
        return 0.0, 0.0

# Aanroep voor MPPT waarden
st.session_state.p_mppt1, st.session_state.p_mppt2 = get_mppt_data()

# ====================== DATA LADEN ======================
@st.cache_data(ttl=60)
def load_historical_data(url):
    try:
        return pd.read_csv(f"{url}&ts={int(time.time()/60)}", header=0, decimal=",")
    except: return None

df_raw = load_historical_data(CSV_URL)
df_display = pd.DataFrame()
monthly_summary = pd.DataFrame()
stand_gisteren = None
all_time_peak_sheet = 3729.0

if df_raw is not None:
    try:
        df_full = df_raw.iloc[:, :7].copy()
        df_full.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWhdag', 'KWh']
