import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
import pytz
try:
    from streamlit_autorefresh import st_autorefresh
except:
    st_autorefresh = None

# ==========================================
# SOLAR PIEK PRO v14.9 - MPPT & LIVE REFRESH
# ==========================================

# Activeer de 2-seconden verversing
if st_autorefresh:
    st_autorefresh(interval=2000, key="solar_refresh")

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzl6V4knhaZnB7zgt5kvFkgTCph3Y-3S4KDHJEPzaaU1gqvTIfokzIiFUxDfhiBlIxW/exec"

PUBLIEK_IP = "94.110.235.108"
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"
# Gebruik DeviceId 2 voor de Symo MPPT data (gezien op je systeeminfo screenshot)
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
    st.session_state.p_symo_peak = 0.0
    st.session_state.p_galvo_peak = 0.0
    st.session_state.p_mppt1, st.session_state.p_mppt2 = 0.0, 0.0
    st.session_state.start_kwh_dag = None
    st.session_state.last_sync_time = "Nog geen sync"
    st.session_state.last_sheet_update = 0
    st.session_state.initialized = True

# ====================== DATA FUNCTIES ======================

@st.cache_data(ttl=60)
def load_historical_data(url):
    try:
        return pd.read_csv(f"{url}&ts={int(time.time()/60)}", header=0, decimal=",")
    except: return None

def fetch_hw_data(url):
    try:
        r = requests.get(url, timeout=1.2).json()
        power = round(abs(float(r.get('active_power_w', 0))))
        kwh = float(r.get('total_power_export_kwh', 0))
        if kwh == 0:
            kwh = float(r.get('total_power_export_t1_kwh', 0)) + float(r.get('total_power_export_t2_kwh', 0))
        return (power if power >= 10 else 0), kwh, "🟢"
    except: return 0, 0, "🔴"

def fetch_mppt_live(url):
    try:
        r = requests.get(url, timeout=1.5).json()
        d = r['Body']['Data']
        # Fallback voor verschillende veldnamen (UDC/IDC vs UDC_1/IDC_1)
        u1 = d.get('UDC', {}).get('Value') or d.get('UDC_1', {}).get('Value', 0)
        i1 = d.get('IDC', {}).get('Value') or d.get('IDC_1', {}).get('Value', 0)
        u2 = d.get('UDC_2', {}).get('Value', 0)
        i2 = d.get('IDC_2', {}).get('Value', 0)
        return round(u1 * i1, 0), round(u2 * i2, 0)
    except: return 0.0, 0.0

# ====================== LIVE DATA & VERWERKING ======================
val_s, kwh_s, dot_s = fetch_hw_data(URL_1)
val_g, kwh_g, dot_g = fetch_hw_data(URL_2)
val_t, kwh_nu = val_s + val_g, kwh_s + kwh_g

# Live MPPT waarden ophalen
st.session_state.p_mppt1, st.session_state.p_mppt2 = fetch_mppt_live(URL_SYMO_MPPT)

# Historiek verwerking (Google Sheets)
df_raw = load_historical_data(CSV_URL)
monthly_summary, df_display = pd.DataFrame(), pd.DataFrame()
stand_gisteren, all_time_peak_sheet = None, 3729.0

if df_raw is not None:
    try:
        df_full = df_raw.iloc[:, :7].copy()
        df_full.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWhdag', 'KWhdag']
        atp = pd.to_numeric(df_full['Totaal'], errors='coerce').max()
        if atp > 0: all_time_peak_sheet = atp

        df_full['temp_date'] = pd.to_datetime(df_full['Datum'], dayfirst=True, errors='coerce')
        df_full['Maand'] = df_full['temp_date'].dt.strftime('%m-%Y')
        df_full['Oogst/dag'] = pd.to_numeric(df_full['Oogst/dag'].astype(str).str.replace(',', '.'), errors='coerce')
        
        monthly_summary = df_full.groupby('Maand')['Oogst/dag'].sum().reset_index()
        monthly_summary['temp_sort'] = pd.to_datetime(monthly_summary['Maand'], format='%m-%Y')
        monthly_summary = monthly_summary.sort_values('temp_sort', ascending=False).drop(columns=['temp_sort'])

        df_sorted = df_full.sort_values('temp_date', ascending=False)
        gisteren_df = df_sorted[df_sorted['Datum'] != vandaag_nl]
        if not gisteren_df.empty:
            stand_gisteren = pd.to_numeric(gisteren_df['KWhdag'].iloc[0], errors='coerce')
        df_display = df_sorted[df_sorted['Maand'] == huidige_maand_jaar].drop(columns=['temp_date', 'Maand']).copy()
    except: pass

if st.session_state.start_kwh_dag is None:
    st.session_state.start_kwh_dag = stand_gisteren if stand_gisteren else kwh_nu

oogst_vandaag = round(max(0.0, kwh_nu - (st.session_state.start_kwh_dag or kwh_nu)), 1)
st.session_state.p_total_peak = max(st.session_state.p_total_peak, val_t)

# ====================== UI ======================
st.title("⚡ Solar Piek PRO")

st.markdown(f"<h1 style='text-align:center;color:#FFB300; font-size: 55px;'>⚡ {val_t:,.0f} Watt</h1>", unsafe_allow_html=True)
st.progress(min(val_t / 8000, 1.0))
st.caption(f"🔄 Laatste update: {datetime.now(tz).strftime('%H:%M:%S')} | Symo: {dot_s} Galvo: {dot_g}")

ca, cb = st.columns(2)
ca.metric("⚡ Oogst vandaag", f"{oogst_vandaag:.1f} kWh")
cb.metric("🏆 All-time Piek", f"{max(all_time_peak_sheet, st.session_state.p_total_peak):,.0f} W")

st.divider()
st.subheader("Symo MPPT Details (Live DC Input)")
m1, m2, m3 = st.columns(3)
m1.metric("MPPT 1 (West)", f"{st.session_state.p_mppt1:.0f} W")
m2.metric("MPPT 2 (Oost)", f"{st.session_state.p_mppt2:.0f} W")
m3.metric("Totaal Symo DC", f"{st.session_state.p_mppt1 + st.session_state.p_mppt2:.0f} W")

st.divider()
with st.expander("☀️ Historiek & Maandoverzicht", expanded=True):
    st.subheader("Maandtotalen")
    st.dataframe(monthly_summary.round(1), hide_index=True, use_container_width=True)
    st.divider()
    st.subheader(f"Dagen in {huidige_maand_jaar}")
    st.dataframe(df_display, hide_index=True, use_container_width=True)
