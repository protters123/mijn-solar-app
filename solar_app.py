import streamlit as st
import requests
import time
import pandas as pd
import io
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO + WEERSTATION ☀️🌦️
# Volledig verbeterde & opgeschoonde versie
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzvjNV9Tr1aHoSXX-SQrcTTf7xg3nHzqSzG66tIsAbhx9ioTfecz527eDHQ184qCeN6/exec"

PUBLIEK_IP = "94.110.235.108"
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"   # Symo
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"   # Galvo

st.set_page_config(
    page_title="Solar Piek PRO",
    page_icon="☀️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

tz = pytz.timezone('Europe/Brussels')
nu_lokaal = datetime.now(tz)
vandaag_iso = nu_lokaal.strftime('%Y-%m-%d')
vandaag_nl = nu_lokaal.strftime('%d-%m-%Y')

# ====================== SESSION STATE ======================
if 'initialized' not in st.session_state or st.session_state.huidige_datum != vandaag_iso:
    st.session_state.p_symo_peak = 0.0
    st.session_state.p_galvo_peak = 0.0
    st.session_state.p_total_peak = 0.0
    st.session_state.start_kwh_dag = None
    st.session_state.laatste_opslag_datum = None
    st.session_state.huidige_datum = vandaag_iso

# ====================== HELPER FUNCTIES ======================
def sla_naar_sheets(s, g, t, oogst, start_kwh=None):
    """Update of toevoegen van de dag in Google Sheets"""
    try:
        payload = {
            "datum": vandaag_nl,
            "symo": round(s, 1),
            "galvo": round(g, 1),
            "totaal": round(t, 1),
            "oogst": round(oogst, 2),
            "start_kwh": round(start_kwh, 3) if start_kwh is not None else None,
            "actie": "update"
        }
        r = requests.post(WEBAPP_URL, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        st.warning(f"⚠️ Opslaan mislukt: {e}")
        return False

def fetch_hw_data(url):
    """Haal live data op van één inverter"""
    try:
        r = requests.get(url, timeout=3).json()
        power = round(abs(float(r.get('active_power_w', 0))))
        t1 = float(r.get('total_power_export_t1_kwh', 0))
        t2 = float(r.get('total_power_export_t2_kwh', 0))
        kwh_totaal = t1 + t2
        return power, kwh_totaal if kwh_totaal > 0 else None, "🟢" if kwh_totaal > 0 else "🔴"
    except:
        return 0, None, "🔴"

def laad_geheugen_uit_sheet():
    """Laad de laatste waarden van vandaag uit Google Sheets"""
    try:
        df = pd.read_csv(CSV_URL, dtype=str)
        # Kolommen normaliseren
        df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst', 'StartKWh'][:len(df.columns)]
        
        vandaag = df[df['Datum'] == vandaag_nl]
        if vandaag.empty:
            return 0.0, 0.0, 0.0, None
            
        # Neem rij met hoogste totaal (meest recente piek)
        vandaag['Totaal_num'] = pd.to_numeric(vandaag['Totaal'], errors='coerce')
        rij = vandaag.loc[vandaag['Totaal_num'].idxmax()]
        
        start_kwh = float(rij['StartKWh']) if pd.notna(rij.get('StartKWh')) and rij.get('StartKWh') != '' else None
        
        return (
            float(rij.get('Symo', 0)),
            float(rij.get('Galvo', 0)),
            float(rij.get('Totaal', 0)),
            start_kwh
        )
    except Exception:
        return 0.0, 0.0, 0.0, None

@st.cache_data(ttl=300)  # 5 minuten cache voor weer
def get_weather():
    try:
        r = requests.get("https://wttr.in/Borgloon?format=%t|%C|%h&m&lang=nl", timeout=8)
        r.raise_for_status()
        parts = r.text.strip().split('|')
        if len(parts) >= 3:
            return parts[0].strip(), parts[1].strip(), f"💧 {parts[2].strip()}"
    except:
        pass
    return "N/A", "Weerdata niet beschikbaar", ""

# ====================== HISTORIEK LADEN ======================
try:
    res = requests.get(CSV_URL, timeout=8)
    if res.status_code == 200:
        table_df = pd.read_csv(io.StringIO(res.text))
        table_df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWh'][:len(table_df.columns)]
        historical_max = pd.to_numeric(table_df['Totaal'], errors='coerce').max()
    else:
        table_df = pd.DataFrame()
        historical_max = 3729.0
except:
    table_df = pd.DataFrame()
    historical_max = 3729.0

# ====================== LIVE DATA ======================
val_s, kwh_s, icon_s = fetch_hw_data(URL_1)
val_g, kwh_g, icon_g = fetch_hw_data(URL_2)
val_t = val_s + val_g

# Ochtend: start_kwh vastleggen (één keer per dag)
if kwh_s is not None and kwh_g is not None and st.session_state.start_kwh_dag is None:
    start_waarde = kwh_s + kwh_g
    st.session_state.start_kwh_dag = start_waarde
    sla_naar_sheets(0, 0, 0, 0, start_waarde)

# Oogst vandaag berekenen
oogst_vandaag = 0.00
if st.session_state.start_kwh_dag is not None and kwh_s is not None and kwh_g is not None:
    oogst_vandaag = round((kwh_s + kwh_g) - st.session_state.start_kwh_dag, 2)

# Nieuwe piek? → direct opslaan
if val_t > st.session_state.p_total_peak:
    st.session_state.p_total_peak = val_t
    st.session_state.p_symo_peak = max(val_s, st.session_state.p_symo_peak)
    st.session_state.p_galvo_peak = max(val_g, st.session_state.p_galvo_peak)
    
    if sla_naar_sheets(
        st.session_state.p_symo_peak,
        st.session_state.p_galvo_peak,
        st.session_state.p_total_peak,
        oogst_vandaag,
        st.session_state.start_kwh_dag
    ):
        st.toast("🏆 Nieuwe piek opgeslagen!", icon="📈")

# Avond: definitieve opslag om 23:00
if nu_lokaal.hour >= 23 and st.session_state.get('laatste_opslag_datum') != vandaag_iso:
    if sla_naar_sheets(
        st.session_state.p_symo_peak,
        st.session_state.p_galvo_peak,
        st.session_state.p_total_peak,
        oogst_vandaag,
        st.session_state.start_kwh_dag
    ):
        st.session_state.laatste_opslag_datum = vandaag_iso
        st.toast("🌙 Dagtotalen definitief opgeslagen!", icon="💾")

# ====================== UI ======================
st.title("☀️ Solar Piek PRO")
st.caption(f"📍 Borgloon • {vandaag_nl} • {nu_lokaal.strftime('%H:%M')}")

# Weer
temp, desc, hum = get_weather()
col_w1, col_w2, col_w3 = st.columns([1, 2, 1])
with col_w1:
    st.metric("🌡️ Temperatuur", temp)
with col_w2:
    st.markdown(f"**{desc}**")
with col_w3:
    st.write(hum)

st.divider()

# Live vermogen (groot en prominent)
st.markdown(f"""
    <h1 style='text-align: center; color: #FFB300; margin: 0; padding: 0;'>
        ⚡ {val_t:,.0f} Watt
    </h1>
""", unsafe_allow_html=True)

# Progress bar (max 8 kW als voorbeeld – pas aan indien nodig)
st.progress(min(val_t / 8000, 1.0))

st.markdown(f"### 📈 Oogst vandaag: **{oogst_vandaag} kWh**")

# All-time record
all_time = max(historical_max, st.session_state.p_total_peak)
st.metric("🏆 All-time Record", f"{all_time:,.0f} W")

st.divider()

# Per inverter
c1, c2, c3 = st.columns(3)
with c1:
    st.metric(f"{icon_s} Symo", f"{val_s} W", f"Piek: {st.session_state.p_symo_peak:,.0f} W")
with c2:
    st.metric(f"{icon_g} Galvo", f"{val_g} W", f"Piek: {st.session_state.p_galvo_peak:,.0f} W")
with c3:
    st.metric("☀️ Totaal", f"{val_t} W", f"Piek: {st.session_state.p_total_peak:,.0f} W")

st.divider()

# Historiek
st.subheader("📜 Historiek")
if not table_df.empty:
    # Laatste 10 dagen + omgekeerde volgorde (nieuwste bovenaan)
    recent = table_df.iloc[::-1].head(10)[['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag']]
    st.dataframe(
        recent.style.format({"Symo": "{:.0f}", "Galvo": "{:.0f}", "Totaal": "{:.0f}", "Oogst/dag": "{:.2f}"}),
        use_container_width=True,
        height=300
    )
else:
    st.info("Nog geen historische data gevonden.")

# Handmatige update knop
if st.button("💾 Handmatig opslaan in Sheets", type="primary", use_container_width=True):
    if sla_naar_sheets(
        st.session_state.p_symo_peak,
        st.session_state.p_galvo_peak,
        st.session_state.p_total_peak,
        oogst_vandaag,
        st.session_state.start_kwh_dag
    ):
        st.success("✅ Succesvol opgeslagen!")
        time.sleep(1.5)
        st.rerun()

st.caption("Auto-refresh elke 5 seconden • Data van Symo + Galvo via lokale API")

# Auto refresh
time.sleep(5)
st.rerun()
