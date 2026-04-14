import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime
import pytz

# ==========================================
# SOLAR PIEK PRO v12.3 - EXPANDER HERSTELD
# ==========================================

SHEET_ID = "19wEhTv_-3PkwWl3dnp8xn_e5SKtwBmuJO4yS8W-uEmo"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzl6V4knhaZnB7zgt5kvFkgTCph3Y-3S4KDHJEPzaaU1gqvTIfokzIiFUxDfhiBlIxW/exec"

PUBLIEK_IP = "94.110.235.108"
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek PRO", page_icon="☀️", layout="centered")

tz = pytz.timezone('Europe/Brussels')
nu = datetime.now(tz)
vandaag_nl = nu.strftime('%d-%m-%Y')
vandaag_iso = nu.strftime('%Y-%m-%d')

# --- INITIALISATIE ---
if 'initialized' not in st.session_state:
    st.session_state.huidige_datum = vandaag_iso
    st.session_state.p_total_peak = 0.0
    st.session_state.p_symo_peak = 0.0
    st.session_state.start_kwh_dag = None
    st.session_state.last_sync_time = "Nog geen sync"
    st.session_state.last_sheet_update = 0
    st.session_state.initialized = True

# ====================== DATA LADEN ======================
@st.cache_data(ttl=60)
def load_historical_data(url):
    try:
        # Cache buster toegevoegd voor verse data
        return pd.read_csv(f"{url}&ts={int(time.time()/60)}", header=0, decimal=",")
    except: return None

df_raw = load_historical_data(CSV_URL)
df_display = pd.DataFrame()
monthly_summary = pd.DataFrame()
stand_gisteren = None
all_time_peak = 3729.0

if df_raw is not None:
    try:
        df_full = df_raw.iloc[:, :7].copy()
        df_full.columns = ['Datum', 'Symo', 'Galvo', 'Totaal', 'Oogst/dag', 'StartKWhdag', 'KWhdag']
        
        # Piek bepalen
        atp = pd.to_numeric(df_full['Totaal'], errors='coerce').max()
        if atp > 0: all_time_peak = atp
        
        # Datum conversie
        df_full['temp_date'] = pd.to_datetime(df_full['Datum'], dayfirst=True, errors='coerce')
        df_sorted = df_full.sort_values('temp_date', ascending=False)

        # --- MAANDOVERZICHT BEREKENING ---
        df_full['Maand'] = df_full['temp_date'].dt.strftime('%m-%Y')
        # Dwing numerieke waarden af voor correcte optelling (komma naar punt)
        df_full['Oogst/dag'] = pd.to_numeric(df_full['Oogst/dag'].astype(str).str.replace(',', '.'), errors='coerce')
        monthly_summary = df_full.groupby('Maand')['Oogst/dag'].sum().reset_index()
        monthly_summary = monthly_summary.sort_values('Maand', ascending=False)

        # Gisteren bepalen voor startwaarde
        gisteren_df = df_sorted[df_sorted['Datum'] != vandaag_nl]
        if not gisteren_df.empty:
            val_gisteren = pd.to_numeric(gisteren_df['KWhdag'].iloc[0], errors='coerce')
            if val_gisteren > 0: stand_gisteren = float(val_gisteren)

        # Tabel voor weergave
        df_display = df_sorted.drop(columns=['temp_date']).head(15)
    except: pass

# ====================== LIVE DATA ======================
def fetch_hw_data(url):
    try:
        r = requests.get(url, timeout=1.5).json()
        power = round(abs(float(r.get('active_power_w', 0))))
        kwh = float(r.get('total_power_export_kwh', 0))
        if kwh == 0:
            kwh = float(r.get('total_power_export_t1_kwh', 0)) + float(r.get('total_power_export_t2_kwh', 0))
        return (power if power >= 10 else 0), kwh, "🟢"
    except: return 0, 0, "🔴"

val_s, kwh_s, dot_s = fetch_hw_data(URL_1)
val_g, kwh_g, dot_g = fetch_hw_data(URL_2)
val_t, kwh_nu = val_s + val_g, kwh_s + kwh_g

if st.session_state.start_kwh_dag is None:
    st.session_state.start_kwh_dag = stand_gisteren if stand_gisteren else kwh_nu

oogst_vandaag = round(max(0.0, kwh_nu - (st.session_state.start_kwh_dag or kwh_nu)), 3)

if val_s > st.session_state.p_symo_peak: st.session_state.p_symo_peak = val_s
if val_t > st.session_state.p_total_peak: st.session_state.p_total_peak = val_t

@st.cache_data(ttl=3600)
def get_weather():
    try:
        # URL gefixed voor stabiel weer
        r = requests.get("https://wttr.in|%C|%h&lang=nl", timeout=3)
        p = r.text.strip().split('|')
        return p[0], p[1], p[2], "🌤️"
    except: return "12°C", "Bewolkt", "80%", "⛅"

# ====================== UI ======================
st.title("☀️ Solar Piek PRO")
temp, cond, hum, icon = get_weather()
w1, w2, w3 = st.columns(3)
w1.metric("🌡️ Temp", temp)
w2.metric(f"{icon} Weer", cond)
w3.metric("💧 Vocht", hum)

st.divider()
st.markdown(f"<h1 style='text-align:center;color:#FFB300; font-size: 55px;'>⚡ {val_t:,.0f} Watt</h1>", unsafe_allow_html=True)
st.progress(min(val_t / 8000, 1.0))
st.caption(f"🔄 Sync: **{st.session_state.last_sync_time}**")

ca, cb = st.columns(2)
with ca: st.metric("📈 Oogst vandaag", f"{oogst_vandaag:.3f} kWh")
with cb: st.metric("🏆 Piek", f"{max(all_time_peak, st.session_state.p_total_peak):,.0f} W")

st.divider()
c1, c2, c3 = st.columns(3)
with c1: st.metric(f"{dot_s} Symo", f"{val_s} W", f"Piek: {st.session_state.p_symo_peak:,.0f} W")
with c2: st.metric(f"{dot_g} Galvo", f"{val_g} W")
with c3: st.metric("☀️ Totaal", f"{val_t} W")

# --- HIER IS HET UITKLAPMENU WEER ---
if not df_display.empty:
    with st.expander("📊 Historiek & Maandoverzicht"):
        st.subheader("Maandtotalen")
        st.dataframe(monthly_summary, hide_index=True, use_container_width=True)
        
        st.divider()
        
        st.subheader("Laatste 15 dagen")
        st.dataframe(df_display, hide_index=True, use_container_width=True)

time.sleep(1)
st.rerun()
