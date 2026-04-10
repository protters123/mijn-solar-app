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
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzvjNV9Tr1aHoSXX-SQrcTTf7xg3nHzqSzG66tIsAbhx9ioTfecz527eDHQ184qCeN6/exec" 

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek & Weer", page_icon="☀️", layout="centered")

tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
vandaag_iso = nu_lokaal.strftime('%Y-%m-%d')
vandaag_nl = nu_lokaal.strftime('%d-%m-%Y')

# --- DATA FUNCTIES ---
def sla_naar_sheets(s, g, t, oogst, start_kwh=None):
    """Update bestaande rij voor vandaag of voeg toe als hij nog niet bestaat."""
    try:
        payload = {
            "datum": vandaag_nl, 
            "symo": s, 
            "galvo": g, 
            "totaal": t, 
            "oogst": oogst,
            "start_kwh": start_kwh,
            "actie": "update"   # Nieuwe parameter zodat het script weet dat we updaten
        }
        r = requests.post(WEBAPP_URL, json=payload, timeout=10)
        if r.status_code == 200:
            return True
        else:
            st.warning(f"⚠️ Opslaan mislukt (status {r.status_code})")
            return False
    except Exception as e:
        st.warning(f"⚠️ Fout bij opslaan: {e}")
        return False

def fetch_hw_data(url):
    try:
        r = requests.get(url, timeout=2).json()
        power = round(abs(float(r.get('active_power_w', 0))))
        t1 = float(r.get('total_power_export_t1_kwh', 0))
        t2 = float(r.get('total_power_export_t2_kwh', 0))
        kwh_totaal = t1 + t2
        return power, kwh_totaal if kwh_totaal > 0 else None, "🟢" if kwh_totaal > 0 else "🔴"
    except:
        return 0, None, "🔴"

def laad_geheugen_uit_sheet():
    try:
        res = requests.get(CSV_URL, timeout=10)
        if res.status_code == 200:
            df = pd.read_csv(io.StringIO(res.text))
            cols = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst', 'StartKWh']
            df.columns = cols[:len(df.columns)]
            
            vandaag_data = df[df['Datum'] == vandaag_nl]
            if not vandaag_data.empty:
                vandaag_data['Totaal_num'] = pd.to_numeric(vandaag_data['Totaal'], errors='coerce')
                max_idx = vandaag_data['Totaal_num'].idxmax()
                rij = vandaag_data.loc[max_idx]
                
                start_kwh = float(rij['StartKWh']) if 'StartKWh' in rij and pd.notnull(rij.get('StartKWh')) else None
                return float(rij['Symo']), float(rij['Galvo']), float(rij['Totaal']), start_kwh
    except:
        pass
    return 0.0, 0.0, 0.0, None

@st.cache_data(ttl=900)
def get_weather_cached(date_str):
    try:
        url = "https://wttr.in/Borgloon?format=%t|%C|%h&m&lang=nl"
        r = requests.get(url, timeout=10)
        r.encoding = 'utf-8'
        if r.status_code == 200 and "|" in r.text:
            parts = r.text.split('|')
            return parts[0].strip(), parts[1].strip(), f"💧 Vochtigheid: {parts[2].strip()}"
        return "14°C", "Licht Bewolkt", "💧 Vochtigheid: 65%"
    except:
        return "N/A", "Weerdata niet bereikbaar", ""

# Historiek laden
historical_max = 3729.0
table_df = pd.DataFrame()
try:
    res = requests.get(CSV_URL, timeout=5)
    if res.status_code == 200:
        table_df = pd.read_csv(io.StringIO(res.text))
        table_df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWh'][:len(table_df.columns)]
        historical_max = pd.to_numeric(table_df['Totaal'], errors='coerce').max()
except:
    pass

