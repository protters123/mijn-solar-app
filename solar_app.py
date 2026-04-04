import streamlit as st
import requests
import time
import pandas as pd
import io
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - DEFINITIEVE VERSIE ☀️
# ==========================================

# DE CORRECTE LINKS VOOR JOUW SPREADSHEET
SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv"

# INVERTER IP'S (Publiek IP voor externe toegang)
PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- RECORDS INITIALISEREN ---
if 'p_total' not in st.session_state:
    # We starten met de records die we in je historiek zien
    st.session_state.p_symo = 3711.0
    st.session_state.p_galvo = 6.0
    st.session_state.p_total = 3729.0 # Jouw hoogste record van 30 maart!

def fetch_status(url):
    """Haalt live wattage op van de omvormer API."""
    try:
        r = requests.get(url, timeout=2).json()
        val = abs(float(r.get('active_power_w', 0)))
        return val, "🟢"
    except: 
        return 0.0, "🔴"

# --- LIVE DATA OPHALEN ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# Update records in het geheugen tijdens deze sessie
if val_s > st.session_state.p_symo: st.session_state.p_symo = val_s
if val_g > st.session_state.p_galvo: st.session_state.p_galvo = val_g
if val_t > st.session_state.p_total: 
    st.session_state.p_total = val_t
    st.balloons() # Feestje bij een nieuw record!

# --- DASHBOARD UI ---
st.title("☀️ Solar Piek Pro") 
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
st.metric("🏆 All-time Record", f"{st.session_state.p_total:,.0f} W")

st.divider()

# Symo & Galvo live meters
c1, c2 = st.columns(2)
with c1:
    st.markdown(f"### {icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
    st.caption(f"Record: {st.session_state.p_symo:,.0f} W")
with c2:
    st.markdown(f"### {icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")
    st.caption(f"Record: {st.session_state.p_galvo:,.0f} W")

st.divider()

# --- TABEL SECTIE ---
st.subheader("💚 Maandoverzicht") 

try:
    response = requests.get(CSV_URL, timeout=5)
    if response.status_code == 200:
        df = pd.read_csv(io.StringIO(response.text))
        
        if not df.empty:
            # We bouwen een schone tabel en filteren eventuele tekst-regels eruit
            clean_df = pd.DataFrame({
                'Datum': df.iloc[:, 0].astype(str),
                'Symo (W)': pd.to_numeric(df.iloc[:, 1], errors='coerce'),
                'Galvo (W)': pd.to_numeric(df.iloc[:, 2], errors='coerce'),
                'Totaal (W)': pd.to_numeric(df.iloc[:, 3], errors='coerce')
            }).dropna(subset=['Totaal (W)']) # Filtert rommel-regels automatisch
            
            # Toon de tabel (nieuwste dag bovenaan)
            st.dataframe(clean_df.iloc[::-1], use_container_width=True, hide_index=True)
except Exception:
    st.info("De tabel wordt geladen vanuit Google Sheets...")

st.caption(f"Laatste update: {datetime.now().strftime('%H:%M:%S')} | Verversing elke 2 sec")

# Automatische refresh van de pagina
time.sleep(2)
st.rerun()
