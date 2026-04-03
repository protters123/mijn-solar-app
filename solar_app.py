import streamlit as st
from streamlit_gsheets import GSheetsConnection
import requests
import time
import pandas as pd
from datetime import datetime

# ==========================================
# DENNIS SOLAR PIEK - CLOUD DATABASE VERSIE
# ==========================================
PUBLIEK_IP = "94.110.235.108"
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

# JOUW GOOGLE SHEET LINK (NU CORRECT INGEVULD)
SHEET_URL = "https://google.com"

st.set_page_config(page_title="Solar Piek", page_icon="☀️", layout="centered")
st.title("☀️ Solar Piek")

# Maak verbinding met Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCTIE: RECORDS OPHALEN ---
def get_peaks():
    try:
        # Lees de data uit de sheet
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        s = float(df.iloc[0, 0]) # Symo_Piek (Kolom A)
        g = float(df.iloc[0, 1]) # Galvo_Piek (Kolom B)
        t = float(df.iloc[0, 2]) # Totaal_Piek (Kolom C)
        return s, g, t
    except Exception as e:
        # Als de sheet leeg is of niet bereikbaar, gebruik deze startwaardes
        return 3740.0, 0.0, 0.0

# --- FUNCTIE: RECORDS OPSLAAN ---
def save_peaks(s, g, t):
    # Maak een tabelletje om terug te schrijven naar de eerste rij onder de titels
    new_df = pd.DataFrame([[s, g, t]], columns=["Symo_Piek", "Galvo_Piek", "Totaal_Piek"])
    conn.update(spreadsheet=SHEET_URL, data=new_df)

# --- HOOFDPROGRAMMA ---
p_symo, p_galvo, p_total = get_peaks()

try:
    # Live data ophalen van je beide meters thuis
    res1 = requests.get(URL_1, timeout=2).json()
    res2 = requests.get(URL_2, timeout=2).json()
    
    val_symo = abs(float(res1['active_power_w']))
    val_galvo = abs(float(res2['active_power_w']))
    val_total = val_symo + val_galvo
    
    # Check voor nieuwe records
    updated = False
    if val_symo > p_symo: p_symo = val_symo; updated = True
    if val_galvo > p_galvo: p_galvo = val_galvo; updated = True
    if val_total > p_total: 
        p_total = val_total; updated = True
        st.balloons() # Feestje!
    
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
    # Dit verschijnt als de meters thuis niet bereikbaar zijn (bijv. poort dicht of IP veranderd)
    st.warning("Verbinden met meters thuis mislukt...")
    st.info(f"Huidige records uit database: Symo {p_symo}W | Galvo {p_galvo}W")

# Tijd & Refresh
st.caption(f"Laatste check: {datetime.now().strftime('%H:%M:%S')} | Gegevensbron: Google Sheets")
time.sleep(2)
st.rerun()
