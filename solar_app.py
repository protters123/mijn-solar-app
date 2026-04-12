import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO v9.0 - DE DEFINITIEVE FIX
# ==========================================

# Herstel van de originele werkende URL's
SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbyhiYefAqGxI8YXZ0Jm4UqSo2pQ6pO6Ip6ciRGEEWQdXaXl14XR7L83G1ivg0f9VV2r/exec"

PUBLIEK_IP = "94.110.235.108"
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek PRO", page_icon="☀️", layout="centered")

tz = pytz.timezone('Europe/Brussels')
nu = datetime.now(tz)
vandaag_nl = nu.strftime('%d-%m-%Y')
vandaag_iso = nu.strftime('%Y-%m-%d')

# --- ROBUUSTE INITIALISATIE ---
if 'huidige_datum' not in st.session_state or st.session_state.huidige_datum != vandaag_iso:
    st.session_state.huidige_datum = vandaag_iso
    st.session_state.p_total_peak = 0.0
    st.session_state.p_symo_peak = 0.0
    st.session_state.p_galvo_peak = 0.0
    st.session_state.start_kwh_dag = None
    st.session_state.last_sheet_update = 0

# ====================== DATA LADEN ======================
all_time_peak = 3729.0
try:
    df_raw = pd.read_csv(CSV_URL, header=0)
    df_full = df_raw.iloc[:, :6]
    df_full.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWhdag']
    atp = pd.to_numeric(df_full['Totaal'], errors='coerce').max()
    if atp > 0: all_time_peak = atp
    
    # Forceer de startwaarde uit de sheet als we die nog niet hebben
    if st.session_state.start_kwh_dag is None:
        vandaag_df = df_full[df_full['Datum'] == vandaag_nl]
        if not vandaag_df.empty:
            val_start = vandaag_df['StartKWhdag'].iloc[-1]
            if pd.notna(val_start) and float(val_start) > 0:
                st.session_state.start_kwh_dag = float(val_start)
except:
    pass

# ====================== FUNCTIES ======================
def sla_naar_sheets(s, g, t, oogst, start_kwh, force=False):
    nu_ts = time.time()
    # Snelle sync: elke 15 seconden voor live-gevoel
    if force or (nu_ts - st.session_state.last_sheet_update > 15):
        try:
            payload = {"datum": vandaag_nl, "symo": int(s), "galvo": int(g), "totaal": int(t), "oogst": float(oogst), "start_kwh": float(start_kwh), "actie": "update"}
            requests.post(WEBAPP_URL, json=payload, timeout=5)
            st.session_state.last_sheet_update = nu_ts
        except:
            pass

def fetch_hw_data(url):
    try:
        r = requests.get(url, timeout=3).json()
        raw_p = abs(float(r.get('active_power_w', 0)))
        power = round(raw_p) if raw_p >= 10 else 0
        kwh = float(r.get('total_power_export_kwh', 0))
        if kwh == 0:
            kwh = float(r.get('total_power_export_t1_kwh', 0)) + float(r.get('total_power_export_t2_kwh', 0))
        return power, kwh, "🟢"
    except:
        return 0, 0, "🔴"

@st.cache_data(ttl=600)
def get_weather():
    try:
        r = requests.get("https://wttr.in|%C|%h&lang=nl", timeout=10)
        p = r.text.strip().split('|')
        return p[0].replace("+",""), p[1], p[2], "🌤️"
    except:
        return "12°C", "Bewolkt", "70%", "☁️"

# ====================== LIVE DATA ======================
val_s, kwh_s, dot_s = fetch_hw_data(URL_1)
val_g, kwh_g, dot_g = fetch_hw_data(URL_2)
val_t = val_s + val_g
kwh_nu = kwh_s + kwh_g

# Oogst beveiliging: zet startwaarde bij eerste meting
if kwh_nu > 0 and st.session_state.start_kwh_dag is None:
    st.session_state.start_kwh_dag = kwh_nu

# Berekening Oogst met hoge precisie
oogst_vandaag = round(max(0.0, kwh_nu - st.session_state.start_kwh_dag), 3)

# Update dagpiek
if val_t > st.session_state.p_total_peak:
    st.session_state.p_total_peak = val_t
    st.session_state.p_symo_peak, st.session_state.p_galvo_peak = val_s, val_g

# Direct naar sheets
sla_naar_sheets(val_s, val_g, st.session_state.p_total_peak, oogst_vandaag, st.session_state.start_kwh_dag)

# ====================== UI ======================
st.title("☀️ Solar Piek PRO")
t, d, h, i = get_weather()
c_w1, c_w2, c_w3 = st.columns(3)
c_w1.metric("🌡️ Temp", t)
c_w2.metric("☁️ Weer", d)
c_w3.metric("💧 Vocht", h)

st.divider()
st.markdown(f"<h1 style='text-align:center;color:#FFB300;'>⚡ {val_t:,.0f} Watt</h1>", unsafe_allow_html=True)
st.progress(min(val_t / 8000, 1.0))

ca, cb = st.columns(2)
ca.metric("📈 Oogst vandaag", f"{oogst_vandaag:.3f} kWh")
cb.metric("🏆 Dag Piek", f"{st.session_state.p_total_peak:,.0f} W")

st.divider()
c1, c2, c3 = st.columns(3)
c1.metric(f"{dot_s} Symo", f"{val_s} W", f"Piek: {st.session_state.p_symo_peak} W")
c2.metric(f"{dot_g} Galvo", f"{val_g} W", f"Piek: {st.session_state.p_galvo_peak} W")
c3.metric("☀️ Totaal", f"{val_t} W", f"Piek: {st.session_state.p_total_peak} W")

st.divider()
if st.button("🔄 Reset Oogst (Start nu op 0.000)"):
    st.session_state.start_kwh_dag = kwh_nu
    sla_naar_sheets(val_s, val_g, st.session_state.p_total_peak, 0, kwh_nu, force=True)
    st.rerun()

time.sleep(2)
st.rerun()
