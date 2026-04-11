import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO v3.9 - Offline inverters fix
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzvjNV9Tr1aHoSXX-SQrcTTf7xg3nHzqSzG66tIsAbhx9ioTfecz527eDHQ184qCeN6/exec"

PUBLIEK_IP = "94.110.235.108"
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"   # Symo
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"   # Galvo

st.set_page_config(page_title="Solar Piek PRO", page_icon="☀️", layout="centered")

tz = pytz.timezone('Europe/Brussels')
nu = datetime.now(tz)
vandaag_nl = nu.strftime('%d-%m-%Y')
vandaag_iso = nu.strftime('%Y-%m-%d')

# ====================== SESSION STATE + STARTWAARDE LADEN ======================
if 'initialized' not in st.session_state or st.session_state.get('huidige_datum') != vandaag_iso:
    st.session_state.start_kwh_dag = None
    st.session_state.p_symo_peak = 0.0
    st.session_state.p_galvo_peak = 0.0
    st.session_state.p_total_peak = 0.0

    # Laad data uit Sheet (één keer laden voor efficiëntie)
    try:
        df = pd.read_csv(CSV_URL, header=0, usecols=range(6))
        df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWh']
        df['Totaal'] = pd.to_numeric(df['Totaal'], errors='coerce')
        df['StartKWh'] = pd.to_numeric(df['StartKWh'], errors='coerce')

        vandaag = df[df['Datum'] == vandaag_nl]
        if not vandaag.empty:
            # StartKWh
            start = vandaag['StartKWh'].iloc[-1]
            st.session_state.start_kwh_dag = float(start) if pd.notna(start) else None

            # Piek (neem de rij met max Totaal)
            rij = vandaag.loc[vandaag['Totaal'].idxmax()]
            st.session_state.p_symo_peak = float(rij.get('Symo', 0)) if pd.notna(rij.get('Symo')) else 0.0
            st.session_state.p_galvo_peak = float(rij.get('Galvo', 0)) if pd.notna(rij.get('Galvo')) else 0.0
            st.session_state.p_total_peak = float(rij.get('Totaal', 0)) if pd.notna(rij.get('Totaal')) else 0.0
    except Exception as e:
        st.error(f"Fout bij laden van Sheet: {e}")

    st.session_state.huidige_datum = vandaag_iso
    st.session_state.initialized = True

