import streamlit as st
import requests
import time
import os
from datetime import datetime

# ==========================================
# CONFIGURATIE - HOMEWIZARD KWH METER
# ==========================================
HW_IP = "94.110.235.108:8081"  # Jouw HomeWizard IP-adres
URL = f"http://{HW_IP}/api/v1/data"
PEAK_FILE = "hoogste_piek.txt"

# ==========================================
# FUNCTIES VOOR DATA & OPSLAG
# ==========================================
def get_saved_peak():
    if os.path.exists(PEAK_FILE):
        try:
            with open(PEAK_FILE, "r") as f:
                return float(f.read())
        except:
            return 0.0
    return 0.0

def save_new_peak(value):
    with open(PEAK_FILE, "w") as f:
        f.write(str(value))

def fetch_homewizard_data():
    try:
        response = requests.get(URL, timeout=3)
        data = response.json()
        # Bij een kWh meter voor zonnepanelen kijken we naar 'active_power_w'
        # We gebruiken abs() omdat opwekking soms als negatief getal wordt getoond
        wattage = abs(float(data['active_power_w']))
        return wattage
    except Exception as e:
        return None

# ==========================================
# DE INTERFACE (GSM VRIENDELIJK)
# ==========================================
st.set_page_config(page_title="Zonne-Piek Monitor", page_icon="⚡")

st.title("⚡ HomeWizard Solar Piek")
st.subheader("Live opbrengst van je panelen")

# Haal data op
current_w = fetch_homewizard_data()
old_peak = get_saved_peak()

# Check voor nieuwe record-piek
if current_w is not None and current_w > old_peak:
    save_new_peak(current_w)
    st.balloons() # Feestje op je scherm bij een record!
    highest_peak = current_w
else:
    highest_peak = old_peak

# Weergave in grote blokken
col1, col2 = st.columns(2)

with col1:
    if current_w is not None:
        st.metric(label="Huidige Opwekking", value=f"{current_w:,.0f} W")
    else:
        st.error("Meter niet gevonden")
        st.info("Check of 'Lokale API' aanstaat in de HomeWizard app.")

with col2:
    st.metric(label="🏆 Hoogste Piek Ooit", value=f"{highest_peak:,.0f} W")

# Tijdstip van laatste meting
now = datetime.now().strftime("%H:%M:%S")
st.caption(f"Laatste update: {now} | Ververst elke 5 seconden")

# Grafiek van de laatste metingen
if 'history' not in st.session_state:
    st.session_state.history = []

if current_w is not None:
    st.session_state.history.append(current_w)
    if len(st.session_state.history) > 60: # Laatste minuut bij 5s interval
        st.session_state.history.pop(0)

if st.session_state.history:
    st.line_chart(st.session_state.history)

# Automatische herstart van het script voor live updates
time.sleep(5)
st.rerun()
