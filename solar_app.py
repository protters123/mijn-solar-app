import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - DE DEFINITIEVE FIX
# ==========================================
PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

# JOUW GOOGLE SHEET EXPORT LINK
# Deze link zet je Sheet direct om in data die de app begrijpt
SHEET_ID = "1OeCoRbusZQjeXgnQi4YoKD1P8k84mHc0akqX2LizE3g"
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- RECORDS UIT SECRETS ---
if 'p_total' not in st.session_state:
    st.session_state.p_symo = st.secrets.get("symo_piek", 3711.0)
    st.session_state.p_galvo = st.secrets.get("galvo_piek", 6.0)
    st.session_state.p_total = st.secrets.get("totaal_piek", 3717.0)

def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

# --- DATA ---
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
st.title("☀️ Solar Piek Pro")
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

# --- GRAFIEK SECTIE ---
st.subheader("📅 Maandoverzicht")
try:
    # We lezen de data direct in via de CSV link
    df = pd.read_csv(CSV_URL)
    if not df.empty:
        # We pakken de eerste kolom (Datum) en de laatste (Piek_Totaal)
        df.columns = [c.strip() for c in df.columns]
        st.bar_chart(data=df, x=df.columns[0], y=df.columns[-1])
except:
    st.info("Grafiek wordt geladen zodra er data in de Google Sheet staat.")

st.caption(f"Check: {datetime.now().strftime('%H:%M:%S')} | 2 sec interval")
time.sleep(2)
st.rerun()
