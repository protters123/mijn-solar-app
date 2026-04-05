import streamlit as st
import requests
import time
import pandas as pd
import io
import os
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO - VERSIE 13:45 ARCHIVE ☀️
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv&gid=0"

# VUL HIER JE ECHTE GOOGLE SCRIPT URL IN
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxwClGZryn1ZbtLWqAQs5LF98WVm0ANb5rOyjgbYG9xQXHEjfgWG5RUbfXGXf8B4Xbb/exec" 

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek", page_icon="☀️", layout="centered")

# --- TIJDZONE & GEHEUGEN ---
tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
vandaag_str = nu_lokaal.strftime('%d-%m-%Y')
CACHE_FILE = "dagpiek_geheugen.txt"
ARCHIVE_LOG = "laatst_gearchiveerd.txt"

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
    st.session_state.p_symo_peak, st.session_state.p_galvo_peak = s_start, g_start

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

# --- LIVE DATA OPHALEN ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# Update Dagpieken in het geheugen
if val_s > st.session_state.p_symo_peak or val_g > st.session_state.p_galvo_peak:
    st.session_state.p_symo_peak = max(val_s, st.session_state.p_symo_peak)
    st.session_state.p_galvo_peak = max(val_g, st.session_state.p_galvo_peak)
    sla_dagpiek_op(st.session_state.p_symo_peak, st.session_state.p_galvo_peak)

# --- AUTO-ARCHIVEREN LOGICA (13:45) ---
# --- AUTO-ARCHIVEREN LOGICA (Aangepast naar 13:52) ---
target_uur = 13
target_min = 57

if nu_lokaal.hour == target_uur and nu_lokaal.minute == target_min:
    vandaag_sleutel = nu_lokaal.strftime('%Y-%m-%d')
    laatst_datum = ""
    
    # Controleer of de archief-log bestaat om dubbel schrijven te voorkomen
    if os.path.exists(ARCHIVE_LOG):
        try:
            with open(ARCHIVE_LOG, "r") as f: laatst_datum = f.read().strip()
        except: pass
    
    # Alleen schrijven als we dit vandaag nog niet gedaan hebben op dit tijdstip
    if laatst_datum != vandaag_sleutel:
        params = {
            "symo": int(st.session_state.p_symo_peak), 
            "galvo": int(st.session_state.p_galvo_peak)
        }
        try:
            # Hier wordt de data naar je Google Script gestuurd
            r = requests.get(WEBAPP_URL, params=params, timeout=15)
            if r.status_code == 200:
                with open(ARCHIVE_LOG, "w") as f: f.write(vandaag_sleutel)
                st.balloons()
                st.toast("✅ Piekmomenten om 13:52 naar Sheet geschreven!")
        except Exception as e:
            st.error(f"Fout bij schrijven naar Sheet: {e}")


# --- UI DASHBOARD ---
st.title("☀️ Solar Piek Pro") 
st.write(f"📅 **Datum:** {vandaag_str} | ⏰ **Tijd:** {nu_lokaal.strftime('%H:%M')} (Schrijven om {target_uur}:{target_min})")

st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")

# Kolommen voor de individuele pieken
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
st.caption(f"Laatste update: {nu_lokaal.strftime('%H:%M:%S')}")

time.sleep(2)
st.rerun()
