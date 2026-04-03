import streamlit as st
import requests
import time
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# SOLAR PIEK PRO - STATUS & HISTORIEK
# ==========================================
PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

# JOUW CORRECTE GOOGLE SHEET LINK
SHEET_URL = "https://google.com"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- RECORDS LADEN UIT SECRETS ---
if 'p_symo' not in st.session_state:
    st.session_state.p_symo = st.secrets.get("symo_piek", 3740.0)
    st.session_state.p_galvo = st.secrets.get("galvo_piek", 0.0)
    st.session_state.p_total = st.secrets.get("totaal_piek", 3740.0)

# Verbinding voor de grafiek
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_data_with_status(url):
    try:
        res = requests.get(url, timeout=2).json()
        val = abs(float(res['active_power_w']))
        return val, "🟢" # Groen bolletje voor Online
    except:
        return 0.0, "🔴" # Rood bolletje voor Offline

# --- DATA OPHALEN ---
val_s, icon_s = fetch_data_with_status(URL_1)
val_g, icon_g = fetch_data_with_status(URL_2)
val_t = val_s + val_g

# Update records in geheugen
if val_s > st.session_state.p_symo: st.session_state.p_symo = val_s
if val_g > st.session_state.p_galvo: st.session_state.p_galvo = val_g
if val_t > st.session_state.p_total: 
    st.session_state.p_total = val_t
    st.balloons()

# --- DISPLAY ---
st.title("☀️ Solar Piek Pro")

# Totaaloverzicht
st.markdown(f"### 📊 Totaal Live: {val_t:,.0f} W")
st.metric("🏆 All-time Record", f"{st.session_state.p_total:,.0f} W")

st.divider()

# Individuele status met bolletjes
c1, c2 = st.columns(2)
with c1:
    st.subheader(f"{icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
    st.caption(f"Piek Symo: {st.session_state.p_symo} W")

with c2:
    st.subheader(f"{icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")
    st.caption(f"Piek Galvo: {st.session_state.p_galvo} W")

st.divider()

# --- MAANDOVERZICHT ---
st.subheader("📅 Maandoverzicht Hoogste Pieken")
try:
    # We lezen alleen als de link correct is
    if "docs.google.com" in SHEET_URL:
        df_hist = conn.read(spreadsheet=SHEET_URL, worksheet="Historiek", ttl=0)
        if not df_hist.empty:
            st.bar_chart(df_hist.set_index("Datum")["Piek_Totaal"])
        else:
            st.info("Nog geen data in tabblad 'Historiek' gevonden.")
except Exception:
    st.caption("Grafiek tijdelijk niet beschikbaar.")

st.caption(f"Check: {datetime.now().strftime('%H:%M:%S')} | 2 sec interval")
time.sleep(2)
st.rerun()
