import streamlit as st
import requests
import time
import pandas as pd
import io
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - RECORD UPDATE 🏆
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv"

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- INITIALISATIE ---
if 'p_symo_peak' not in st.session_state:
    st.session_state.p_symo_peak = 0.0
    st.session_state.p_galvo_peak = 0.0
    st.session_state.session_max_total = 0.0

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        val = abs(float(r['active_power_w']))
        return val, "🟢"
    except: return 0.0, "🔴"

# --- DATA LADEN & RECORDS BEREKENEN ---
historical_alltime = 0.0
month_record = 0.0

try:
    response = requests.get(CSV_URL, timeout=5)
    if response.status_code == 200:
        df = pd.read_csv(io.StringIO(response.text))
        df['Totaal (W)'] = pd.to_numeric(df.iloc[:, 3], errors='coerce')
        df['Datum'] = pd.to_datetime(df.iloc[:, 0], errors='coerce')
        
        # 1. All-time Record uit tabel
        historical_alltime = df['Totaal (W)'].max()
        
        # 2. Maand Record (hoogste waarde van huidige maand/jaar)
        nu = datetime.now()
        maand_data = df[(df['Datum'].dt.month == nu.month) & (df['Datum'].dt.year == nu.year)]
        if not maand_data.empty:
            month_record = maand_data['Totaal (W)'].max()
except:
    historical_alltime = 3729.0 # Jouw hoogste waarde van 30-03

# --- LIVE DATA OPHALEN ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# Update sessie-pieken
if val_s > st.session_state.p_symo_peak: st.session_state.p_symo_peak = val_s
if val_g > st.session_state.p_galvo_peak: st.session_state.p_galvo_peak = val_g
if val_t > st.session_state.session_max_total: st.session_state.session_max_total = val_t

# Bepaal finale records (historie vs live sessie)
final_alltime = max(historical_alltime, st.session_state.session_max_total)
final_month = max(month_record, st.session_state.session_max_total)

# --- DASHBOARD UI ---
st.title("☀️ Solar Piek Pro") 
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")

# Twee kolommen voor de records bovenin
r1, r2 = st.columns(2)
with r1:
    st.metric("🏆 All-time Record", f"{final_alltime:,.0f} W")
with r2:
    st.metric("📅 Record deze Maand", f"{final_month:,.0f} W")

st.divider()

# Symo & Galvo live meters + Dagpieken
c1, c2 = st.columns(2)
with c1:
    st.markdown(f"### {icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
    st.caption(f"Piek Vandaag: {st.session_state.p_symo_peak:,.0f} W")
with c2:
    st.markdown(f"### {icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")
    st.caption(f"Piek Vandaag: {st.session_state.p_galvo_peak:,.0f} W")

st.divider()

# --- TABEL SECTIE ---
st.subheader("💚 Maandoverzicht") 
try:
    if not df.empty:
        # Weergeven van de tabel (datum sortering behouden)
        table_display = pd.DataFrame({
            'Datum': df.iloc[:, 0].astype(str),
            'Symo (W)': pd.to_numeric(df.iloc[:, 1], errors='coerce'),
            'Galvo (W)': pd.to_numeric(df.iloc[:, 2], errors='coerce'),
            'Totaal (W)': df['Totaal (W)']
        }).dropna(subset=['Datum'])
        st.table(table_display.iloc[::-1].head(10)) # Toon laatste 10 dagen
except:
    st.info("Laden van overzicht...")

st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')} | Verversing elke 2 sec")

time.sleep(2)
st.rerun()
