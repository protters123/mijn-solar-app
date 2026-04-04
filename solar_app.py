import streamlit as st
import requests
import time
import pandas as pd
import io
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - DE DEFINITIEVE FIX
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
# FIX: Correcte URL voor Google Sheets
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv"

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

# --- DATA LADEN & RECORDS BEPALEN ---
historical_max = 3717.0
sheet_peak_symo = 0.0
sheet_peak_galvo = 0.0
table_df = pd.DataFrame()
vandaag = datetime.now().strftime('%d-%m-%Y')

try:
    response = requests.get(CSV_URL, timeout=5)
    if response.status_code == 200:
        df = pd.read_csv(io.StringIO(response.text))
        if not df.empty:
            # All-time Record (Kolom 4)
            historical_max = pd.to_numeric(df.iloc[:, 3], errors='coerce').max()
            
            # Zoek piek van vandaag in de sheet
            vandaag_data = df[df.iloc[:, 0].astype(str).str.contains(vandaag, na=False)]
            if not vandaag_data.empty:
                sheet_peak_symo = pd.to_numeric(vandaag_data.iloc[:, 1], errors='coerce').max()
                sheet_peak_galvo = pd.to_numeric(vandaag_data.iloc[:, 2], errors='coerce').max()

            table_df = pd.DataFrame({
                'Datum': df.iloc[:, 0].astype(str),
                'Symo (W)': pd.to_numeric(df.iloc[:, 1], errors='coerce'),
                'Galvo (W)': pd.to_numeric(df.iloc[:, 2], errors='coerce'),
                'Totaal (W)': pd.to_numeric(df.iloc[:, 3], errors='coerce')
            }).dropna(subset=['Datum'])
except: pass

# --- LIVE DATA OPHALEN ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# Gebruik session_state om de piek van de huidige sessie vast te houden
if 'p_symo_session' not in st.session_state:
    st.session_state.p_symo_session = sheet_peak_symo
if 'p_galvo_session' not in st.session_state:
    st.session_state.p_galvo_session = sheet_peak_galvo

# Update pieken (neem de hoogste van: sheet, sessie of live)
st.session_state.p_symo_session = max(val_s, st.session_state.p_symo_session, sheet_peak_symo)
st.session_state.p_galvo_session = max(val_g, st.session_state.p_galvo_session, sheet_peak_galvo)

all_time = max(historical_max, val_t)

# --- UI ---
st.title("☀️ Solar Piek Pro") 
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
st.metric("🏆 All-time Record", f"{all_time:,.0f} W")

st.divider()

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"### {icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
    st.metric("Piek Vandaag", f"{st.session_state.p_symo_session:,.0f} W")

with c2:
    st.markdown(f"### {icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")
    st.metric("Piek Vandaag", f"{st.session_state.p_galvo_session:,.0f} W")

st.divider()
st.subheader("💚 Maandoverzicht") 
if not table_df.empty:
    st.table(table_df.iloc[::-1])
else:
    st.warning("Kan verbinding met Google Sheets niet herstellen.")

st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(2)
st.rerun()
