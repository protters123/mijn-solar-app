import streamlit as st
import requests
import time
import pandas as pd
import io
import os
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - VOLAUTOMATISCH ☀️
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv&gid=0"

# PLAK HIER DE GEKOPIEERDE URL VAN JE SCHERM:
WEBAPP_URL = "https://google.com"

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- GEHEUGEN: PIEK ONTHOUDEN ---
CACHE_FILE = "dagpiek_geheugen.txt"
ARCHIVE_LOG = "laatst_gearchiveerd.txt"

def laad_dagpiek():
    vandaag = datetime.now().strftime('%Y-%m-%d')
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                parts = f.read().split(",")
                if parts[0] == vandaag:
                    return float(parts[1]), float(parts[2])
        except: pass
    return 0.0, 0.0

def sla_dagpiek_op(s, g):
    vandaag = datetime.now().strftime('%Y-%m-%d')
    with open(CACHE_FILE, "w") as f:
        f.write(f"{vandaag},{s},{g}")

# Initialiseer sessie-geheugen
if 'p_symo_peak' not in st.session_state:
    s_start, g_start = laad_dagpiek()
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

# Update & bewaar piek lokaal tegen vergeten bij refresh
if val_s > st.session_state.p_symo_peak:
    st.session_state.p_symo_peak = val_s
    sla_dagpiek_op(st.session_state.p_symo_peak, st.session_state.p_galvo_peak)
if val_g > st.session_state.p_galvo_peak:
    st.session_state.p_galvo_peak = val_g
    sla_dagpiek_op(st.session_state.p_symo_peak, st.session_state.p_galvo_peak)

# --- AUTO-LOGICA (ARCHIVEREN OM 23:00) ---
nu = datetime.now()
vandaag = nu.strftime('%Y-%m-%d')
if nu.hour == 23:
    laatst_datum = ""
    if os.path.exists(ARCHIVE_LOG):
        with open(ARCHIVE_LOG, "r") as f: laatst_datum = f.read().strip()
    
    if laatst_datum != vandaag:
        params = {"symo": int(st.session_state.p_symo_peak), "galvo": int(st.session_state.p_galvo_peak)}
        try:
            r = requests.get(WEBAPP_URL, params=params, timeout=10)
            if r.status_code == 200:
                with open(ARCHIVE_LOG, "w") as f: f.write(vandaag)
                st.toast("🚀 Dagpiek automatisch gearchiveerd!")
        except: pass

# --- UI DASHBOARD ---
st.title("☀️ Solar Piek Pro") 
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
st.metric("🏆 All-time Record", "3,729 W")

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

# --- TABEL SECTIE ---
st.subheader("💚 Maandoverzicht") 
try:
    res = requests.get(CSV_URL, timeout=10)
    if res.status_code == 200:
        df = pd.read_csv(io.StringIO(res.text))
        st.table(df.iloc[::-1].head(15))
except:
    st.warning("Verbinden met Google Sheets...")

st.caption(f"Update: {nu.strftime('%H:%M:%S')} | Auto-log om 23:00")
time.sleep(2)
st.rerun()
