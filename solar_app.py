import streamlit as st
from streamlit_gsheets import GSheetsConnection
import requests
import time
import pandas as pd
from datetime import datetime

# ==========================================
# DENNIS SOLAR PIEK - CLOUD DATABASE VERSIE
# ==========================================
PUBLIEK_IP = "162.120.187.55"
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

# JOUW GOOGLE SHEET LINK
SHEET_URL = "https://google.com"

st.set_page_config(page_title="Solar Piek", page_icon="☀️", layout="centered")
st.title("☀️ Solar Piek")

# Maak verbinding met Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCTIE: RECORDS OPHALEN ---
def get_peaks():
    try:
        # Lees rij 2 van de sheet
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        s = float(df.iloc[0, 0]) # Symo_Piek
        g = float(df.iloc[0, 1]) # Galvo_Piek
        t = float(df.iloc[0, 2]) # Totaal_Piek
        return s, g, t
    except Exception as e:
        # Als er iets misgaat, gebruik dan deze startwaardes
        return 3740.0, 0.0, 0.0

# --- FUNCTIE: RECORDS OPSLAAN ---
def save_peaks(s, g, t):
    # Maak een tabelletje om terug te schrijven
    new_df = pd.DataFrame([[s, g, t]], columns=["Symo_Piek", "Galvo_Piek", "Totaal_Piek"])
    conn.update(spreadsheet=SHEET_URL, data=new_df)

# --- HOOFDPROGRAMMA ---
p_symo, p_galvo, p_total = get_peaks()

try:
    # Live data ophalen
    val_symo = abs(float(requests.get(URL_1, timeout=2).json()['active_power_w']))
    val_galvo = abs(float(requests.get(URL_2, timeout=2).json()['active_power_w']))
    val_total = val_symo + val_galvo
    
    # Check voor nieuwe records
    updated = False
    if val_symo > p_symo: p_symo = val_symo; updated = True
    if val_galvo > p_galvo: p_galvo = val_galvo; updated = True
    if val_total > p_total: 
        p_total = val_total; updated = True
        st.balloons() # Feestje bij nieuw totaal-record!
    
    # Sla alleen op in Google Sheets als er een NIEUW record is
    if updated:
        save_peaks(p_symo, p_galvo, p_total)

    # Display op scherm
    st.markdown(f"### 📊 Totaaloverzicht: {val_total:,.0f} W")
    st.metric("🏆 Hoogste Totaal Ooit", f"{p_total:,.0f} W")
    
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
    st.warning("Aan het verbinden met HomeWizard...")

# Tijd & Refresh
st.caption(f"Laatste check: {datetime.now().strftime('%H:%M:%S')} | Database: Google Sheets")
time.sleep(2)
st.rerun()

