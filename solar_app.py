import streamlit as st
import requests
import time
import pandas as pd
import io
import os
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - HERSTELDE VERSIE ☀️
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv"

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- PIEK GEHEUGEN ---
CACHE_FILE = "piek_geheugen.txt"

def laad_pieken():
    vandaag = datetime.now().strftime('%Y-%m-%d')
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                parts = f.read().split(",")
                if parts[0] == vandaag:
                    return float(parts[1]), float(parts[2]), float(parts[3])
        except: pass
    return 0.0, 0.0, 3729.0 # Start met historisch record

if 'p_symo_peak' not in st.session_state:
    s_c, g_c, t_c = laad_pieken()
    st.session_state.p_symo_peak = s_c
    st.session_state.p_galvo_peak = g_c
    st.session_state.p_total_peak = t_c

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

# --- LIVE DATA ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# Update records en schrijf naar bestand
update = False
if val_s > st.session_state.p_symo_peak:
    st.session_state.p_symo_peak = val_s
    update = True
if val_g > st.session_state.p_galvo_peak:
    st.session_state.p_galvo_peak = val_g
    update = True
if val_t > st.session_state.p_total_peak:
    st.session_state.p_total_peak = val_t
    update = True
    st.balloons()

if update:
    vandaag = datetime.now().strftime('%Y-%m-%d')
    with open(CACHE_FILE, "w") as f:
        f.write(f"{vandaag},{st.session_state.p_symo_peak},{st.session_state.p_galvo_peak},{st.session_state.p_total_peak}")

# --- UI ---
st.title("☀️ Solar Piek Pro") 
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
st.metric("🏆 All-time Record", f"{st.session_state.p_total_peak:,.0f} W")

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

# --- TABEL ---
st.subheader("💚 Maandoverzicht") 
try:
    response = requests.get(CSV_URL, timeout=5)
    if response.status_code == 200:
        df = pd.read_csv(io.StringIO(response.text))
        if not df.empty:
            table_df = pd.DataFrame({
                'Datum': df.iloc[:, 0].astype(str),
                'Symo (W)': pd.to_numeric(df.iloc[:, 1], errors='coerce'),
                'Galvo (W)': pd.to_numeric(df.iloc[:, 2], errors='coerce'),
                'Totaal (W)': pd.to_numeric(df.iloc[:, 3], errors='coerce')
            }).dropna(subset=['Datum'])
            st.table(table_df.iloc[::-1])
except:
    st.warning("Verbinding met Google Sheets herstellen...")

st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')} | Verversing 2 sec")
time.sleep(2)
st.rerun()
