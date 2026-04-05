import streamlit as st
import requests
import time
import pandas as pd
import io
import os
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO - DEFINITIEVE VERSIE + WEER ☀️
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

# JE PERSOONLIJKE LINK IS HIER HERSTELD:
WEBAPP_URL = "https://google.com"

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- TIJDZONE & GEHEUGEN ---
tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
CACHE_FILE = "dagpiek_geheugen.txt"
ARCHIVE_LOG = "laatst_gearchiveerd.txt"

# --- FUNCTIE: WEER OPHALEN (Tongeren-Borgloon) ---
def get_weather():
    try:
        url = "https://open-meteo.com"
        res = requests.get(url, timeout=3).json()
        return res['current_weather'], res['daily']
    except:
        return None, None

def laad_dagpiek():
    vandaag = nu_lokaal.strftime('%Y-%m-%d')
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    parts = content.split(",")
                    if parts[0] == vandaag:
                        return float(parts[1]), float(parts[2])
        except: pass
    return 0.0, 0.0

def sla_dagpiek_op(s, g):
    vandaag = nu_lokaal.strftime('%Y-%m-%d')
    with open(CACHE_FILE, "w") as f:
        f.write(f"{vandaag},{s},{g}")

# --- INITIALISEREN ---
if 'p_symo_peak' not in st.session_state:
    s_start, g_start = laad_dagpiek()
    st.session_state.p_symo_peak = s_start
    st.session_state.p_galvo_peak = g_start
if 'record_celebrated' not in st.session_state:
    st.session_state.record_celebrated = False

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

# --- LIVE DATA & WEER OPHALEN ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g
current_w, daily_w = get_weather()

# Update Dagpieken in geheugen
update_cache = False
if val_s > st.session_state.p_symo_peak:
    st.session_state.p_symo_peak = val_s
    update_cache = True
if val_g > st.session_state.p_galvo_peak:
    st.session_state.p_galvo_peak = val_g
    update_cache = True

if update_cache:
    sla_dagpiek_op(st.session_state.p_symo_peak, st.session_state.p_galvo_peak)

# --- DATA LADEN UIT SHEET ---
historical_max = 3729.0
table_df = pd.DataFrame()
try:
    res = requests.get(CSV_URL, timeout=10)
    if res.status_code == 200:
        df = pd.read_csv(io.StringIO(res.text))
        if not df.empty:
            historical_max = pd.to_numeric(df.iloc[:, 3], errors='coerce').max()
            table_df = df
except: pass

# --- RECORD CHECK & BALLONNEN ---
current_all_time = max(historical_max, val_t)
if val_t > historical_max and not st.session_state.record_celebrated:
    st.balloons()
    st.session_state.record_celebrated = True
elif val_t <= historical_max:
    st.session_state.record_celebrated = False

# --- AUTO-LOGICA (ARCHIVEREN OM 23:00) ---
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
                st.toast("🚀 Dagpiek automatisch gearchiveerd!")
        except: pass

# --- UI DASHBOARD ---
st.title("☀️ Solar Piek Pro") 

# --- WEER DISPLAY BOVENAAN ---
if current_w:
    w1, w2, w3 = st.columns(3)
    w1.metric("🌡️ Nu", f"{current_w['temperature']}°C")
    w2.metric("🌤️ Max Vandaag", f"{daily_w['temperature_2m_max'][0]}°C")
    w3.metric("⛱️ UV Index", f"{daily_w['uv_index_max'][0]}")
    st.divider()

st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
st.metric("🏆 All-time Record", f"{current_all_time:,.0f} W")

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
if not table_df.empty:
    st.table(table_df.iloc[::-1].head(15))
else:
    st.info("Tabel wordt geladen...")

st.caption(f"Update: {nu_lokaal.strftime('%H:%M:%S')} | Auto-log om 23:00")
time.sleep(2)
st.rerun()
