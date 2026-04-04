import streamlit as st
import requests
import time
import pandas as pd
import io
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - DE "RESTART" VERSIE ☀️
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
# Gebruik de meest directe export link
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- SIMPEL SESSIE GEHEUGEN ---
if 'p_symo_peak' not in st.session_state:
    st.session_state.p_symo_peak = 0.0
    st.session_state.p_galvo_peak = 0.0

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

# --- LIVE DATA ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

if val_s > st.session_state.p_symo_peak: st.session_state.p_symo_peak = val_s
if val_g > st.session_state.p_galvo_peak: st.session_state.p_galvo_peak = val_g

# --- UI ---
st.title("☀️ Solar Piek Pro") 
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
st.metric("🏆 All-time Record", "3,729 W") # Even hardcoded voor stabiliteit

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

# --- TABEL (PUUR EN SIMPEL) ---
st.subheader("💚 Maandoverzicht") 
try:
    # We proberen de data op te halen zonder cache of extra poeha
    res = requests.get(CSV_URL, timeout=10)
    if res.status_code == 200:
        df = pd.read_csv(io.StringIO(res.text))
        # Alleen de kolommen die we echt nodig hebben
        st.table(df.iloc[::-1].head(10)) 
    else:
        st.error(f"Google geeft foutcode: {res.status_code}")
except Exception as e:
    st.warning("Kan de tabel niet laden. Controleer of de sheet op 'Openbaar' staat.")

st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(2)
st.rerun()
