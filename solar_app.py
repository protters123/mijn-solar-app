import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - DE DEFINITIEVE FIX ☀️
# ==========================================

# JOUW DIRECTE CSV LINK
CSV_URL = "https://google.com"

# INVERTER GEGEVENS
PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- LIVE DATA OPHALEN ---
def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

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
    # We lezen de data in en dwingen Pandas om de koppen te gebruiken
    df = pd.read_csv(CSV_URL)
    
    # We selecteren alleen de kolommen die we nodig hebben
    # Let op: De namen moeten EXACT zo in je sheet staan (hoofdlettergevoelig)
    if 'Datum' in df.columns:
        output_df = df[['Datum', 'Symo', 'Galvo', 'Totaal']]
        
        # We tonen de tabel (nieuwste boven)
        st.table(output_df.iloc[::-1])
    else:
        st.error("Kolom 'Datum' niet gevonden. Check de koppen in je Google Sheet.")
        st.write("Ik zie nu deze kolommen:", df.columns.tolist())

except Exception as e:
    st.info("Bezig met synchroniseren van Google Sheets...")

st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')} | Verversing elke 2 sec")
time.sleep(2)
st.rerun()
