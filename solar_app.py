import streamlit as st
import requests
import time
import pandas as pd
import io
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO + WEERSTATION ☀️🌦️
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://google.com{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxcc3gEUesc1ZDG7c1zhHvmh2B92zId1TT8hLYPz3dKxv1zIxQzybH5eqsHYkHczJE/exec" 

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Dashboard", page_icon="☀️", layout="centered")

tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
vandaag_iso = nu_lokaal.strftime('%Y-%m-%d')
vandaag_nl = nu_lokaal.strftime('%d-%m-%Y')

# --- DATA FUNCTIES ---
def sla_naar_sheets(s, g, t, oogst, start_kwh=None):
    try:
        payload = {"datum": vandaag_nl, "symo": s, "galvo": g, "totaal": t, "oogst": oogst, "start_kwh": start_kwh}
        r = requests.post(WEBAPP_URL, json=payload, timeout=10)
        return r.status_code == 200
    except: return False

def fetch_hw_data(url):
    try:
        r = requests.get(url, timeout=2).json()
        p = round(abs(float(r.get('active_power_w', 0))))
        k = float(r.get('total_power_export_t1_kwh', 0)) + float(r.get('total_power_export_t2_kwh', 0))
        return p, k, "🟢"
    except: return 0, None, "🔴"

def laad_geheugen_uit_sheet():
    try:
        res = requests.get(CSV_URL, timeout=10)
        if res.status_code == 200:
            df = pd.read_csv(io.StringIO(res.text))
            df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst', 'StartKWh'][:len(df.columns)]
            vandaag_data = df[df['Datum'] == vandaag_nl]
            if not vandaag_data.empty:
                rij = vandaag_data.iloc[-1]
                return float(rij['Symo']), float(rij['Galvo']), float(rij['Totaal']), float(rij['StartKWh']) if pd.notnull(rij['StartKWh']) else None
    except: pass
    return 0.0, 0.0, 0.0, None

# --- INITIALISATIE ---
if 'p_total_peak' not in st.session_state:
    s_p, g_p, t_p, s_kwh = laad_geheugen_uit_sheet()
    st.session_state.p_symo_peak, st.session_state.p_galvo_peak, st.session_state.p_total_peak = s_p, g_p, t_p
    st.session_state.start_kwh_dag = s_kwh

if st.session_state.get('huidige_datum') != vandaag_iso:
    st.session_state.update({'p_symo_peak':0.0, 'p_galvo_peak':0.0, 'p_total_peak':0.0, 'start_kwh_dag':None, 'huidige_datum':vandaag_iso})
    st.rerun()

# --- LIVE DATA ---
val_s, kwh_s, icon_s = fetch_hw_data(URL_1)
val_g, kwh_g, icon_g = fetch_hw_data(URL_2)
val_t = val_s + val_g

# Ochtend vastlegging
if kwh_s and kwh_g and st.session_state.start_kwh_dag is None:
    st.session_state.start_kwh_dag = kwh_s + kwh_g
    sla_naar_sheets(0, 0, 0, 0, st.session_state.start_kwh_dag)

oogst_vandaag = round((kwh_s + kwh_g) - st.session_state.start_kwh_dag, 2) if st.session_state.start_kwh_dag else 0.0

if val_t > st.session_state.p_total_peak:
    st.session_state.p_total_peak = val_t
    st.session_state.p_symo_peak, st.session_state.p_galvo_peak = max(val_s, st.session_state.p_symo_peak), max(val_g, st.session_state.p_galvo_peak)

# Opslag om 23:00
if nu_lokaal.strftime("%H:%M") >= "23:00" and st.session_state.get('laatste_opslag_datum') != vandaag_iso:
    if sla_naar_sheets(st.session_state.p_symo_peak, st.session_state.p_galvo_peak, st.session_state.p_total_peak, oogst_vandaag, st.session_state.start_kwh_dag):
        st.session_state.laatste_opslag_datum = vandaag_iso

# --- UI ---
st.title("☀️ Solar Dashboard")
st.write(f"⏰ {nu_lokaal.strftime('%H:%M')} | Live: **{val_t} W** | Oogst: **{oogst_vandaag} kWh**")
st.divider()

c1, c2, c3 = st.columns(3)
with c1: st.metric(f"{icon_s} Symo", f"{val_s} W", f"Piek: {st.session_state.p_symo_peak}")
with c2: st.metric(f"{icon_g} Galvo", f"{val_g} W", f"Piek: {st.session_state.p_galvo_peak}")
with c3: st.metric("☀️ Totaal", f"{val_t} W", f"Piek: {st.session_state.p_total_peak}")

st.divider()
if st.button("💾 Sla nu op (Back-up)"):
    if sla_naar_sheets(st.session_state.p_symo_peak, st.session_state.p_galvo_peak, st.session_state.p_total_peak, oogst_vandaag, st.session_state.start_kwh_dag):
        st.success("Opgeslagen!")
        time.sleep(1)
        st.rerun()

time.sleep(5)
st.rerun()
