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
# Zorg dat dit de URL is van je allerlaatste 'DisplayValues' Google Script!
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxDfDLkd_6mvmwzulY1bnvSgHEmkeuBOcrbrFjMkbmJSnVhxk-jTda8hC_Cg_zfS1eZ/exec" 

PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Dashboard", page_icon="☀️", layout="centered")

# --- TIJD & DATUM ---
tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
vandaag_iso = nu_lokaal.strftime('%Y-%m-%d')
vandaag_nl = nu_lokaal.strftime('%d-%m-%Y')

# --- DATA FUNCTIES ---
def sla_naar_sheets(s, g, t, oogst, start_kwh=None):
    try:
        payload = {
            "datum": vandaag_nl, 
            "symo": s, 
            "galvo": g, 
            "totaal": t, 
            "oogst": oogst,
            "start_kwh": start_kwh
        }
        r = requests.post(WEBAPP_URL, json=payload, timeout=10)
        return r.status_code == 200
    except: return False

def fetch_hw_data(url):
    try:
        r = requests.get(url, timeout=2).json()
        power = round(abs(float(r.get('active_power_w', 0))))
        t1 = float(r.get('total_power_export_t1_kwh', 0))
        t2 = float(r.get('total_power_export_t2_kwh', 0))
        kwh_totaal = t1 + t2
        return power, kwh_totaal if kwh_totaal > 0 else None, "🟢"
    except: return 0, None, "🔴"

def laad_geheugen_uit_sheet():
    try:
        res = requests.get(CSV_URL, timeout=10)
        if res.status_code == 200:
            df = pd.read_csv(io.StringIO(res.text))
            # Verwachte kolommen: Datum(A), Symo(B), Galvo(C), Totaal(D), Oogst(E), StartKWh(F)
            df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst', 'StartKWh'][:len(df.columns)]
            vandaag_data = df[df['Datum'] == vandaag_nl]
            if not vandaag_data.empty:
                rij = vandaag_data.iloc[-1]
                # Gebruik pd.to_numeric om errors bij lege cellen te voorkomen
                return (
                    float(pd.to_numeric(rij['Symo'], errors='coerce') or 0.0), 
                    float(pd.to_numeric(rij['Galvo'], errors='coerce') or 0.0), 
                    float(pd.to_numeric(rij['Totaal'], errors='coerce') or 0.0),
                    float(pd.to_numeric(rij['StartKWh'], errors='coerce')) if pd.notnull(rij['StartKWh']) else None
                )
    except: pass
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
    except: return "N/A", "N/A", ""

# --- HISTORIEK LADEN ---
historical_max = 3729.0
table_df = pd.DataFrame()
try:
    res = requests.get(CSV_URL, timeout=5)
    if res.status_code == 200:
        table_df = pd.read_csv(io.StringIO(res.text))
        table_df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWh'][:len(table_df.columns)]
        historical_max = pd.to_numeric(table_df['Totaal'], errors='coerce').max() or 3729.0
except: pass

# --- INITIALISATIE & RESET ---
if 'huidige_datum' not in st.session_state:
    st.session_state.huidige_datum = vandaag_iso

if st.session_state.huidige_datum != vandaag_iso:
    st.session_state.update({'p_symo_peak':0.0, 'p_galvo_peak':0.0, 'p_total_peak':0.0, 'start_kwh_dag':None, 'huidige_datum':vandaag_iso})
    st.rerun()

if 'p_total_peak' not in st.session_state:
    s_p, g_p, t_p, s_kwh = laad_geheugen_uit_sheet()
    st.session_state.p_symo_peak, st.session_state.p_galvo_peak, st.session_state.p_total_peak = s_p, g_p, t_p
    st.session_state.start_kwh_dag = s_kwh

# --- LIVE DATA ---
val_s, kwh_s, icon_s = fetch_hw_data(URL_1)
val_g, kwh_g, icon_g = fetch_hw_data(URL_2)
val_t = val_s + val_g

# Ochtend vastlegging (wordt getriggerd door Cron-job 06:00 of eerste browser bezoek)
if kwh_s is not None and kwh_g is not None:
    if st.session_state.start_kwh_dag is None:
        st.session_state.start_kwh_dag = kwh_s + kwh_g
        # Meteen vastleggen in de sheet als ijkpunt
        sla_naar_sheets(0, 0, 0, 0, st.session_state.start_kwh_dag)

# Oogst berekenen
oogst_vandaag = 0.0
if st.session_state.start_kwh_dag and kwh_s is not None and kwh_g is not None:
    oogst_vandaag = round((kwh_s + kwh_g) - st.session_state.start_kwh_dag, 2)

# Update pieken
if val_t > st.session_state.p_total_peak:
    st.session_state.p_total_peak = val_t
    st.session_state.p_symo_peak, st.session_state.p_galvo_peak = max(val_s, st.session_state.p_symo_peak), max(val_g, st.session_state.p_galvo_peak)

# --- UI DASHBOARD ---
st.title("☀️ Solar Dashboard")
temp, desc, hum = get_weather_cached(vandaag_iso)
st.info(f"**{temp}** | {desc} | {hum}")

# Waarschuwing als de startwaarde ontbreekt (gebeurt alleen bij fouten in de sheet)
if st.session_state.start_kwh_dag is None:
    st.warning("⚠️ Geen startwaarde (StartKWh) gevonden voor vandaag. De oogst-teller staat tijdelijk op 0.")

st.write(f"⏰ {nu_lokaal.strftime('%H:%M')} | Live: **{val_t:,.0f} W** | Oogst: **{oogst_vandaag} kWh**")
st.metric("🏆 All-time Record", f"{max(historical_max, st.session_state.p_total_peak):,.0f} W")
st.divider()

# Volgorde: Symo | Galvo | Totaal
c1, c2, c3 = st.columns(3)
with c1: st.metric(f"{icon_s} Symo", f"{val_s} W", f"Piek: {st.session_state.p_symo_peak} W")
with c2: st.metric(f"{icon_g} Galvo", f"{val_g} W", f"Piek: {st.session_state.p_galvo_peak} W")
with c3: st.metric("☀️ Totaal", f"{val_t} W", f"Piek: {st.session_state.p_total_peak} W")

st.divider()
st.subheader("📅 Historiek") 
if not table_df.empty:
    st.dataframe(table_df.iloc[::-1, :5], use_container_width=True, height=250)

if st.button("💾 Handmatige Back-up"):
    if sla_naar_sheets(st.session_state.p_symo_peak, st.session_state.p_galvo_peak, st.session_state.p_total_peak, oogst_vandaag, st.session_state.start_kwh_dag):
        st.success("Opgeslagen!")
        time.sleep(1)
        st.rerun()

# Opslag 23:00 (via Cron-job)
if nu_lokaal.strftime("%H:%M") >= "23:00" and st.session_state.get('laatste_opslag_datum') != vandaag_iso:
    if st.session_state.p_total_peak > 0:
        if sla_naar_sheets(st.session_state.p_symo_peak, st.session_state.p_galvo_peak, st.session_state.p_total_peak, oogst_vandaag, st.session_state.start_kwh_dag):
            st.session_state.laatste_opslag_datum = vandaag_iso

time.sleep(5)
st.rerun()
