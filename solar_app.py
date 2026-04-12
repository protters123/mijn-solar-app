import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO v9.9 - STARTWAARDE FIX
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbyLkdLIz2K4X8rIWsq4CF20fgbI9E-t7TEHyqHadCgxxL3seoGwGvN-ZjB-U7YEU3nP/exec"

PUBLIEK_IP = "94.110.235.108"
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek PRO", page_icon="☀️", layout="centered")

tz = pytz.timezone('Europe/Brussels')
nu = datetime.now(tz)
vandaag_nl = nu.strftime('%d-%m-%Y')
vandaag_iso = nu.strftime('%Y-%m-%d')

# --- INITIALISATIE ---
keys = {
    'huidige_datum': vandaag_iso,
    'p_total_peak': 0.0,
    'p_symo_peak': 0.0,
    'p_galvo_peak': 0.0,
    'start_kwh_dag': None,
    'last_sheet_update': 0
}

for key, default in keys.items():
    if key not in st.session_state:
        st.session_state[key] = default

if st.session_state.huidige_datum != vandaag_iso:
    for key, default in keys.items():
        st.session_state[key] = default
    st.session_state.huidige_datum = vandaag_iso

# ====================== DATA LADEN ======================
all_time_peak = 3729.0
df_display = pd.DataFrame()

try:
    # Forceer verversing van de CSV door een timestamp toe te voegen (voorkomt cache van Google)
    df_raw = pd.read_csv(f"{CSV_URL}&cache={time.time()}", header=0)
    df_full = df_raw.iloc[:, :7]
    df_full.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWhdag', 'KWhdag']
    
    atp = pd.to_numeric(df_full['Totaal'], errors='coerce').max()
    if atp > 0: all_time_peak = atp
    
    # BELANGRIJK: Haal de startwaarde uit de sheet
    vandaag_df = df_full[df_full['Datum'] == vandaag_nl]
    if not vandaag_df.empty:
        val_sheet = vandaag_df['StartKWhdag'].iloc[0] # Pak de EERSTE regel van vandaag
        if pd.notna(val_sheet) and float(val_sheet) > 1000: 
            st.session_state.start_kwh_dag = float(val_sheet)
    
    df_full['Datum_dt'] = pd.to_datetime(df_full['Datum'], dayfirst=True, errors='coerce')
    df_display = df_full.sort_values('Datum_dt', ascending=False).head(15).drop(columns=['Datum_dt'])
except: pass

# ====================== FUNCTIES ======================
def sla_naar_sheets(s, g, t, oogst, start_kwh, kwh_nu, force=False):
    nu_ts = time.time()
    if force or (nu_ts - st.session_state.last_sheet_update > 20):
        try:
            payload = {
                "datum": vandaag_nl, "symo": int(s), "galvo": int(g), "totaal": int(t), 
                "oogst": float(oogst), "start_kwh": float(start_kwh), "kwh_nu": float(kwh_nu), 
                "actie": "update"
            }
            requests.post(WEBAPP_URL, json=payload, timeout=5)
            st.session_state.last_sheet_update = nu_ts
        except: pass

def fetch_hw_data(url):
    try:
        r = requests.get(url, timeout=3).json()
        raw_p = abs(float(r.get('active_power_w', 0)))
        power = round(raw_p) if raw_p >= 10 else 0
        kwh = float(r.get('total_power_export_kwh', 0))
        if kwh == 0:
            kwh = float(r.get('total_power_export_t1_kwh', 0)) + float(r.get('total_power_export_t2_kwh', 0))
        return power, kwh, "🟢"
    except: return 0, 0, "🔴"

# ====================== LIVE DATA ======================
val_s, kwh_s, dot_s = fetch_hw_data(URL_1)
val_g, kwh_g, dot_g = fetch_hw_data(URL_2)
val_t, kwh_nu = val_s + val_g, kwh_s + kwh_g

# Alleen als de sheet écht geen waarde heeft, zetten we de huidige stand vast
if kwh_nu > 0 and st.session_state.start_kwh_dag is None:
    st.session_state.start_kwh_dag = kwh_nu

# Berekening Oogst
oogst_vandaag = round(max(0.0, kwh_nu - (st.session_state.start_kwh_dag or kwh_nu)), 3)

if val_t > st.session_state.p_total_peak:
    st.session_state.p_total_peak = val_t
    st.session_state.p_symo_peak, st.session_state.p_galvo_peak = val_s, val_g

# Update sheets
if st.session_state.start_kwh_dag:
    sla_naar_sheets(val_s, val_g, st.session_state.p_total_peak, oogst_vandaag, st.session_state.start_kwh_dag, kwh_nu)

# ====================== UI ======================
st.title("☀️ Solar Piek PRO")
st.caption(f"📍 Tongeren-Borgloon • {vandaag_nl} • {nu.strftime('%H:%M:%S')}")

st.divider()
st.markdown(f"<h1 style='text-align:center;color:#FFB300; font-size: 55px;'>⚡ {val_t:,.0f} Watt</h1>", unsafe_allow_html=True)
st.progress(min(val_t / 8000, 1.0))

ca, cb = st.columns(2)
with ca: st.metric("📈 Oogst vandaag", f"{oogst_vandaag:.3f} kWh")
with cb: st.metric("🏆 All Time Peak", f"{max(all_time_peak, st.session_state.p_total_peak):,.0f} W")

st.divider()
c1, c2, c3 = st.columns(3)
with c1: st.metric(f"{dot_s} Symo", f"{val_s} W", f"Piek: {st.session_state.p_symo_peak} W")
with c2: st.metric(f"{dot_g} Galvo", f"{val_g} W", f"Piek: {st.session_state.p_galvo_peak} W")
with c3: st.metric("☀️ Totaal", f"{val_t} W", f"Piek: {st.session_state.p_total_peak:,.0f} W")

st.divider()
st.subheader("📜 Historiek")
if not df_display.empty:
    st.dataframe(df_display, use_container_width=True, hide_index=True)

if st.button("🔄 Reset Startwaarde (Huidige stand als beginpunt)"):
    st.session_state.start_kwh_dag = kwh_nu
    sla_naar_sheets(val_s, val_g, st.session_state.p_total_peak, 0, kwh_nu, kwh_nu, force=True)
    st.rerun()

time.sleep(2)
st.rerun()
