import streamlit as st
import requests
import time
import pandas as pd
import io
import os
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO - DE DEFINITIEVE FIX ☀️
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv&gid=0"

# PLAK HIER DE MIDDELSTE URL VAN JE SCHERM:
WEBAPP_URL = "https://google.com"

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- TIJD & GEHEUGEN ---
tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
CACHE_FILE = "dagpiek_geheugen.txt"
ARCHIVE_LOG = "laatst_gearchiveerd.txt"

def laad_dagpiek():
    vandaag = nu_lokaal.strftime('%Y-%m-%d')
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                parts = f.read().split(",")
                if parts[0] == vandaag:
                    return float(parts[1]), float(parts[2])
        except: pass
    return 0.0, 0.0

def sla_dagpiek_op(s, g):
    vandaag = nu_lokaal.strftime('%Y-%m-%d')
    with open(CACHE_FILE, "w") as f:
        f.write(f"{vandaag},{s},{g}")

if 'p_symo_peak' not in st.session_state:
    s_start, g_start = laad_dagpiek()
    st.session_state.p_symo_peak = s_start
    st.session_state.p_galvo_peak = g_start

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

# --- LIVE DATA ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

if val_s > st.session_state.p_symo_peak:
    st.session_state.p_symo_peak = val_s
    sla_dagpiek_op(st.session_state.p_symo_peak, st.session_state.p_galvo_peak)
if val_g > st.session_state.p_galvo_peak:
    st.session_state.p_galvo_peak = val_g
    sla_dagpiek_op(st.session_state.p_symo_peak, st.session_state.p_galvo_peak)

# --- AUTO-LOGICA (23:00) ---
vandaag = nu_lokaal.strftime('%Y-%m-%d')
if nu_lokaal.hour == 23:
    laatst_datum = ""
    if os.path.exists(ARCHIVE_LOG):
        try:
            with open(ARCHIVE_LOG, "r") as f: laatst_datum = f.read().strip()
        except: pass
    
    if laatst_datum != vandaag:
        params = {"symo": int(st.session_state.p_symo_peak), "galvo": int(st.session_state.p_galvo_peak)}
        try:
            r = requests.get(WEBAPP_URL, params=params, timeout=15)
            if r.status_code == 200:
                with open(ARCHIVE_LOG, "w") as f: f.write(vandaag)
                st.toast("🚀 Automatisch gearchiveerd!")
        except: pass

# --- UI ---
st.title("☀️ Solar Piek Pro") 
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")

# All-time Record berekenen uit tabel
historical_max = 3729.0
try:
    res = requests.get(CSV_URL, timeout=5)
    df_rec = pd.read_csv(io.StringIO(res.text))
    historical_max = pd.to_numeric(df_rec.iloc[:, 3], errors='coerce').max()
except: pass

st.metric("🏆 All-time Record", f"{max(historical_max, val_t):,.0f} W")

# --- TIJDELIJKE TEST-KNOP ---
if st.button("🧪 TEST: Sla nu op in Google Sheet"):
    params = {"symo": int(st.session_state.p_symo_peak), "galvo": int(st.session_state.p_galvo_peak)}
    r = requests.get(WEBAPP_URL, params=params)
    if r.status_code == 200: st.success("✅ Het werkt! Check je Sheet.")
    else: st.error("❌ Fout. Check je Google Script implementatie.")

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
    res = requests.get(CSV_URL, timeout=10)
    df = pd.read_csv(io.StringIO(res.text))
    st.table(df.iloc[::-1].head(12))
except:
    st.info("Tabel wordt geladen...")

st.caption(f"Update: {nu_lokaal.strftime('%H:%M:%S')} | Auto-log om 23:00")
time.sleep(2)
st.rerun()
