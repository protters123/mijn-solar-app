import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
import pytz

# Probeer autorefresh voor de live ervaring (elke 2 seconden)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=2000, key="solar_refresh")
except:
    pass

# ==========================================
# SOLAR PIEK PRO v14.9 - MPPT & LIVE REFRESH
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzl6V4knhaZnB7zgt5kvFkgTCph3Y-3S4KDHJEPzaaU1gqvTIfokzIiFUxDfhiBlIxW/exec"

PUBLIEK_IP = "94.110.235.108"
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

# CORRECTE URL: toegevoegd .cgi en DeviceId=2
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
    st.session_state.p_total_peak = 0.0
    st.session_state.p_mppt1, st.session_state.p_mppt2 = 0.0, 0.0
    st.session_state.last_sync_time = "Nog geen sync"
    st.session_state.last_sheet_update = 0
    st.session_state.initialized = True

# ====================== DATA FUNCTIES ======================

@st.cache_data(ttl=60)
def load_historical_data(url):
    try:
        df = pd.read_csv(f"{url}&ts={int(time.time()/60)}", header=0, decimal=",")
        df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWhdag', 'KWhdag']
        return df
    except: return None

def fetch_hw_data(url):
    try:
        r = requests.get(url, timeout=1.2).json()
        power = round(abs(float(r.get('active_power_w', 0))))
        kwh = float(r.get('total_power_export_kwh', 0))
        return (power if power >= 10 else 0), kwh, "🟢"
    except: return 0, 0, "🔴"

def fetch_mppt_live(url):
    try:
        r = requests.get(url, timeout=1.8).json()
        d = r['Body']['Data']
        # Check op beide mogelijke veldnamen voor stroom en spanning
        u1 = d.get('UDC', {}).get('Value') or d.get('UDC_1', {}).get('Value', 0)
        i1 = d.get('IDC', {}).get('Value') or d.get('IDC_1', {}).get('Value', 0)
        u2 = d.get('UDC_2', {}).get('Value', 0)
        i2 = d.get('IDC_2', {}).get('Value', 0)
        return round(u1 * i1, 0), round(u2 * i2, 0)
    except:
        return 0.0, 0.0

# ====================== LIVE DATA OPHALEN ======================
val_s, kwh_s, dot_s = fetch_hw_data(URL_1)
val_g, kwh_g, dot_g = fetch_hw_data(URL_2)
val_t = val_s + val_g
kwh_nu = kwh_s + kwh_g

# Haal de DC wattages op via de .cgi API
st.session_state.p_mppt1, st.session_state.p_mppt2 = fetch_mppt_live(URL_SYMO_MPPT)

# Historiek laden
df_raw = load_historical_data(CSV_URL)
monthly_summary, df_display = pd.DataFrame(), pd.DataFrame()
all_time_peak_sheet = 3729.0

if df_raw is not None:
    try:
        df_raw['temp_date'] = pd.to_datetime(df_raw['Datum'], dayfirst=True, errors='coerce')
        df_raw['Maand'] = df_raw['temp_date'].dt.strftime('%m-%Y')
        df_raw['Oogst/dag'] = pd.to_numeric(df_raw['Oogst/dag'].astype(str).str.replace(',', '.'), errors='coerce')
        
        # Maandtotalen
        monthly_summary = df_raw.groupby('Maand')['Oogst/dag'].sum().reset_index()
        monthly_summary['temp_sort'] = pd.to_datetime(monthly_summary['Maand'], format='%m-%Y')
        monthly_summary = monthly_summary.sort_values('temp_sort', ascending=False).drop(columns=['temp_sort'])
        
        # Tabel deze maand
        df_display = df_raw[df_raw['Maand'] == huidige_maand_jaar].sort_values('temp_date', ascending=False)
        all_time_peak_sheet = pd.to_numeric(df_raw['Totaal'], errors='coerce').max() or 3729.0
    except: pass

st.session_state.p_total_peak = max(st.session_state.p_total_peak, val_t)

# ====================== UI WEERGAVE ======================
st.title("⚡ Solar Piek PRO")

st.markdown(f"<h1 style='text-align:center;color:#FFB300; font-size: 55px;'>⚡ {val_t:,.0f} Watt</h1>", unsafe_allow_html=True)
st.progress(min(val_t / 8000, 1.0))
st.caption(f"🔄 Laatste update: {datetime.now(tz).strftime('%H:%M:%S')} | Symo: {dot_s} Galvo: {dot_g}")

ca, cb = st.columns(2)
# Oogst berekening gebaseerd op kwh_nu en start van de dag (vereenvoudigd voor stabiliteit)
ca.metric("🏆 All-time Piek", f"{max(all_time_peak_sheet, st.session_state.p_total_peak):,.0f} W")
cb.metric("☀️ Totaal DC Symo", f"{st.session_state.p_mppt1 + st.session_state.p_mppt2:.0f} W")

st.divider()
st.subheader("Symo MPPT Details (Live DC Input)")
m1, m2 = st.columns(2)
m1.metric("MPPT 1 (West)", f"{st.session_state.p_mppt1:.0f} W")
m2.metric("MPPT 2 (Oost)", f"{st.session_state.p_mppt2:.0f} W")

st.divider()
with st.expander("☀️ Historiek & Maandoverzicht", expanded=True):
    st.subheader("Maandtotalen")
    st.dataframe(monthly_summary.round(1), hide_index=True, use_container_width=True)
    st.divider()
    st.subheader(f"Dagen in {huidige_maand_jaar}")
    if not df_display.empty:
        st.dataframe(df_display.drop(columns=['temp_date', 'Maand']), hide_index=True, use_container_width=True)
