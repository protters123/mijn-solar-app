import streamlit as st
import requests
import time
import pandas as pd
import io
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - EXTRA ROBUUST
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
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

# --- DATA LADEN ---
historical_max = 3717.0
table_df = pd.DataFrame()

try:
    # We halen de data op zonder dat de hele app stopt bij een fout
    response = requests.get(CSV_URL, timeout=5)
    if response.status_code == 200:
        raw_df = pd.read_csv(io.StringIO(response.text))
        if not raw_df.empty:
            # All-time Record berekenen uit de 4e kolom
            historical_max = pd.to_numeric(raw_df.iloc[:, 3], errors='coerce').max()
            
            # Tabel netjes maken
            table_df = pd.DataFrame({
                'Datum': raw_df.iloc[:, 0].astype(str),
                'Symo (W)': pd.to_numeric(raw_df.iloc[:, 1], errors='coerce'),
                'Galvo (W)': pd.to_numeric(raw_df.iloc[:, 2], errors='coerce'),
                'Totaal (W)': pd.to_numeric(raw_df.iloc[:, 3], errors='coerce')
            }).dropna(subset=['Datum'])
except Exception as e:
    st.error(f"Sheet verbindingsfout: {e}")

# --- LIVE DATA & PIEKEN ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# Gebruik session_state voor de pieken (blijft bewaard zolang tabblad open is)
if 'p_symo_max' not in st.session_state: st.session_state.p_symo_max = 0.0
if 'p_galvo_max' not in st.session_state: st.session_state.p_galvo_max = 0.0

st.session_state.p_symo_max = max(val_s, st.session_state.p_symo_max)
st.session_state.p_galvo_max = max(val_g, st.session_state.p_galvo_max)

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
    st.metric("Piek Vandaag", f"{st.session_state.p_symo_max:,.0f} W")
with c2:
    st.markdown(f"### {icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")
    st.metric("Piek Vandaag", f"{st.session_state.p_galvo_max:,.0f} W")

st.divider()
st.subheader("💚 Maandoverzicht") 

if not table_df.empty:
    # Toon de tabel, nieuwste eerst
    st.table(table_df.iloc[::-1])
else:
    st.info("De tabel is momenteel leeg of wordt geladen...")

st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(2)
st.rerun()