# Session state initialisatie
if 'huidige_datum' not in st.session_state or st.session_state.huidige_datum != vandaag_iso:
    s_p, g_p, t_p, s_kwh = laad_geheugen_uit_sheet()
    st.session_state.p_symo_peak = s_p
    st.session_state.p_galvo_peak = g_p
    st.session_state.p_total_peak = t_p
    st.session_state.start_kwh_dag = s_kwh
    st.session_state.huidige_datum = vandaag_iso

# Live data ophalen
val_s, kwh_s, icon_s = fetch_hw_data(URL_1)
val_g, kwh_g, icon_g = fetch_hw_data(URL_2)
val_t = val_s + val_g

# Ochtend: start_kwh vastleggen
if kwh_s is not None and kwh_g is not None and st.session_state.start_kwh_dag is None:
    start_waarde = kwh_s + kwh_g
    st.session_state.start_kwh_dag = start_waarde
    sla_naar_sheets(0, 0, 0, 0, start_waarde)

# Oogst berekenen
oogst_vandaag = 0.00
if st.session_state.start_kwh_dag is not None and kwh_s is not None and kwh_g is not None:
    oogst_vandaag = round((kwh_s + kwh_g) - st.session_state.start_kwh_dag, 2)

# Nieuwe piek? → direct updaten in sheet
if val_t > st.session_state.p_total_peak:
    st.session_state.p_total_peak = val_t
    st.session_state.p_symo_peak = max(val_s, st.session_state.p_symo_peak)
    st.session_state.p_galvo_peak = max(val_g, st.session_state.p_galvo_peak)
    
    if sla_naar_sheets(st.session_state.p_symo_peak, st.session_state.p_galvo_peak, 
                       st.session_state.p_total_peak, oogst_vandaag, 
                       st.session_state.start_kwh_dag):
        st.toast("🏆 Nieuwe piek bijgewerkt in Sheets!", icon="📈")

# Avond opslag (23:00)
if nu_lokaal.strftime("%H:%M") >= "23:00" and st.session_state.get('laatste_opslag_datum') != vandaag_iso:
    if sla_naar_sheets(st.session_state.p_symo_peak, st.session_state.p_galvo_peak, 
                       st.session_state.p_total_peak, oogst_vandaag, 
                       st.session_state.start_kwh_dag):
        st.session_state.laatste_opslag_datum = vandaag_iso
        st.toast("✅ Dagtotalen definitief opgeslagen!", icon="💾")

# === UI ===
st.title("☀️ Solar Dashboard")
temp, desc, hum = get_weather_cached(vandaag_iso)
st.info(f"**{temp}** | {desc} | {hum}")

st.write(f"⏰ {nu_lokaal.strftime('%H:%M')} | {vandaag_nl}")
st.markdown(f"## Live: ⚡ {val_t:,.0f} W")
st.markdown(f"### Oogst vandaag: 📈 {oogst_vandaag} kWh")

st.metric("🏆 All-time Record", f"{max(historical_max, st.session_state.p_total_peak):,.0f} W")
st.divider()

c1, c2, c3 = st.columns(3)
with c1: st.metric(f"{icon_s} Symo", f"{val_s} W", f"Piek: {st.session_state.p_symo_peak} W")
with c2: st.metric(f"{icon_g} Galvo", f"{val_g} W", f"Piek: {st.session_state.p_galvo_peak} W")
with c3: st.metric("☀️⚡ Totaal", f"{val_t} W", f"Piek: {st.session_state.p_total_peak} W")

st.divider()
st.subheader("☀️ Historiek") 
if not table_df.empty:
    st.dataframe(table_df.iloc[::-1, :5], use_container_width=True, height=250)

if st.button("💾 Handmatige update"):
    sla_naar_sheets(st.session_state.p_symo_peak, st.session_state.p_galvo_peak, 
                    st.session_state.p_total_peak, oogst_vandaag, st.session_state.start_kwh_dag)
    st.success("✅ Bijgewerkt!")
    time.sleep(1)
    st.rerun()

time.sleep(5)
st.rerun()
