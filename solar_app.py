import streamlit as st
import requests
import time
import pandas as pd
import io
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - DE DEFINITIEVE FIX ☀️
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv"

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        val = abs(float(r['active_power_w']))
        return val, "🟢"
    except: return 0.0, "🔴"

# --- DATA LADEN & RECORDS UIT SHEET HALEN ---
all_time_rec = 3717.0
sheet_peak_s = 0.0
sheet_peak_g = 0.0
table_df = pd.DataFrame()
vandaag_str = datetime.now().strftime('%d-%m-%Y')

try:
    response = requests.get(CSV_URL, timeout=5)
    if response.status_code == 200:
        df = pd.read_csv(io.StringIO(response.text))
        if not df.empty:
            # 1. All-time record
            all_time_rec = pd.to_numeric(df.iloc[:, 3], errors='coerce').max()
            
            # 2. Zoek of vandaag al in de lijst staat voor de dagpiek
            vandaag_data = df[df.iloc[:, 0].astype(str).str.contains(vandaag_str, na=False)]
            if not vandaag_data.empty:
                sheet_peak_s = pd.to_numeric(vandaag_data.iloc[:, 1], errors='coerce').max()
                sheet_peak_g = pd.to_numeric(vandaag_data.iloc[:, 2], errors='coerce').max()

            table_df = pd.DataFrame({
                'Datum': df.iloc[:, 0].astype(str),
                'Symo (W)': pd.to_numeric(df.iloc[:, 1], errors='coerce'),
                'Galvo (W)': pd.to_numeric(df.iloc[:, 2], errors='coerce'),
                'Totaal (W)': pd.to_numeric(df.iloc[:, 3], errors='coerce')
            }).dropna(subset=['Datum'])
except: pass

# --- LIVE DATA & GEHEUGEN ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# Initialiseer sessie-geheugen met de waarde uit de sheet
if 'p_symo_peak' not in st.session_state: st.session_state.p_symo_peak = sheet_peak_s
if 'p_galvo_peak' not in st.session_state: st.session_state.p_galvo_peak = sheet_peak_g

# Update records (hoogste van: live, sessie of sheet)
st.session_state.p_symo_peak = max(val_s, st.session_state.p_symo_peak, sheet_peak_s)
st.session_state.p_galvo_peak = max(val_g, st.session_state.p_galvo_peak, sheet_peak_g)

# --- DASHBOARD UI ---
st.title("☀️ Solar Piek Pro") 
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
st.metric("🏆 All-time Record", f"{max(all_time_rec, val_t):,.0f} W")

st.divider()

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"### {icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
    st.metric("Piek Vandaag", f"{st.session_state.p_symo_peak:,.0f} W")
with c2:
    st.markdown(f"### {icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")
    st.metric("Piek Vandaag", f"{st.session_state.p_galvo_peak:,.0f} W")

st.divider()
st.subheader("💚 Maandoverzicht") 
if not table_df.empty:
    st.table(table_df.iloc[::-1])
else:
    st.info("De tabel wordt geladen...")

st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')} | Verversing elke 2 sec")

time.sleep(2)
st.rerun()
