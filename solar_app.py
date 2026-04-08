import streamlit as st
import requests
import time
import pandas as pd
import io
import os
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO - OOGST/DAG OPSLAG VERSIE
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbw86oW3oRutITUgcetScdvTViMtX3R3i1zz3LQOYQI6pD6UpXLqg8QrE_lzYklbZjQF/exec" 

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek", page_icon="☀️", layout="centered")

# --- CSS VOOR ANIMATIE ---
st.markdown("""
    <style>
    @keyframes blinker { 50% { opacity: 0; } }
    .stroom-teken {
        animation: blinker 1.5s linear infinite;
        color: #FFD700;
        font-size: 1.5rem;
        margin-right: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# --- TIJDZONE & GEHEUGEN ---
tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
vandaag_iso = nu_lokaal.strftime('%Y-%m-%d')
vandaag_nl = nu_lokaal.strftime('%d-%m-%Y')

CACHE_FILE = "dagpiek_geheugen.txt"
ARCHIVE_LOG = "laat_gearchiveerd.txt"

def laad_dagpiek():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    parts = content.split(",")
                    if parts[0] == vandaag_iso:
                        return float(parts[1]), float(parts[2])
        except: pass
    return 0.0, 0.0

def sla_dagpiek_op(s, g):
    with open(CACHE_FILE, "w") as f:
        f.write(f"{vandaag_iso},{s},{g}")

# --- INITIALISEREN ---
if 'p_symo_peak' not in st.session_state:
    s_start, g_start = laad_dagpiek()
    st.session_state.p_symo_peak, st.session_state.p_galvo_peak = s_start, g_start

def fetch_fronius_data(url):
    try:
        r = requests.get(url, timeout=2).json()
        power = abs(float(r.get('active_power_w', 0)))
        energy = float(r.get('energy_today_wh', 0)) / 1000.0  # Naar kWh
        return power, energy, "🟢"
    except:
        return 0.0, 0.0, "🔴"

# --- LIVE DATA OPHALEN ---
val_s, kwh_s, icon_s = fetch_fronius_data(URL_1)
val_g, kwh_g, icon_g = fetch_fronius_data(URL_2)
val_t = val_s + val_g
kwh_t = kwh_s + kwh_g

# Update Dagpieken
if val_s > st.session_state.p_symo_peak or val_g > st.session_state.p_galvo_peak:
    st.session_state.p_symo_peak = max(val_s, st.session_state.p_symo_peak)
    st.session_state.p_galvo_peak = max(val_g, st.session_state.p_galvo_peak)
    sla_dagpiek_op(st.session_state.p_symo_peak, st.session_state.p_galvo_peak)

# --- AUTO-ARCHIVEREN OM 23:00 ---
if nu_lokaal.hour == 23 and nu_lokaal.minute == 0:
    laatst_datum = ""
    if os.path.exists(ARCHIVE_LOG):
        try:
            with open(ARCHIVE_LOG, "r") as f: laatst_datum = f.read().strip()
        except: pass
    if laatst_datum != vandaag_iso:
        # We sturen nu ook de 'kwh' parameter mee
        params = {
            "symo": int(st.session_state.p_symo_peak), 
            "galvo": int(st.session_state.p_galvo_peak),
            "kwh": round(kwh_t, 2)
        }
        try:
            r = requests.get(WEBAPP_URL, params=params, timeout=15)
            if r.status_code == 200:
                with open(ARCHIVE_LOG, "w") as f: f.write(vandaag_iso)
                st.balloons()
        except: pass

# --- UI DASHBOARD ---
st.title("☀️ Solar Piek") 
st.write(f"⏰ App-tijd: {nu_lokaal.strftime('%H:%M')} ({vandaag_nl})")

# Hoofdstatistieken
col_a, col_b = st.columns(2)
with col_a:
    st.markdown(f"### Totaal Live: <span class='stroom-teken'>⚡</span> {val_t:,.0f} W", unsafe_allow_html=True)
with col_b:
    st.markdown(f"### 🍯 Oogst Vandaag: {kwh_t:,.2f} kWh")

# --- DATA LADEN UIT SHEET ---
historical_max = 3729.0
table_df = pd.DataFrame()
try:
    res = requests.get(CSV_URL, timeout=10)
    if res.status_code == 200:
        df = pd.read_csv(io.StringIO(res.text))
        if not df.empty:
            # We forceren hier de 5e kolom 'Oogst/dag'
            if len(df.columns) >= 5:
                df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag']
            else:
                df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal']
                df['Oogst/dag'] = "" # Maak leeg als kolom nog niet bestaat
            
            historical_max = pd.to_numeric(df['Totaal'], errors='coerce').max()
            table_df = df
except: pass

st.metric("🏆 All-time Record", f"{max(historical_max, val_t):,.0f} W")
st.divider()

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"### {icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
    st.metric("Piek", f"{st.session_state.p_symo_peak:,.0f} W")
    st.caption(f"Oogst: {kwh_s:,.2f} kWh")
with c2:
    st.markdown("### 📊 Totaal")
    totaal_piek_vandaag = st.session_state.p_symo_peak + st.session_state.p_galvo_peak
    st.metric("Piek Vandaag", f"{totaal_piek_vandaag:,.0f} W")
    st.caption(f"Totaal: {kwh_t:,.2f} kWh")
with c3:
    st.markdown(f"### {icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")
    st.metric("Piek", f"{st.session_state.p_galvo_peak:,.0f} W")
    st.caption(f"Oogst: {kwh_g:,.2f} kWh")

st.divider()

# --- JAAROVERZICHT TABEL ---
st.subheader("📅 Jaaroverzicht (Historie)") 
if not table_df.empty:
    st.dataframe(table_df.iloc[::-1], use_container_width=True, height=350)

st.caption(f"Update: {nu_lokaal.strftime('%H:%M:%S')}")
time.sleep(2)
st.rerun()
