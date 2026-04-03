import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - TABEL EDITIE ☀️
# ==========================================

# DE DIRECTE LINK DIE JE STUURDE (MOET PRECIES DEZE ZIJN)
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

# --- LIVE DATA ---
val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

if val_t > st.session_state.p_total: 
    st.session_state.p_total = val_t
    st.balloons()

# --- DASHBOARD UI ---
st.title("☀️ Solar Piek Pro") 
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")
st.metric("🏆 All-time Record", f"{st.session_state.p_total:,.0f} W")

st.divider()

# Live meters
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
    # Inlezen van de CSV
    df = pd.read_csv(CSV_URL)
    
    if not df.empty:
        # We pakken de kolommen op positie om fouten te voorkomen
        table_df = pd.DataFrame({
            'Datum': df.iloc[:, 0].astype(str),
            'Symo (W)': pd.to_numeric(df.iloc[:, 1], errors='coerce'),
            'Galvo (W)': pd.to_numeric(df.iloc[:, 2], errors='coerce'),
            'Totaal (W)': pd.to_numeric(df.iloc[:, 3], errors='coerce')
        }).dropna(how='all')

        # Kleur de getallen groen (alleen voor weergave)
        # Sorteer nieuwste bovenaan
        st.dataframe(
            table_df.iloc[::-1].style.format(precision=0).column_config(
                "Totaal (W)", help="Gecombineerde piek", width="medium"
            )
        )
    else:
        st.info("Spreadsheet is leeg.")
except Exception as e:
    st.error("Wacht op data van Google Sheets...")

st.caption(f"Laatste update: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(2)
st.rerun()
