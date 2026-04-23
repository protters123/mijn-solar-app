import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
import pytz

# Probeer autorefresh voor de 2-seconden update
try:
    from streamlit_autorefresh import st_autorefresh
except:
    st_autorefresh = None

# ==========================================
# SOLAR PIEK PRO v14.8 - STABILITY & TABLE FIX
# ==========================================

# Activeer de 2-seconden refresh voor de UI
if st_autorefresh:
    st_autorefresh(interval=2000, key="solar_refresh")

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
PUBLIEK_IP = "94.110.235.108"
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"
URL_SYMO_MPPT = f"http://{PUBLIEK_IP}:8081/solar_api/v1/GetInverterRealtimeData.cgi?Scope=Device&DeviceId=2&DataCollection=CommonInverterData"

st.set_page_config(page_title="Solar Piek PRO", page_icon="⚡☀️⚡", layout="centered")

tz = pytz.timezone('Europe/Brussels')
nu = datetime.now(tz)
vandaag_nl = nu.strftime('%d-%m-%Y')
huidige_maand_jaar = nu.strftime('%m-%Y') 
vandaag_iso = nu.strftime('%Y-%m-%d')

# --- INITIALISATIE ---
if 'initialized' not in st.session_state or st.session_state.huidige_datum != vandaag_iso:
    st.session_state.huidige_datum = vandaag_iso
    st.session_state.p_mppt1, st.session_state.p_mppt2 = 0.0, 0.0
    st.session_state.initialized = True

# ====================== DATA FUNCTIES ======================

@st.cache_data(ttl=60)
def load_historical_data(url):
    try:
        df = pd.read_csv(f"{url}&ts={int(time.time()/60)}", header=0, decimal=",")
        df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWhdag', 'KWhdag']
        df['temp_date'] = pd.to_datetime(df['Datum'], dayfirst=True, errors='coerce')
        df['Maand'] = df['temp_date'].dt.strftime('%m-%Y')
        df['Oogst/dag'] = pd.to_numeric(df['Oogst/dag'].astype(str).str.replace(',', '.'), errors='coerce')
        return df
    except: return None

def fetch_hw_data(url):
    try:
        r = requests.get(url, timeout=0.8).json()
        power = round(abs(float(r.get('active_power_w', 0))))
        kwh = float(r.get('total_power_export_kwh', 0))
        return (power if power >= 10 else 0), kwh, "🟢"
    except: return 0, 0, "🔴"

@st.cache_data(ttl=10) # Ontlast de omvormer door MPPT 10 sec te onthouden
def fetch_mppt_data_cached(url):
    try:
        r = requests.get(url, timeout=1.2).json()
        d = r['Body']['Data']
        u1 = d.get('UDC', {}).get('Value') or d.get('UDC_1', {}).get('Value', 0)
        i1 = d.get('IDC', {}).get('Value') or d.get('IDC_1', {}).get('Value', 0)
        u2 = d.get('UDC_2', {}).get('Value', 0)
        i2 = d.get('IDC_2', {}).get('Value', 0)
        return round(u1 * i1, 0), round(u2 * i2, 0)
    except: return 0.0, 0.0

# ====================== LIVE DATA OPHALEN ======================
val_s, kwh_s, dot_s = fetch_hw_data(URL_1)
val_g, kwh_g, dot_g = fetch_hw_data(URL_2)
val_t = val_s + val_g

# Gebruik de gecachte MPPT functie
st.session_state.p_mppt1, st.session_state.p_mppt2 = fetch_mppt_data_cached(URL_SYMO_MPPT)

# Historiek laden
df_raw = load_historical_data(CSV_URL)

# ====================== UI ======================
st.title("⚡ Solar Piek PRO")

st.markdown(f"<h1 style='text-align:center;color:#FFB300; font-size: 55px;'>⚡ {val_t:,.0f} Watt</h1>", unsafe_allow_html=True)
st.progress(min(val_t / 8000, 1.0))
st.caption(f"🔄 Update: {datetime.now(tz).strftime('%H:%M:%S')} | Symo: {dot_s} Galvo: {dot_g}")

st.divider()
st.subheader("Symo Live DC Details")
m1, m2, m3 = st.columns(3)
m1.metric("MPPT 1 (West)", f"{st.session_state.p_mppt1:.0f} W")
m2.metric("MPPT 2 (Oost)", f"{st.session_state.p_mppt2:.0f} W")
m3.metric("Totaal DC", f"{st.session_state.p_mppt1 + st.session_state.p_mppt2:.0f} W")

with st.expander("☀️ Historiek & Maandoverzicht", expanded=True):
    if df_raw is not None:
        # Maandtotalen
        st.subheader("Maandtotalen")
        monthly = df_raw.groupby('Maand')['Oogst/dag'].sum().reset_index()
        monthly['temp_sort'] = pd.to_datetime(monthly['Maand'], format='%m-%Y')
        monthly = monthly.sort_values('temp_sort', ascending=False).drop(columns=['temp_sort'])
        st.dataframe(monthly.round(1), hide_index=True, use_container_width=True)
        
        st.divider()
        
        # Dagen huidige maand
        st.subheader(f"Dagen in {huidige_maand_jaar}")
        df_display = df_raw[df_raw['Maand'] == huidige_maand_jaar].sort_values('temp_date', ascending=False)
        st.dataframe(df_display.drop(columns=['temp_date', 'Maand']), hide_index=True, use_container_width=True)
    else:
        st.error("Kon geen historische data laden uit Google Sheets.")
