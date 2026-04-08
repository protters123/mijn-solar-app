import streamlit as st
import requests
import time
import pandas as pd
import io
import os
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO - CLOUD OPTIMIZED ☀️📈
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbyIBhDGzmQQvokyzBjYT0Nt8qiRFKtElxMCrhelxfPOLNF2NNbAgOP3PAGTSEQEsMmq/exec" 

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek", page_icon="☀️", layout="centered")

# --- CSS VOOR ANIMATIE ---
st.markdown("""
    <style>
    @keyframes blinker { 50% { opacity: 0; } }
    .stroom-teken { animation: blinker 1.5s linear infinite; color: #FFD700; font-size: 1.5rem; margin-right: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- TIJDZONE & DATUM ---
tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
vandaag_iso = nu_lokaal.strftime('%Y-%m-%d')
vandaag_nl = nu_lokaal.strftime('%d-%m-%Y')

CACHE_FILE = "dagpiek_geheugen.txt"
ARCHIVE_LOG = "laat_gearchiveerd.txt"

def laad_geheugen():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                parts = f.read().strip().split(",")
                if parts[0] == vandaag_iso:
                    return float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
        except: pass
    return 0.0, 0.0, 0.0, 0.0

def sla_geheugen_op(s, g, t, kwh):
    try:
        with open(CACHE_FILE, "w") as f:
            f.write(f"{vandaag_iso},{s},{g},{t},{kwh}")
    except: pass

# --- DATA OPHALEN FUNCTIE ---
def fetch_fronius_data(url):
    try:
        r = requests.get(url, timeout=2).json()
        power = abs(float(r.get('active_power_w', 0)))
        energy = float(r.get('energy_today_wh', 0)) / 1000.0
        return power, energy, "🟢"
    except:
        return 0.0, 0.0, "🔴"

# --- INITIALISEREN & RECOVERY UIT SHEET ---
if 'max_kwh_today' not in st.session_state:
    s_p, g_p, t_p, k_p = laad_geheugen()
    
    # Als lokaal geheugen leeg is (Cloud herstart), check de Google Sheet
    if k_p == 0:
        try:
            res_rec = requests.get(CSV_URL, timeout=5)
            if res_rec.status_code == 200:
                df_rec = pd.read_csv(io.StringIO(res_rec.text))
                if not df_rec.empty:
                    last_row = df_rec.iloc[-1]
                    # Check of de laatste rij in de sheet van vandaag is
                    if str(last_row.iloc[0]) == vandaag_nl:
                        s_p = float(last_row.get('Symo', 0))
                        g_p = float(last_row.get('Galvo', 0))
                        t_p = float(last_row.get('Totaal', 0))
                        k_p = float(last_row.get('Oogst/dag', 0))
        except: pass

    st.session_state.p_symo_peak = s_p
    st.session_state.p_galvo_peak = g_p
    st.session_state.p_total_peak = t_p
    st.session_state.max_kwh_today = k_p

# --- LIVE DATA VERWERKEN ---
val_s, kwh_s_live, icon_s = fetch_fronius_data(URL_1)
val_g, kwh_g_live, icon_g = fetch_fronius_data(URL_2)

val_t = val_s + val_g
kwh_t_live = kwh_s_live + kwh_g_live

# Update logica: alleen als waarde hoger is (beveiliging tegen 0-drops)
updated = False
if val_s > st.session_state.p_symo_peak:
    st.session_state.p_symo_peak = val_s
    updated = True
if val_g > st.session_state.p_galvo_peak:
    st.session_state.p_galvo_peak = val_g
    updated = True
if val_t > st.session_state.p_total_peak:
    st.session_state.p_total_peak = val_t
    updated = True
if kwh_t_live > st.session_state.max_kwh_today:
    st.session_state.max_kwh_today = kwh_t_live
    updated = True

if updated:
    sla_geheugen_op(st.session_state.p_symo_peak, st.session_state.p_galvo_peak, 
                    st.session_state.p_total_peak, st.session_state.max_kwh_today)

# --- AUTO-ARCHIVEREN ---
if nu_lokaal.hour == 23:
    laatst_datum = ""
    if os.path.exists(ARCHIVE_LOG):
        try:
            with open(ARCHIVE_LOG, "r") as f: laatst_datum = f.read().strip()
        except: pass
    if laatst_datum != vandaag_iso:
        params = {
            "symo": int(st.session_state.p_symo_peak), 
            "galvo": int(st.session_state.p_galvo_peak),
            "kwh": round(st.session_state.max_kwh_today, 2)
        }
        try:
            r = requests.get(WEBAPP_URL, params=params, timeout=15)
            if r.status_code == 200:
                with open(ARCHIVE_LOG, "w") as f: f.write(vandaag_iso)
                st.balloons()
        except: pass

# --- UI DASHBOARD ---
st.title("☀️ Solar Piek") 
st.image("https://wttr.in", use_container_width=True)
st.write(f"⏰ App-tijd: {nu_lokaal.strftime('%H:%M')} ({vandaag_nl})")

col_a, col_b = st.columns(2)
with col_a:
    st.markdown(f"### Totaal Live: <span class='stroom-teken'>⚡</span> {val_t:,.0f} W", unsafe_allow_html=True)
with col_b:
    st.markdown(f"### 🍯 Oogst Vandaag: {st.session_state.max_kwh_today:,.2f} kWh")

# Historische data laden
historical_max = 3729.0
table_df = pd.DataFrame()
try:
    res = requests.get(CSV_URL, timeout=10)
    if res.status_code == 200:
        df = pd.read_csv(io.StringIO(res.text))
        if not df.empty:
            # Dynamisch kolommen toewijzen
            cols = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag']
            df.columns = cols[:len(df.columns)]
            historical_max = pd.to_numeric(df['Totaal'], errors='coerce').max()
            table_df = df
except: pass

st.metric("🏆 All-time Record", f"{max(historical_max, st.session_state.p_total_peak):,.0f} W")
st.divider()

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"### {icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
    st.metric("Piek", f"{st.session_state.p_symo_peak:,.0f} W")
with c2:
    st.markdown("### 📊 Systeem")
    st.metric("Gelijktijdige Piek", f"{st.session_state.p_total_peak:,.0f} W")
    st.caption(f"Max Oogst: {st.session_state.max_kwh_today:,.2f} kWh")
with c3:
    st.markdown(f"### {icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")
    st.metric("Piek", f"{st.session_state.p_galvo_peak:,.0f} W")

st.divider()
st.subheader("📅 Jaaroverzicht") 
if not table_df.empty:
    st.dataframe(table_df.iloc[::-1], use_container_width=True, height=350)

st.caption(f"Laatste check: {nu_lokaal.strftime('%H:%M:%S')}")
time.sleep(5) # Iets langer wachten voor stabiliteit in Cloud
st.rerun()
