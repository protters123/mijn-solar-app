import streamlit as st
import requests
import time
import pandas as pd
import io
import os
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - MET OPSLAAN FUNCTIE ☀️
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv"
# JOUW PERSOONLIJKE GOOGLE SCRIPT URL:
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbyGEe_-BSVg5o0f_5oR9hHXs2h8Qvtl172ojC-edFyXgGHMOG4h7zkSkXIxdZlyI_lG/exec"

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- GEHEUGEN FUNCTIES (LOKAAL) ---
CACHE_FILE = "piek_geheugen.txt"

def laad_pieken():
    vandaag = datetime.now().strftime('%Y-%m-%d')
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                data = f.read().split(",")
                if data[0] == vandaag:
                    return float(data[1]), float(data[2]), float(data[3])
        except: pass
    return 0.0, 0.0, 3717.0

def sla_pieken_op(s, g, t):
    vandaag = datetime.now().strftime('%Y-%m-%d')
    with open(CACHE_FILE, "w") as f:
        f.write(f"{vandaag},{s},{g},{t}")

# Initialiseer geheugen
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

# Update records
update_needed = False
if val_s > st.session_state.p_symo_peak:
    st.session_state.p_symo_peak = val_s
    update_needed = True
if val_g > st.session_state.p_galvo_peak:
    st.session_state.p_galvo_peak = val_g
    update_needed = True
if val_t > st.session_state.p_total_peak:
    st.session_state.p_total_peak = val_t
    update_needed = True
    st.balloons()

if update_needed:
    sla_pieken_op(st.session_state.p_symo_peak, st.session_state.p_galvo_peak, st.session_state.p_total_peak)

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

# --- NIEUW: OPSLAAN NAAR GOOGLE SHEETS KNOP ---
st.subheader("💾 Data Opslaan")
if st.button("Sla Dagpiek op in Google Sheet"):
    with st.spinner("Bezig met opslaan..."):
        params = {
            "symo": int(st.session_state.p_symo_peak),
            "galvo": int(st.session_state.p_galvo_peak)
        }
        try:
            r = requests.get(WEBAPP_URL, params=params, timeout=10)
            if r.status_code == 200:
                st.success(f"✅ Opgeslagen! Symo: {params['symo']}W | Galvo: {params['galvo']}W")
                time.sleep(2)
            else:
                st.error("Fout bij Google Script. Controleer je implementatie.")
        except:
            st.error("Kon geen verbinding maken met Google Script.")

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
    st.info("Tabel wordt geladen...")

st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')} | Verversing elke 2 sec")
time.sleep(2)
st.rerun()
