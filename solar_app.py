import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO v3.2 - Dynamische Weer Emoji's
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzvjNV9Tr1aHoSXX-SQrcTTf7xg3nHzqSzG66tIsAbhx9ioTfecz527eDHQ184qCeN6/exec"

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
    try:
        df = pd.read_csv(CSV_URL, header=0, usecols=range(6))
        df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWh']
        vandaag = df[df['Datum'] == vandaag_nl]
        if not vandaag.empty:
            vandaag['Totaal'] = pd.to_numeric(vandaag['Totaal'], errors='coerce')
            rij = vandaag.loc[vandaag['Totaal'].idxmax()]
            st.session_state.p_symo_peak = float(rij.get('Symo', 0))
            st.session_state.p_galvo_peak = float(rij.get('Galvo', 0))
            st.session_state.p_total_peak = float(rij.get('Totaal', 0))
        else:
            st.session_state.p_symo_peak = st.session_state.p_galvo_peak = st.session_state.p_total_peak = 0.0
    except:
        st.session_state.p_symo_peak = st.session_state.p_galvo_peak = st.session_state.p_total_peak = 0.0
    
    st.session_state.start_kwh_dag = None
    st.session_state.laatste_opslag_datum = None
    st.session_state.huidige_datum = vandaag_iso
    st.session_state.initialized = True

# ====================== FUNCTIES ======================
def sla_naar_sheets(s, g, t, oogst, start_kwh=None):
    try:
        payload = {
            "datum": vandaag_nl, "symo": round(float(s),1), "galvo": round(float(g),1),
            "totaal": round(float(t),1), "oogst": round(float(oogst),2),
            "start_kwh": round(float(start_kwh),3) if start_kwh is not None else None, "actie": "update"
        }
        return requests.post(WEBAPP_URL, json=payload, timeout=10).status_code == 200
    except:
        return False

def fetch_hw_data(url):
    try:
        data = requests.get(url, timeout=3).json()
        power = round(abs(float(data.get('active_power_w', 0))))
        kwh = float(data.get('total_power_export_t1_kwh', 0)) + float(data.get('total_power_export_t2_kwh', 0))
        return power, kwh if kwh > 0 else None, "🟢"
    except:
        return 0, None, "🔴"

@st.cache_data(ttl=300)
def get_weather():
    try:
        r = requests.get("https://wttr.in/Borgloon?format=%t|%C|%h&m&lang=nl", timeout=8)
        parts = r.text.strip().split('|')
        
        temp = parts[0].strip().replace("Â", "").replace("°", "") + "°C"
        desc = parts[1].strip()
        hum = parts[2].strip().rstrip('%')
        
        # Uitgebreide weer-emoji mapping
        d = desc.lower()
        if any(x in d for x in ["zonnig", "helder", "zon"]):
            icon = "☀️"
        elif any(x in d for x in ["licht bewolkt", "meest zonnig"]):
            icon = "⛅"
        elif any(x in d for x in ["bewolkt", "overwegend bewolkt"]):
            icon = "☁️"
        elif any(x in d for x in ["regen", "buien", "neerslag"]):
            icon = "🌧️"
        elif "onweer" in d or "bliksem" in d:
            icon = "⛈️"
        elif any(x in d for x in ["sneeuw", "sneeuwbuien"]):
            icon = "❄️"
        elif "mist" in d or "nevel" in d:
            icon = "🌫️"
        elif "storm" in d or "wind" in d:
            icon = "🌬️"
        else:
            icon = "🌤️"  # default
        
        return temp, desc, hum, icon
    except:
        return "+11°C", "Bewolkt", "54", "☁️"

# ====================== LIVE DATA ======================
val_s, kwh_s, _ = fetch_hw_data(URL_1)
val_g, kwh_g, _ = fetch_hw_data(URL_2)
val_t = val_s + val_g

if kwh_s is not None and kwh_g is not None and st.session_state.start_kwh_dag is None:
    st.session_state.start_kwh_dag = kwh_s + kwh_g
    sla_naar_sheets(0, 0, 0, 0, st.session_state.start_kwh_dag)

