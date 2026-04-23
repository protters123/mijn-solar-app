import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO v13.9 - MPPT UPDATE
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzl6V4knhaZnB7zgt5kvFkgTCph3Y-3S4KDHJEPzaaU1gqvTIfokzIiFUxDfhiBlIxW/exec"

PUBLIEK_IP = "94.110.235.108"
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_SYMO_MPPT = f"http://{PUBLIEK_IP}:8081/solar_api/v1/GetInverterRealtimeData.cgi?Scope=Device&DeviceId=1&DataCollection=CommonInverterData"

st.set_page_config(page_title="Solar Piek PRO", page_icon="⚡☀️⚡", layout="centered")

tz = pytz.timezone('Europe/Brussels')
nu = datetime.now(tz)
vandaag_iso = nu.strftime('%Y-%m-%d')

# --- INITIALISATIE ---
if 'initialized' not in st.session_state or st.session_state.huidige_datum != vandaag_iso:
    st.session_state.huidige_datum = vandaag_iso
    st.session_state.p_mppt1 = 0.0
    st.session_state.p_mppt2 = 0.0
    st.session_state.initialized = True

# --- DATA OPHALEN ---
def get_mppt_data():
    try:
        res = requests.get(URL_SYMO_MPPT, timeout=5).json()
        d = res['Body']['Data']
        p1 = d.get('UDC', {}).get('Value', 0) * d.get('IDC', {}).get('Value', 0)
        p2 = d.get('UDC_2', {}).get('Value', 0) * d.get('IDC_2', {}).get('Value', 0)
        return round(p1, 1), round(p2, 1)
    except:
        return 0.0, 0.0

st.session_state.p_mppt1, st.session_state.p_mppt2 = get_mppt_data()

# --- WEERGAVE OP HET SCHERM ---
st.title("⚡ Solar Piek PRO")

# Toon de MPPT waarden in twee kolommen
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("MPPT 1 (West)", f"{st.session_state.p_mppt1} W")
with col2:
    st.metric("MPPT 2 (Oost)", f"{st.session_state.p_mppt2} W")
with col3:
    totaal_dc = round(st.session_state.p_mppt1 + st.session_state.p_mppt2, 1)
    st.metric("Totaal Symo DC", f"{totaal_dc} W")

st.divider()

# ====================== DATA LADEN (Rest van je code) ======================
@st.cache_data(ttl=60)
def load_historical_data(url):
    try:
        return pd.read_csv(f"{url}&ts={int(time.time()/60)}", header=0, decimal=",")
    except: return None

df_raw = load_historical_data(CSV_URL)
# ... rest van je script ...
