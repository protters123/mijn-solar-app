import streamlit as st
import requests
import time
import pandas as pd
import io
from datetime import datetime

# ==========================================
# SOLAR PIEK PRO - DE DEFINITIEVE FIX ☀️
# ==========================================

# DE DIRECTE CSV LINK
CSV_URL = "https://google.com"

# INVERTER IP'S
PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek Pro", page_icon="☀️", layout="centered")

# --- LIVE DATA OPHALEN ---
def fetch_status(url):
    try:
        r = requests.get(url, timeout=2).json()
        return abs(float(r['active_power_w'])), "🟢"
    except: return 0.0, "🔴"

val_s, icon_s = fetch_status(URL_1)
val_g, icon_g = fetch_status(URL_2)
val_t = val_s + val_g

# --- DASHBOARD UI ---
st.title("☀️ Solar Piek Pro") 
st.subheader(f"📊 Totaal Live: {val_t:,.0f} W")

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"### {icon_s} Symo")
    st.metric("Nu", f"{val_s:,.0f} W")
with c2:
    st.markdown(f"### {icon_g} Galvo")
    st.metric("Nu", f"{val_g:,.0f} W")

st.divider()

# --- TABEL SECTIE ---
st.subheader("💚 Maandoverzicht") 

try:
    # We halen de data op als tekst
    response = requests.get(CSV_URL, timeout=5)
    
    # We negeren de headers van Google en zetten onze eigen koppen erop
    # Dit voorkomt de "Kolom Datum niet gevonden" fout
    df = pd.read_csv(io.StringIO(response.text), header=None, skiprows=1)
    
    if not df.empty:
        # We pakken alleen de eerste 4 kolommen
        table_df = df.iloc[:, :4]
        table_df.columns = ['Datum', 'Symo', 'Galvo', 'Totaal']
        
        # We maken de getallen mooi groen en de datum wit (standaard Streamlit tabel)
        # Sorteer: Nieuwste dag bovenaan
        st.table(table_df.iloc[::-1])
    else:
        st.info("De spreadsheet lijkt leeg.")

except Exception as e:
    st.warning("Aan het wachten op de juiste tabeldata van Google...")
    # Als je wilt zien wat Google écht stuurt, haal dan het hekje hieronder weg:
    # st.write(pd.read_csv(io.StringIO(requests.get(CSV_URL).text)).head())

st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')} | Verversing elke 2 sec")

# Refresh pagina
time.sleep(2)
st.rerun()
