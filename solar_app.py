import streamlit as st
import requests
import time
import pandas as pd
import io
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - GEOPTIMALISEERDE VERSIE ☀️
# ==========================================

# CONFIGURATIE
SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
# DE CORRECTE URL VOOR GOOGLE SHEETS CSV EXPORT:
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv"

# INVERTER IP'S
PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- RECORDS INITIALISEREN (SESSION STATE) ---
if 'p_total_rec' not in st.session_state:
    st.session_state.p_symo_rec = st.secrets.get("symo_piek", 3711.0)
    st.session_state.p_galvo_rec = st.secrets.get("galvo_piek", 6.0)
    st.session_state.p_total_rec = st.secrets.get("totaal_piek", 3717.0)

# --- FUNCTIES ---
def fetch_status(url):
    """Haalt live data op van de omvormer API."""
    try:
        r = requests.get(url, timeout=1.5).json()
        val = abs(float(r.get('active_power_w', 0)))
        return val, "🟢"
    except Exception:
        return 0.0, "🔴"

@st.cache_data(ttl=60) # Cache de spreadsheet voor 60 seconden om verbanning te voorkomen
def get_table_data(url):
    """Haalt de geschiedenis op uit Google Sheets."""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
            # Selecteer eerste 4 kolommen: Datum, Symo, Galvo, Totaal
            clean_df = pd.DataFrame({
                'Datum': df.iloc[:, 0].astype(str),
                'Symo (W)': pd.to_numeric(df.iloc[:, 1], errors='coerce'),
                'Galvo (W)': pd.to_numeric(df.iloc[:, 2], errors='coerce'),
                'Totaal (W)': pd.to_numeric(df.iloc[:, 3], errors='coerce')
            }).dropna(subset=['Datum'])
            return clean_df.iloc[::-1] # Nieuwste bovenaan
    except Exception:
        return None
    return None

# --- LIVE DATA VERWERKEN ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# Update records en vier feest bij nieuw record
if val_s > st.session_state.p_symo_rec: st.session_state.p_symo_rec = val_s
if val_g > st.session_state.p_galvo_rec: st.session_state.p_galvo_rec = val_g
if val_t > st.session_state.p_total_rec: 
    st.session_state.p_total_rec = val_t
    st.balloons()

# --- DASHBOARD UI ---
st.title("☀️ Solar Piek Pro") 
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
st.metric("🏆 All-time Record", f"{st.session_state.p_total_rec:,.0f} W")

st.divider()

# Symo & Galvo live meters
c1, c2 = st.columns(2)
with c1:
    st.markdown(f"### {icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
    st.caption(f"Record: {st.session_state.p_symo_rec:,.0f} W")
with c2:
    st.markdown(f"### {icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")
    st.caption(f"Record: {st.session_state.p_galvo_rec:,.0f} W")

st.divider()

# --- TABEL SECTIE ---
st.subheader("💚 Maandoverzicht") 
history_df = get_table_data(CSV_URL)

if history_df is not None and not history_df.empty:
    st.table(history_df.head(10)) # Toon de laatste 10 metingen
else:
    st.info("Wachten op verbinding met Google Sheets...")

st.caption(f"Laatste update: {datetime.now().strftime('%H:%M:%S')} | Verversing elke 2 sec")

# --- AUTO-REFRESH ---
time.sleep(2)
st.rerun()
