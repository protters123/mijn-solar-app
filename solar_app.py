import streamlit as st
import requests
import time
import pandas as pd
import io
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - DE DEFINITIEVE FIX ☀️
# ==========================================

# DE DIRECTE CSV LINK
CSV_URL = "https://google.com"

# INVERTER IP'S
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
    # We halen de data op als tekst
    response = requests.get(CSV_URL, timeout=5)
    
    # We laden de data ZONDER rijen over te slaan (skiprows=0)
    # Zo pakken we alles wat Google Sheets stuurt
    df = pd.read_csv(io.StringIO(response.text))
    
    if not df.empty:
        # We hernoemen de kolommen handmatig zodat het altijd klopt
        # We gaan ervan uit dat je 4 kolommen hebt: Datum, Symo, Galvo, Totaal
        df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal']
        
        # We tonen de data direct, met de nieuwste rijen boven
        st.table(df.iloc[::-1])
    else:
        st.info("De spreadsheet lijkt leeg.")

except Exception as e:
    st.warning("Aan het wachten op de juiste tabeldata van Google...")

st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')} | Verversing elke 2 sec")

# Refresh pagina
time.sleep(2)
st.rerun()