oogst_vandaag = round((kwh_s + kwh_g - st.session_state.start_kwh_dag), 2) if st.session_state.start_kwh_dag is not None else 0.0

if val_t > st.session_state.p_total_peak:
    st.session_state.p_total_peak = val_t
    st.session_state.p_symo_peak = max(val_s, st.session_state.p_symo_peak)
    st.session_state.p_galvo_peak = max(val_g, st.session_state.p_galvo_peak)
    sla_naar_sheets(st.session_state.p_symo_peak, st.session_state.p_galvo_peak, val_t, oogst_vandaag, st.session_state.start_kwh_dag)

if nu.hour >= 23 and st.session_state.get('laatste_opslag_datum') != vandaag_iso:
    sla_naar_sheets(st.session_state.p_symo_peak, st.session_state.p_galvo_peak,
                    st.session_state.p_total_peak, oogst_vandaag, st.session_state.start_kwh_dag)
    st.session_state.laatste_opslag_datum = vandaag_iso

# ====================== UI ======================
st.title("☀️ Solar Piek PRO")
st.caption(f"📍 Borgloon • {vandaag_nl} • {nu.strftime('%H:%M')}")

temp, desc, hum, weather_icon = get_weather()

col1, col2, col3 = st.columns([1,2,1])
with col1: st.metric("🌡️ Temperatuur", temp)
with col2: st.markdown(f"**{weather_icon} {desc}**", unsafe_allow_html=True)
with col3: st.metric("💧 Vochtigheid", f"{hum}%")

st.divider()

st.markdown(f"<h1 style='text-align: center; color: #FFB300;'>⚡ {val_t:,.0f} Watt</h1>", unsafe_allow_html=True)
st.progress(min(val_t / 8000, 1.0))

st.markdown(f"### 📈 Oogst vandaag: **{oogst_vandaag:.2f} kWh**")
st.metric("🏆 All-time Record", f"{max(3729, st.session_state.p_total_peak):,.0f} W")

st.divider()

c1, c2, c3 = st.columns(3)
with c1: st.metric("🟢 Symo", f"{val_s} W", f"Piek: {st.session_state.p_symo_peak:,.0f} W")
with c2: st.metric("🔴 Galvo", f"{val_g} W", f"Piek: {st.session_state.p_galvo_peak:,.0f} W")
with c3: st.metric("☀️ Totaal", f"{val_t} W", f"Piek: {st.session_state.p_total_peak:,.0f} W")

st.divider()

st.subheader("📜 Historiek")
try:
    df = pd.read_csv(CSV_URL, header=0, usecols=range(6))
    df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWh']
    for col in ['Symo', 'Galvo', 'Totaal', 'Oogst/dag']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['Datum_dt'] = pd.to_datetime(df['Datum'], format='%d-%m-%Y', errors='coerce')
    df = df.sort_values('Datum_dt', ascending=False).head(15)
    display_df = df[['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag']].rename(columns={'Oogst/dag': 'Oogst'})
    st.dataframe(display_df.style.format({'Symo': '{:.0f}', 'Galvo': '{:.0f}', 'Totaal': '{:.0f}', 'Oogst': '{:.2f}'}), 
                 use_container_width=True, height=380, hide_index=True)
except:
    pass

# Groot wolkje onderaan
st.markdown("""
    <div style='text-align: center; margin-top: 50px; opacity: 0.6;'>
        <h1 style='font-size: 5rem; margin: 0;'>☁️</h1>
    </div>
""", unsafe_allow_html=True)

if st.button("💾 Nu handmatig opslaan", type="primary", use_container_width=True):
    if sla_naar_sheets(st.session_state.p_symo_peak, st.session_state.p_galvo_peak,
                       st.session_state.p_total_peak, oogst_vandaag, st.session_state.start_kwh_dag):
        st.success("✅ Opgeslagen!")
        time.sleep(1)
        st.rerun()

time.sleep(5)
st.rerun()
