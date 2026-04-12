import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO v6.0 - StartKWh & Weather Fix
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxZ_cOloEY5eA5zvHhfZfbvgARkMa3O59-AniXHpJ1hsUAo2hnguNx5BBFldnX5RacV/exec"

PUBLIEK_IP = "94.110.235.108"
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek PRO", page_icon="☀️", layout="centered")

tz = pytz.timezone('Europe/Brussels')
nu = datetime.now(tz)
vandaag_nl = nu.strftime('%d-%m-%Y')
vandaag_iso = nu.strftime('%Y-%m-%d')

# ====================== SESSION STATE ======================
if 'initialized' not in st.session_state or st.session_state.get('huidige_datum') != vandaag_iso:
    st.session_state.p_total_peak = 0.0
    st.session_state.start_kwh_dag = None
    st.session_state.huidige_datum = vandaag_iso
    st.session_state.initialized = True

# ====================== DATA LADEN ======================
all_time_peak = 0.0
try:
    df_full = pd.read_csv(CSV_URL, header=0, usecols=range(6))
    df_full.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWhdag']
    all_time_peak = pd.to_numeric(df_full['Totaal'], errors='coerce').max()

    vandaag = df_full[df_full['Datum'] == vandaag_nl]
    if not vandaag.empty:
        val_start = vandaag['StartKWhdag'].iloc[-1]
        if pd.notna(val_start) and float(val_start) > 0:
            st.session_state.start_kwh_dag = float(val_start)
except:
    pass

# ====================== FUNCTIES ======================
def sla_naar_sheets(s, g, t, oogst, start_kwh):
    try:
        payload = {
            "datum": vandaag_nl,
            "symo": round(float(s), 1),
            "galvo": round(float(g), 1),
            "totaal": round(float(t), 1),
            "oogst": round(float(oogst), 2),
            "start_kwh": round(float(start_kwh), 3) if start_kwh else 0,
            "actie": "update"
        }
        return requests.post(WEBAPP_URL, json=payload, timeout=10).status_code == 200
    except: return False

def fetch_hw_data(url):
    try:
        data = requests.get(url, timeout=3).json()
        power = round(abs(float(data.get('active_power_w', 0))))
        
        # PROBEER ALLE EXPORT VELDEN (HomeWizard kWh meters vs P1 meters)
        kwh = data.get('total_power_export_kwh') # 3-fase kWh meter
        if kwh is None:
            # P1 meter of gesplitste meter
            kwh = float(data.get('total_power_export_t1_kwh', 0)) + float(data.get('total_power_export_t2_kwh', 0))
            
        return power, float(kwh)
    except: return 0, 0

@st.cache_data(ttl=300)
def get_weather():
    try:
        r = requests.get("https://wttr.in|%C|%h&m&lang=nl", timeout=8)
        parts = r.text.strip().split('|')
        # Filter dubbele 'C' en 'Â'
        t_clean = parts[0].replace("Â", "").replace("C", "").strip()
        return f"{t_clean}°C", parts[1], parts[2]
    except: return "--°C", "Laden...", "--%"

# ====================== LIVE DATA & LOGICA ======================
val_s, kwh_s = fetch_hw_data(URL_1)
val_g, kwh_g = fetch_hw_data(URL_2)
val_t = val_s + val_g
kwh_totaal_nu = kwh_s + kwh_g

# Startwaarde vastleggen
if kwh_totaal_nu > 0 and st.session_state.start_kwh_dag is None:
    st.session_state.start_kwh_dag = kwh_totaal_nu

oogst_vandaag = 0.0
if st.session_state.start_kwh_dag:
    oogst_vandaag = round(max(0, kwh_totaal_nu - st.session_state.start_kwh_dag), 2)

if val_t > st.session_state.p_total_peak:
    st.session_state.p_total_peak = val_t

# Update sheets
sla_naar_sheets(val_s, val_g, st.session_state.p_total_peak, oogst_vandaag, st.session_state.start_kwh_dag)

# ====================== UI ======================
st.title("☀️ Solar Piek PRO")
st.caption(f"📍 Borgloon • {vandaag_nl} • {nu.strftime('%H:%M')}")

temp, desc, hum = get_weather()
w1, w2, w3 = st.columns(3)
with w1: st.metric("🌡️ Temp", temp)
with w2: st.markdown(f"**{desc}**")
with w3: st.metric("💧 Vocht", hum)

st.divider()
st.markdown(f"<h1 style='text-align:center;color:#FFB300;'>⚡ {val_t:,.0f} Watt</h1>", unsafe_allow_html=True)

c_a, c_b = st.columns(2)
with c_a: st.metric("📈 Oogst vandaag", f"{oogst_vandaag:.2f} kWh")
with c_b: st.metric("🏆 All Time Peak", f"{max(all_time_peak, st.session_state.p_total_peak):,.0f} W")

st.divider()
st.subheader("📜 Historiek")
try:
    st.dataframe(df_full.tail(10), use_container_width=True, hide_index=True)
except:
    st.info("Historiek laden...")

time.sleep(2)
st.rerun()
