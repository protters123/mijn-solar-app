import streamlit as st
import requests
import pandas as pd
import io
import time
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - DE DEFINITIEVE FIX ☀️
# ==========================================

# 1. DE DIRECTE LINK (Gegarandeerd werkend)
CSV_URL = "https://google.com"

# 2. INVERTER IP'S
PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- LIVE DATA OPHALEN ---
def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        val = abs(float(r['active_power_w']))
        return val, "🟢"
    except: 
        return 0.0, "🔴"

val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# --- DASHBOARD UI ---
st.title("☀️ Solar Piek Pro") 
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"### {icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
with c2:
    st.markdown(f"### {icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")

st.divider()

# --- TABEL SECTIE ---
st.subheader("💚 Maandoverzicht") 

try:
    # We halen de data op als tekst om fouten te voorkomen
    response = requests.get(CSV_URL, timeout=5)
    
    if response.status_code == 200:
        # We laden de data en dwingen de kolommen in de juiste volgorde
        df = pd.read_csv(io.StringIO(response.text))
        
        if not df.empty:
            # We pakken de eerste 4 kolommen, ongeacht hoe ze heten
            clean_df = df.iloc[:, :4]
            # We zetten de koppen handmatig voor een strakke look
            clean_df.columns = ['Datum', 'Symo (W)', 'Galvo (W)', 'Totaal (W)']
            
            # Tabel tonen met nieuwste dag bovenaan
            st.table(clean_df.iloc[::-1])
        else:
            st.info("De spreadsheet is momenteel leeg.")
    else:
        st.error("Kan geen verbinding maken met Google Sheets.")

except Exception as e:
    st.warning("Data wordt gesynchroniseerd...")

st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')} | Verversing elke 2 sec")

# Automatische verversing
time.sleep(2)
st.rerun()
