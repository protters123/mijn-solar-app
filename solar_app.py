import streamlit as st
import requests
import time
import os
from datetime import datetime

# ==========================================
# CONFIGURATIE - TWEE METERS (VIA CLOUD)
# ==========================================
PUBLIEK_IP = "94.110.235.108"

# Meter 1 (Poort 8081)
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
PEAK_FILE_1 = "piek_meter_1.txt"

# Meter 2 (Poort 8082)
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"
PEAK_FILE_2 = "piek_meter_2.txt"

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
st.set_page_config(page_title="Dual Solar Monitor", page_icon="⚡", layout="centered")
st.title("⚡ HomeWizard Dual Monitor")

# Data ophalen
val1 = fetch_data(URL_1)
val2 = fetch_data(URL_2)
p1 = get_peak(PEAK_FILE_1)
p2 = get_peak(PEAK_FILE_2)

# Peak checks
if val1 and val1 > p1:
    save_peak(PEAK_FILE_1, val1)
    p1 = val1
if val2 and val2 > p2:
    save_peak(PEAK_FILE_2, val2)
    p2 = val2

# Weergave Meter 1
st.subheader("☀️ Meter 1 (Zonnepanelen)")
c1, c2 = st.columns(2)
c1.metric("Nu", f"{val1:,.0f} W" if val1 is not None else "Offline")
c2.metric("🏆 Piek", f"{p1:,.0f} W")

st.divider()

# Weergave Meter 2
st.subheader("🔋 Meter 2 (Extra Groep)")
c3, c4 = st.columns(2)
c3.metric("Nu", f"{val2:,.0f} W" if val2 is not None else "Offline")
c4.metric("🏆 Piek", f"{p2:,.0f} W")

st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')} | 5 sec interval")
time.sleep(5)
st.rerun()

