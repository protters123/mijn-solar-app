import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - TABEL OVERZICHT ☀️
# ==========================================

# JOUW DIRECTE CSV LINK
CSV_URL = "https://google.com"

# INVERTER GEGEVENS
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
    except: return 0.0, "🔴"

# --- LIVE DATA OPHALEN ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# Update records
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

# Symo & Galvo sectie
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
    df = pd.read_csv(CSV_URL)
    
    if not df.empty:
        # We maken de tabel precies zoals in je screenshot: Datum, Symo, Galvo, Totaal
        table_df = pd.DataFrame({
            'Datum': df['Datum'].astype(str),
            'Symo (W)': df['Symo'],
            'Galvo (W)': df['Galvo'],
            'Totaal (W)': df['Totaal']
        }).dropna(how='all') # Verwijdert lege rijen
        
        # Sorteer: Nieuwste dag bovenaan
        st.table(table_df.iloc[::-1])
    else:
        st.info("Nog geen historische data gevonden.")
except Exception as e:
    st.error(f"Fout bij laden tabel: {e}")


st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')} | 2 sec interval")

# Refresh de pagina elke 2 seconden
time.sleep(2)
st.rerun()
