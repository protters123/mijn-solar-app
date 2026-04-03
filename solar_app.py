import streamlit as st
from streamlit_gsheets import GSheetsConnection
import requests
import time
import pandas as pd
from datetime import datetime

# ==========================================
# DENNIS SOLAR PIEK - DATABASE FIX
# ==========================================
PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

# JOUW GOOGLE SHEET LINK
SHEET_URL = "https://google.com"

st.set_page_config(page_title="Solar Piek", page_icon="☀️", layout="centered")
st.title("☀️ Solar Piek")

# Verbinding maken
conn = st.connection("gsheets", type=GSheetsConnection)

def get_peaks():
    try:
        # We lezen de hele sheet en pakken de eerste rij data
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        s = float(df["Symo_Piek"].iloc[0])
        g = float(df["Galvo_Piek"].iloc[0])
        t = float(df["Totaal_Piek"].iloc[0])
        return max(s, 3740.0), g, t
    except Exception:
        return 3740.0, 0.0, 3740.0

def save_peaks(s, g, t):
    try:
        # We maken een heel simpel tabelletje met exact dezelfde kolomnamen
        data_to_save = pd.DataFrame({
            "Symo_Piek": [s],
            "Galvo_Piek": [g],
            "Totaal_Piek": [t]
        })
        # We overschrijven de sheet met de nieuwe records
        conn.update(spreadsheet=SHEET_URL, data=data_to_save)
        return True
    except Exception as e:
        st.error(f"Fout details: {e}")
        return False

# --- PROGRAMMA ---
p_symo, p_galvo, p_total = get_peaks()

try:
    # Haal live data op
    res1 = requests.get(URL_1, timeout=3).json()
    res2 = requests.get(URL_2, timeout=3).json()
    
    val_symo = abs(float(res1['active_power_w']))
    val_galvo = abs(float(res2['active_power_w']))
    val_total = val_symo + val_galvo
    
    updated = False
    if val_symo > p_symo: p_symo = val_symo; updated = True
    if val_galvo > p_galvo: p_galvo = val_galvo; updated = True
    if val_total > p_total: p_total = val_total; updated = True
    
    if updated:
        if save_peaks(p_symo, p_galvo, p_total):
            if val_total > (p_total - 5): # Alleen vieren als het echt een nieuwe piek is
                st.balloons()

    # Display
    st.markdown(f"### 📊 Totaal: {val_total:,.0f} W")
    st.metric("🏆 Record Totaal", f"{p_total:,.0f} W")
    
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔹 Symo")
        st.metric("Nu", f"{val_symo:,.0f} W")
        st.metric("Piek", f"{p_symo:,.0f} W")
    with c2:
        st.subheader("🔸 Galvo")
        st.metric("Nu", f"{val_galvo:,.0f} W")
        st.metric("Piek", f"{p_galvo:,.0f} W")

except Exception:
    st.warning("⚠️ Live verbinding weg. Records uit Google Sheets zichtbaar.")
    st.metric("🏆 Hoogste Totaal (Record)", f"{p_total:,.0f} W")

st.caption(f"Check: {datetime.now().strftime('%H:%M:%S')} | Database: Google Sheets")
time.sleep(2)
st.rerun()
