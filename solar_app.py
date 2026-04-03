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

# JOUW GOOGLE SHEET LINK
SHEET_URL = "https://google.com"

st.set_page_config(page_title="Solar Piek", page_icon="☀️", layout="centered")
st.title("☀️ Solar Piek")

# Maak verbinding met Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCTIE: RECORDS OPHALEN ---
def get_peaks():
    try:
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        # We pakken de eerste rij data (na de titels)
        s = float(df.iloc[0, 0]) 
        g = float(df.iloc[0, 1]) 
        t = float(df.iloc[0, 2]) 
        # Gebruik 3740 als absolute bodem voor de Symo
        return max(s, 3740.0), g, t
    except Exception:
        return 3740.0, 0.0, 3740.0

# --- FUNCTIE: RECORDS OPSLAAN ---
def save_peaks(s, g, t):
    try:
        new_df = pd.DataFrame([[s, g, t]], columns=["Symo_Piek", "Galvo_Piek", "Totaal_Piek"])
        conn.update(spreadsheet=SHEET_URL, data=new_df)
    except Exception:
        st.error("Opslaan in database mislukt!")

# --- HOOFDPROGRAMMA ---
p_symo, p_galvo, p_total = get_peaks()

try:
    # Live data ophalen van je beide meters thuis
    res1 = requests.get(URL_1, timeout=3).json()
    res2 = requests.get(URL_2, timeout=3).json()
    
    val_symo = abs(float(res1['active_power_w']))
    val_galvo = abs(float(res2['active_power_w']))
    val_total = val_symo + val_galvo
    
    # Check voor nieuwe records
    updated = False
    
    if val_symo > p_symo:
        p_symo = val_symo
        updated = True
        
    if val_galvo > p_galvo:
        p_galvo = val_galvo
        updated = True
        
    if val_total > (p_total + 5): # Alleen ballonnen bij een duidelijke verbetering (>5W)
        p_total = val_total
        updated = True
        st.balloons()
    elif val_total > p_total: # Wel opslaan, maar geen ballonnen bij kleine stapjes
        p_total = val_total
        updated = True
    
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
    st.warning("⚠️ Live verbinding verbroken. Database-waarden zichtbaar.")
    st.metric("🏆 Hoogste Totaal (Record)", f"{p_total:,.0f} W")

# Tijd & Refresh
st.caption(f"Laatste check: {datetime.now().strftime('%H:%M:%S')} | Bron: Google Sheets")
time.sleep(2)
st.rerun()
