import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO v7.2 - URL & Emoji Fix
# ==========================================

# VOLLEDIGE URL'S (Hardcoded om fouten te voorkomen)
CSV_URL = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbyhiYefAqGxI8YXZ0Jm4UqSo2pQ6pO6Ip6ciRGEEWQdXaXl14XR7L83G1ivg0f9VV2r/exec"

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
    st.session_state.p_symo_peak = 0.0
    st.session_state.p_galvo_peak = 0.0
    st.session_state.start_kwh_dag = None
    st.session_state.huidige_datum = vandaag_iso
    st.session_state.initialized = True

# ====================== DATA LADEN ======================
all_time_peak = 3729.0
df_display = pd.DataFrame()

try:
    df_raw = pd.read_csv(CSV_URL, header=0)
    df_full = df_raw.iloc[:, :6]
    df_full.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWhdag']
    
    atp = pd.to_numeric(df_full['Totaal'], errors='coerce').max()
    if atp > 0: all_time_peak = atp

    vandaag_df = df_full[df_full['Datum'] == vandaag_nl]
    if not vandaag_df.empty:
        val_start = vandaag_df['StartKWhdag'].iloc[-1]
        if pd.notna(val_start): st.session_state.start_kwh_dag = float(val_start)
        v_totaal = pd.to_numeric(vandaag_df['Totaal'], errors='coerce').max()
        if pd.notna(v_totaal): st.session_state.p_total_peak = float(v_totaal)
    
    df_display = df_full.tail(15)
except Exception as e:
    st.error(f"Sheet Error: {e}")

# ====================== FUNCTIES ======================
def sla_naar_sheets(s, g, t, oogst, start_kwh):
    try:
        payload = {
            "datum": vandaag_nl, "symo": round(float(s), 1), "galvo": round(float(g), 1),
            "totaal": round(float(t), 1), "oogst": round(float(oogst), 2),
            "start_kwh": round(float(start_kwh), 3) if start_kwh else 0, "actie": "update"
        }
        requests.post(WEBAPP_URL, json=payload, timeout=5)
    except: pass

def fetch_hw_data(url):
    try:
        r = requests.get(url, timeout=3).json()
        power = round(abs(float(r.get('active_power_w', 0))))
        kwh = float(r.get('total_power_export_t1_kwh', 0)) + float(r.get('total_power_export_t2_kwh', 0))
        return power, kwh
    except: return 0, 0

@st.cache_data(ttl=300)
def get_weather():
    try:
        r = requests.get("https://wttr.in|%C|%h&m&lang=nl", timeout=10)
        parts = r.text.strip().split('|')
        t_clean = parts[0].replace("Â", "").replace("C", "").replace("+", "").strip()
        temp = f"{t_clean}°C"
        desc = parts[1].strip()
        hum = parts[2].strip()
        d = desc.lower()
        icon = "☀️" if any(x in d for x in ["zon","helder"]) else "⛅" if "licht" in d else "☁️" if "bewolkt" in d else "🌧️" if "regen" in d else "🌤️"
        return temp, desc, hum, icon
    except: return "?°C", "Laden...", "?", "⛅"

# ====================== LOGICA ======================
val_s, kwh_s = fetch_hw_data(URL_1)
val_g, kwh_g = fetch_hw_data(URL_2)
val_t, kwh_nu = val_s + val_g, kwh_s + kwh_g

if kwh_nu > 0 and st.session_state.start_kwh_dag is None:
    st.session_state.start_kwh_dag = kwh_nu

oogst_vandaag = round(max(0, kwh_nu - st.session_state.start_kwh_dag), 2) if st.session_state.start_kwh_dag else 0.0

if val_t > st.session_state.p_total_peak:
    st.session_state.p_total_peak = val_t
    st.session_state.p_symo_peak, st.session_state.p_galvo_peak = val_s, val_g

sla_naar_sheets(val_s, val_g, st.session_state.p_total_peak, oogst_vandaag, st.session_state.start_kwh_dag)

# ====================== UI ======================
st.title("☀️ Solar Piek PRO")
st.caption(f"📍 Borgloon • {vandaag_nl} • {nu.strftime('%H:%M')}")

temp, desc, hum, icon = get_weather()
w1, w2, w3 = st.columns(3)
with w1: st.metric("🌡️ Temperatuur", temp)
with w2: 
    st.markdown(f"**{desc}**")
    st.markdown(f"### {icon}")
with w3: st.metric("💧 Vochtigheid", hum)

st.divider()
st.markdown(f"<h1 style='text-align:center;color:#FFB300;'>⚡ {val_t:,.0f} Watt</h1>", unsafe_allow_html=True)
st.progress(min(val_t / 8000, 1.0))

ca, cb = st.columns(2)
with ca: st.metric("📈 Oogst vandaag", f"{oogst_vandaag:.2f} kWh")
with cb: st.metric("🏆 All Time Peak", f"{max(all_time_peak, st.session_state.p_total_peak):,.0f} W")

st.divider()
c1, c2, c3 = st.columns(3)
with c1: st.metric("🟢 Symo", f"{val_s} W", f"Piek: {st.session_state.p_symo_peak:,.0f} W")
with c2: st.metric("🔴 Galvo", f"{val_g} W", f"Piek: {st.session_state.p_galvo_peak:,.0f} W")
with c3: st.metric("☀️ Totaal", f"{val_t} W", f"Piek: {st.session_state.p_total_peak:,.0f} W")

st.divider()
st.subheader("📜 Historiek")
if not df_display.empty:
    st.dataframe(df_display, use_container_width=True, hide_index=True)
else:
    st.info("Gegevens laden uit Google Sheet...")

time.sleep(2)
st.rerun()
