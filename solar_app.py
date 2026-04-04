import streamlit as st
import requests
import time
import pandas as pd
import io
import os
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - HERSTELDE VERSIE MET GEHEUGEN
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv"

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- FUNCTIE: PIEK OPSLAAN OP SERVER ---
CACHE_FILE = "dag_records.txt"

def load_cache():
    vandaag = datetime.now().strftime('%Y-%m-%d')
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            line = f.read().strip()
            if line:
                datum, s, g = line.split(",")
                if datum == vandaag:
                    return float(s), float(g)
    return 0.0, 0.0

def save_cache(s, g):
    vandaag = datetime.now().strftime('%Y-%m-%d')
    with open(CACHE_FILE, "w") as f:
        f.write(f"{vandaag},{s},{g}")

# Initialiseer pieken
if 'p_symo_peak' not in st.session_state:
    s_start, g_start = load_cache()
    st.session_state.p_symo_peak = s_start
    st.session_state.p_galvo_peak = g_start

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

# --- LIVE DATA OPHALEN ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# Update records
if val_s > st.session_state.p_symo_peak:
    st.session_state.p_symo_peak = val_s
    save_cache(st.session_state.p_symo_peak, st.session_state.p_galvo_peak)
if val_g > st.session_state.p_galvo_peak:
    st.session_state.p_galvo_peak = val_g
    save_cache(st.session_state.p_symo_peak, st.session_state.p_galvo_peak)

# --- DATA LADEN (De tabel-fix) ---
historical_max = 3717.0
table_df = pd.DataFrame()

try:
    response = requests.get(CSV_URL, timeout=5)
    if response.status_code == 200:
        df = pd.read_csv(io.StringIO(response.text))
        if not df.empty:
            historical_max = pd.to_numeric(df.iloc[:, 3], errors='coerce').max()
            table_df = pd.DataFrame({
                'Datum': df.iloc[:, 0].astype(str),
                'Symo (W)': pd.to_numeric(df.iloc[:, 1], errors='coerce'),
                'Galvo (W)': pd.to_numeric(df.iloc[:, 2], errors='coerce'),
                'Totaal (W)': pd.to_numeric(df.iloc[:, 3], errors='coerce')
            }).dropna(subset=['Datum'])
except:
    pass

# --- UI ---
st.title("☀️ Solar Piek Pro") 
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
st.metric("🏆 All-time Record", f"{max(historical_max, val_t):,.0f} W")

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
    st.info("De tabel wordt geladen vanuit Google Sheets...")

st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')} | Verversing 2s")

time.sleep(2)
st.rerun()
