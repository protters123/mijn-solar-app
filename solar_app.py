import streamlit as st
import requests
import time
import os
from datetime import datetime

# ==========================================
# CONFIGURATIE - DENNIS SOLAR MONITOR
# ==========================================
PUBLIEK_IP = "94.110.235.108"

# Meter 1: Fronius Symo (Poort 8081)
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
PEAK_FILE_1 = "piek_symo.txt"

# Meter 2: Fronius Galvo (Poort 8082)
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"
PEAK_FILE_2 = "piek_galvo.txt"

# Totale Piek (Gecombineerd)
PEAK_FILE_TOTAL = "piek_totaal.txt"

# ==========================================
# FUNCTIES
# ==========================================
def get_peak(file):
    if os.path.exists(file):
        try:
            with open(file, "r") as f: return float(f.read())
        except: return 0.0
    return 0.0

def save_peak(file, value):
    with open(file, "w") as f: f.write(str(value))

def fetch_data(url):
    try:
        response = requests.get(url, timeout=3)
        return abs(float(response.json()['active_power_w']))
    except: return None

# ==========================================
# INTERFACE
# ==========================================
st.set_page_config(page_title="Solar Piek", page_icon="☀️", layout="centered")
st.title("☀️ Solar Piek")

# Data ophalen
val_symo = fetch_data(URL_1)
val_galvo = fetch_data(URL_2)

# Bereken Totaal
val_total = (val_symo or 0) + (val_galvo or 0) if (val_symo is not None or val_galvo is not None) else None

# Oude pieken laden
p_symo = get_peak(PEAK_FILE_1)
p_galvo = get_peak(PEAK_FILE_2)
p_total = get_peak(PEAK_FILE_TOTAL)

# Peak checks & opslaan
if val_symo and val_symo > p_symo:
    save_peak(PEAK_FILE_1, val_symo)
    p_symo = val_symo
if val_galvo and val_galvo > p_galvo:
    save_peak(PEAK_FILE_2, val_galvo)
    p_galvo = val_galvo
if val_total and val_total > p_total:
    save_peak(PEAK_FILE_TOTAL, val_total)
    p_total = val_total
    st.balloons() # Feestje bij een nieuw totaal-record!

# --- SECTIE 1: TOTAAL OVERZICHT ---
st.markdown("### 📊 Totaaloverzicht (Gecombineerd)")
st.info(f"Gecombineerde Piek: {p_total:,.0f} W")
t1, t2 = st.columns(2)
t1.metric("Live Totaal", f"{val_total:,.0f} W" if val_total is not None else "Offline")
t2.metric("🏆 Hoogste Totaal", f"{p_total:,.0f} W")

st.divider()

# --- SECTIE 2: INDIVIDUEEL ---
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🔹 Fronius Symo")
    st.metric("Nu", f"{val_symo:,.0f} W" if val_symo is not None else "Offline")
    st.metric("🏆 Piek symo", f"{p_symo:,.0f} W")

with col_b:
    st.subheader("🔸 Fronius Galvo")
    st.metric("Nu", f"{val_galvo:,.0f} W" if val_galvo is not None else "Offline")
    st.metric("🏆 Piek Galvo", f"{p_galvo:,.0f} W")

# Tijd & Auto-refresh
st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')} | Ververst elke 2 sec")
time.sleep(2)
st.rerun()
