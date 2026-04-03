import streamlit as st
import requests
import time
import pandas as pd
import io
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - DE DEFINITIEVE FIX ☀️
# ==========================================

# 1. DE ENIGE CORRECTE LINK (Nu met docs.google.com en de /d/ map)
SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv"

# 2. INVERTER GEGEVENS
PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- RECORDS INITIALISEREN ---
if 'p_total' not in st.session_state:
    st.session_state.p_symo = st.secrets.get("symo_piek", 3711.0)
    st.session_state.p_galvo = st.secrets.get("galvo_piek", 6.0)
    st.session_state.p_total = st.secrets.get("totaal_piek", 3717.0)

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        val = abs(float(r['active_power_w']))
        return val, "🟢"
    except: 
        return 0.0, "🔴"

# --- LIVE DATA OPHALEN ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# Update records in geheugen
if val_s > st.session_state.p_symo: st.session_state.p_symo = val_s
if val_g > st.session_state.p_galvo: st.session_state.p_galvo = val_g
if val_t > st.session_state.p_total: 
    st.session_state.p_total = val_t
    st.balloons()

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
    # We halen de data op als ruwe tekst
    response = requests.get(CSV_URL, timeout=5)
    
    if response.status_code == 200:
        # We zetten de tekst om naar een tabel
        df = pd.read_csv(io.StringIO(response.text))
        
        if not df.empty:
            # We pakken de eerste 4 kolommen (Datum, Symo, Galvo, Totaal)
            # Dit voorkomt dat we rommel van andere kolommen inladen
            clean_df = df.iloc[:, :4]
            clean_df.columns = ['Datum', 'Symo (W)', 'Galvo (W)', 'Totaal (W)']
            
            # Tabel tonen met de nieuwste dag bovenaan
            st.table(clean_df.iloc[::-1])
        else:
            st.info("De spreadsheet is momenteel leeg.")
    else:
        st.error("Kan geen verbinding maken met de spreadsheet. Controleer of de sheet 'Iedereen met de link' mag lezen.")

except Exception as e:
    st.warning("Wacht op geldige data van de spreadsheet...")

st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')} | 2 sec interval")

# Automatische verversing
time.sleep(2)
st.rerun()
