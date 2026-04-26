import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO v14.1 - INSTANT PEAK SYNC
# ==========================================

st.set_page_config(page_title="Solar Piek PRO", page_icon="⚡☀️⚡", layout="centered")

if 'count' not in st.session_state:
    st.session_state.count = 0

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzl6V4knhaZnB7zgt5kvFkgTCph3Y-3S4KDHJEPzaaU1gqvTIfokzIiFUxDfhiBlIxW/exec"

PUBLIEK_IP = "94.110.235.108"
URL_1 = f"http://{PUBLIEK_IP}:8080/api/v1/data" 
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

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
    st.session_state.start_kwh_dag = None
    st.session_state.last_sync_time = "Nog geen sync"
    st.session_state.last_sheet_update = 0
    st.session_state.initialized = True

# ====================== DATA LADEN ======================
@st.cache_data(ttl=5) # Korte cache voor snelle interactie
def load_historical_data(url):
    try:
        return pd.read_csv(f"{url}&ts={int(time.time()/5)}", header=0, decimal=",")
    except: return None

df_raw = load_historical_data(CSV_URL)
all_time_peak_sheet = 3729.0
stand_gisteren = None

if df_raw is not None:
    try:
        df_full = df_raw.iloc[:, :7].copy()
        df_full.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWhdag', 'KWhdag']
        atp = pd.to_numeric(df_full['Totaal'], errors='coerce').max()
        if atp > 0: all_time_peak_sheet = atp
        
        vandaag_data = df_full[df_full['Datum'] == vandaag_nl]
        if not vandaag_data.empty:
            st.session_state.p_symo_peak = max(st.session_state.p_symo_peak, pd.to_numeric(vandaag_data['Symo'], errors='coerce').max())
            st.session_state.p_galvo_peak = max(st.session_state.p_galvo_peak, pd.to_numeric(vandaag_data['Galvo'], errors='coerce').max())
            st.session_state.p_total_peak = max(st.session_state.p_total_peak, pd.to_numeric(vandaag_data['Totaal'], errors='coerce').max())

        df_full['temp_date'] = pd.to_datetime(df_full['Datum'], dayfirst=True, errors='coerce')
        df_sorted = df_full.sort_values('temp_date', ascending=False)
        gisteren_df = df_sorted[df_sorted['Datum'] != vandaag_nl]
        if not gisteren_df.empty:
            stand_gisteren = pd.to_numeric(gisteren_df['KWhdag'].iloc[0], errors='coerce')
    except: pass

# ====================== FUNCTIES ======================
def fetch_hw_data(url):
    try:
        r = requests.get(url, timeout=1.5).json()
        power = round(abs(float(r.get('active_power_w', 0))))
        kwh = float(r.get('total_power_export_kwh', 0))
        if kwh == 0:
            kwh = float(r.get('total_power_export_t1_kwh', 0)) + float(r.get('total_power_export_t2_kwh', 0))
        return (power if power >= 15 else 0), kwh, "🟢"
    except: return 0, 0, "🔴"

def sla_naar_sheets(s_peak, g_peak, t_peak, oogst, start_kwh, kwh_nu, force=False):
    nu_ts = time.time()
    # Sync als het >30 sec geleden is OF als er een nieuwe piek is (force)
    if force or (nu_ts - st.session_state.last_sheet_update > 30):
        try:
            payload = {"datum": vandaag_nl, "symo": int(s_peak), "galvo": int(g_peak), "totaal": int(t_peak), 
                       "oogst": float(oogst), "start_kwh": float(start_kwh), "kwh_nu": float(kwh_nu), "actie": "update"}
            requests.post(WEBAPP_URL, json=payload, timeout=5)
            st.session_state.last_sheet_update = nu_ts
            st.session_state.last_sync_time = datetime.now(tz).strftime('%H:%M:%S')
        except: pass

# ====================== LIVE DATA VERWERKING ======================
val_s, kwh_s, dot_s = fetch_hw_data(URL_1)
val_g, kwh_g, dot_g = fetch_hw_data(URL_2)
val_t, kwh_nu = val_s + val_g, kwh_s + kwh_g

if st.session_state.start_kwh_dag is None:
    st.session_state.start_kwh_dag = stand_gisteren if stand_gisteren else kwh_nu

oogst_vandaag = round(max(0.0, kwh_nu - (st.session_state.start_kwh_dag or kwh_nu)), 1)

# Check voor NIEUWE piek
nieuwe_piek = False
if val_t > st.session_state.p_total_peak:
    st.session_state.p_total_peak = val_t
    nieuwe_piek = True
if val_s > st.session_state.p_symo_peak:
    st.session_state.p_symo_peak = val_s
    nieuwe_piek = True
if val_g > st.session_state.p_galvo_peak:
    st.session_state.p_galvo_peak = val_g
    nieuwe_piek = True

# Opslaan: forceer sync bij nieuwe piek
if st.session_state.start_kwh_dag:
    sla_naar_sheets(st.session_state.p_symo_peak, st.session_state.p_galvo_peak, st.session_state.p_total_peak, 
                    oogst_vandaag, st.session_state.start_kwh_dag, kwh_nu, force=nieuwe_piek)

# ====================== UI ======================
st.title("⚡ Solar Piek PRO")
st.markdown(f"<h1 style='text-align:center;color:#FFB300; font-size: 60px;'>{val_t:,.0f} W</h1>", unsafe_allow_html=True)
st.progress(min(val_t / 8000, 1.0))
st.caption(f"🔄 Laatste sync: {st.session_state.last_sync_time} {'(PIEK!)' if nieuwe_piek else ''}")

c1, c2 = st.columns(2)
c1.metric("⚡ Oogst", f"{oogst_vandaag:.1f} kWh")
c2.metric("🏆 Record", f"{max(all_time_peak_sheet, st.session_state.p_total_peak):,.0f} W")

st.divider()
col1, col2, col3 = st.columns(3)
col1.metric(f"{dot_s} Symo", f"{val_s} W", f"Piek: {st.session_state.p_symo_peak:,.0f}")
col2.metric(f"{dot_g} Galvo", f"{val_g} W", f"Piek: {st.session_state.p_galvo_peak:,.0f}")
col3.metric("☀️ Totaal", f"{val_t} W", f"Piek: {st.session_state.p_total_peak:,.0f}")

time.sleep(2)
st.rerun()
