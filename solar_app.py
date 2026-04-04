import streamlit as st
import requests
import time
import pandas as pd
import io
from datetime import datetime

# CONFIG
SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv&gid=0"

# INVERTERS
PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️")

# RECORDS
if 'p_total_rec' not in st.session_state:
    st.session_state.p_symo_rec = 3711.0
    st.session_state.p_galvo_rec = 6.0
    st.session_state.p_total_rec = 3717.0

def fetch_status(url):
    try:
        r = requests.get(url, timeout=1.5).json()
        return abs(float(r.get('active_power_w', 0))), "🟢"
    except: return 0.0, "🔴"

@st.cache_data(ttl=30)
def get_clean_data(url):
    try:
        response = requests.get(url, timeout=5)
        df = pd.read_csv(io.StringIO(response.text))
        
        # FIX: Hernoem kolommen & verwijder regels die namen herhalen (zoals op jouw screenshot)
        df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal']
        
        # Filter: Behoud alleen rijen waar 'Totaal' een echt getal is
        df['Totaal'] = pd.to_numeric(df['Totaal'], errors='coerce')
        df = df.dropna(subset=['Totaal'])
        
        return df.iloc[::-1] # Nieuwste eerst
    except: return None

# LIVE DATA
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# UPDATE RECORDS
if val_t > st.session_state.p_total_rec:
    st.session_state.p_total_rec = val_t
    st.balloons()

# UI
st.title("☀️ Solar Piek Pro")
st.metric("🏆 All-time Record", f"{st.session_state.p_total_rec:,.0f} W")

c1, c2 = st.columns(2)
c1.metric(f"{icon_s} Symo", f"{val_s:,.0f} W")
c2.metric(f"{icon_g} Galvo", f"{val_g:,.0f} W")

st.divider()

# TABEL ZONDER FOUTEN
st.subheader("💚 Historiek")
history = get_clean_data(CSV_URL)
if history is not None:
    st.dataframe(history, use_container_width=True, hide_index=True)
else:
    st.error("Kan spreadsheet niet laden.")

time.sleep(2)
st.rerun()