# ====================== FUNCTIES ======================
def sla_naar_sheets(s, g, t, oogst, start_kwh=None):
    try:
        payload = {
            "datum": vandaag_nl,
            "symo": round(float(s), 1),
            "galvo": round(float(g), 1),
            "totaal": round(float(t), 1),
            "oogst": round(float(oogst), 2),
            "start_kwh": round(float(start_kwh), 3) if start_kwh is not None else None,
            "actie": "update"
        }
        response = requests.post(WEBAPP_URL, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Opslag fout: {e}")
        return False

def fetch_hw_data(url):
    try:
        data = requests.get(url, timeout=3).json()
        power = round(abs(float(data.get('active_power_w', 0))))
        kwh = float(data.get('total_power_export_t1_kwh', 0)) + float(data.get('total_power_export_t2_kwh', 0))
        status = "🟢" if kwh > 0 else "🔴"
        return power, kwh if kwh > 0 else None, status
    except Exception as e:
        # st.warning(f"API fout bij {url}: {e}")
        return 0, None, "🔴"

@st.cache_data(ttl=300)
def get_weather():
    try:
        r = requests.get("https://wttr.in/Borgloon?format=%t|%C|%h&m&lang=nl", timeout=8)
        parts = r.text.strip().split('|')
        temp = parts[0].strip().replace("Â", "") + "°C"
        desc = parts[1].strip()
        hum = parts[2].strip().rstrip('%')
        d = desc.lower()
        if any(x in d for x in ["zonnig", "helder", "zon"]): icon = "☀️"
        elif any(x in d for x in ["licht bewolkt"]): icon = "⛅"
        elif any(x in d for x in ["bewolkt"]): icon = "☁️"
        elif any(x in d for x in ["regen", "buien"]): icon = "🌧️"
        else: icon = "🌤️"
        return temp, desc, hum, icon
    except:
        return "+11°C", "Bewolkt", "54", "☁️"

# ====================== LIVE DATA ======================
val_s, kwh_s_raw, status_s = fetch_hw_data(URL_1)
val_g, kwh_g_raw, status_g = fetch_hw_data(URL_2)

# Behandel offline als 0 voor berekeningen
kwh_s = kwh_s_raw if kwh_s_raw is not None else 0.0
kwh_g = kwh_g_raw if kwh_g_raw is not None else 0.0
val_t = val_s + val_g

# Waarschuwing voor offline inverters
if status_s == "🔴":
    st.warning("Symo inverter offline – waarden als 0 behandeld.")
if status_g == "🔴":
    st.warning("Galvo inverter offline – waarden als 0 behandeld (verwacht na installatie).")

# Start kWh vastleggen (sta toe als ten minste één inverter data heeft)
if st.session_state.start_kwh_dag is None and (kwh_s_raw is not None or kwh_g_raw is not None):
    st.session_state.start_kwh_dag = round(kwh_s + kwh_g, 3)  # Meer precisie, gebruik behandelde waarden
    if sla_naar_sheets(0, 0, 0, 0, st.session_state.start_kwh_dag):
        st.session_state.debug_log = "Start_kwh gezet en opgeslagen."
    else:
        st.session_state.debug_log = "Start_kwh gezet, maar opslag faalde."

# Oogst vandaag berekenen met precisie (gebruik behandelde waarden)
oogst_vandaag = 0.0
if st.session_state.start_kwh_dag is not None:
    raw_oogst = (kwh_s + kwh_g) - st.session_state.start_kwh_dag
    oogst_vandaag = max(round(raw_oogst, 2), 0.0)  # Voorkom negatief, rond naar 2 decimalen

# Piek bijwerken
if val_t > st.session_state.p_total_peak:
    st.session_state.p_total_peak = val_t
    st.session_state.p_symo_peak = max(val_s, st.session_state.p_symo_peak)
    st.session_state.p_galvo_peak = max(val_g, st.session_state.p_galvo_peak)
    sla_naar_sheets(st.session_state.p_symo_peak, st.session_state.p_galvo_peak, val_t, oogst_vandaag, st.session_state.start_kwh_dag)

# Avond opslag (alleen als niet al gedaan)
if nu.hour >= 23 and st.session_state.get('laatste_opslag_datum') != vandaag_iso:
    sla_naar_sheets(st.session_state.p_symo_peak, st.session_state.p_galvo_peak,
                    st.session_state.p_total_peak, oogst_vandaag, st.session_state.start_kwh_dag)
    st.session_state.laatste_opslag_datum = vandaag_iso

# ====================== UI ======================
st.title("☀️ Solar Piek PRO")
st.caption(f"📍 Borgloon • {vandaag_nl} • {nu.strftime('%H:%M')}")

temp, desc, hum, weather_icon = get_weather()

col1, col2, col3 = st.columns([1, 1.2, 1])
with col1: st.metric("🌡️ Temperatuur", temp)
with col2:
    st.markdown(f"**{desc}**")
    st.markdown(f"<div style='text-align: center; font-size: 4rem; margin-top: -8px;'>{weather_icon}</div>", unsafe_allow_html=True)
with col3: st.metric("💧 Vochtigheid", f"{hum}%")

st.divider()

st.markdown(f"<h1 style='text-align: center; color: #FFB300;'>⚡ {val_t:,.0f} Watt</h1>", unsafe_allow_html=True)
st.progress(min(val_t / 8000, 1.0))

st.markdown(f"### 📈 Oogst vandaag: **{oogst_vandaag:.2f} kWh**")
st.metric("🏆 All-time Record", f"{max(3729, st.session_state.p_total_peak):,.0f} W")

st.divider()

c1, c2, c3 = st.columns(3)
with c1: st.metric(f"{status_s} Symo", f"{val_s} W", f"Piek: {st.session_state.p_symo_peak:,.0f} W")
with c2: st.metric(f"{status_g} Galvo", f"{val_g} W", f"Piek: {st.session_state.p_galvo_peak:,.0f} W")
with c3: st.metric("☀️ Totaal", f"{val_t} W", f"Piek: {st.session_state.p_total_peak:,.0f} W")

st.divider()

st.subheader("📜 Historiek")
# Laad en toon laatste 10 dagen uit Sheet (gesorteerd op datum, nieuwste bovenaan)
try:
    df_hist = pd.read_csv(CSV_URL, header=0, usecols=range(6))
    df_hist.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWh']
    df_hist = df_hist.sort_index(ascending=False).head(10)  # Nieuwste bovenaan, max 10
    if df_hist.empty:
        st.info("Geen historische data beschikbaar.")
    else:
        st.dataframe(df_hist)
except Exception as e:
    st.error(f"Fout bij laden historiek: {e}")

if st.button("💾 Nu handmatig opslaan", type="primary", use_container_width=True):
    if sla_naar_sheets(st.session_state.p_symo_peak, st.session_state.p_galvo_peak,
                       st.session_state.p_total_peak, oogst_vandaag, st.session_state.start_kwh_dag):
        st.success("✅ Opgeslagen!")
        time.sleep(1)
        st.rerun()
    else:
        st.error("❌ Opslag mislukt – controleer verbinding of Sheet.")

# ====================== DEBUG SECTIE (tijdelijk voor troubleshooting) ======================
if 'show_debug' not in st.session_state:
    st.session_state.show_debug = True

if st.button("Toggle Debug Info"):
    st.session_state.show_debug = not st.session_state.show_debug

if st.session_state.show_debug:
    st.subheader("Debug Info")
    st.write(f"kwh_s: {kwh_s} ({'raw: ' + str(kwh_s_raw) if kwh_s_raw is None else 'OK'}), kwh_g: {kwh_g} ({'raw: ' + str(kwh_g_raw) if kwh_g_raw is None else 'OK'}), start_kwh_dag: {st.session_state.start_kwh_dag}")
    st.write(f"Raw oogst calc: {(kwh_s + kwh_g) - st.session_state.start_kwh_dag if st.session_state.start_kwh_dag is not None else 'Niet berekend (start_kwh ontbreekt)'}")
    st.write(f"Oogst vandaag (afgerond): {oogst_vandaag}")
    st.write(f"Debug log: {st.session_state.get('debug_log', 'Geen logs')}")
    st.write(f"API Status: Symo {status_s}, Galvo {status_g}")

# Auto-rerun voor live updates (pauzeerbaar voor debug)
if not st.session_state.show_debug:  # Alleen rerun als debug niet aanstaat
    time.sleep(5)
    st.rerun()
