import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - FINALE GRAFIEK FIX 💚
# ==========================================
PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

# JOUW GEPUBLICEERDE CSV LINK (GECORRIGEERD)
SHEET_URL = "https://google.com"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- RECORDS UIT SECRETS ---
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

# --- LIVE DATA ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# Update records in geheugen
if val_s > st.session_state.p_symo: st.session_state.p_symo = val_s
if val_g > st.session_state.p_galvo: st.session_state.p_galvo = val_g
if val_t > st.session_state.p_total: 
    st.session_state.p_total = val_t
    st.balloons()

# --- DISPLAY ---
st.title("💚 Solar Piek Pro")
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
st.metric("🏆 All-time Record", f"{st.session_state.p_total:,.0f} W")

st.divider()

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"### {icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
    st.caption(f"Record: {st.session_state.p_symo} W")
with c2:
    st.markdown(f"### {icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")
    st.caption(f"Record: {st.session_state.p_galvo} W")

st.divider()

# --- GRAFIEK (GEFORCEERD) ---
st.subheader("💚 Maandoverzicht")
try:
    # We downloaden de CSV data via de gecorrigeerde link
    df = pd.read_csv(SHEET_URL)
    if not df.empty:
        # We maken de kolomnamen schoon
        df.columns = [c.strip() for c in df.columns]
        # We dwingen de laatste kolom (Totaal) naar een getal voor de balkjes
        df.iloc[:, -1] = pd.to_numeric(df.iloc[:, -1], errors='coerce')
        # Teken de grafiek: X-as is de eerste kolom (Datum), Y-as is de laatste (Totaal)
        st.bar_chart(data=df, x=df.columns[0], y=df.columns[-1])
    else:
        st.info("Nog geen data gevonden in de sheet.")
except Exception as e:
    st.info("De grafiek verschijnt zodra de data uit Google Sheets binnenkomt.")

st.caption(f"Check: {datetime.now().strftime('%H:%M:%S')} | 2 sec interval")
time.sleep(2)
st.rerun()
