import streamlit as st
import requests
import time
from datetime import datetime

# ==========================================
# SOLAR PIEK - SECRETS VERSIE
# ==========================================
PUBLIEK_IP = "94.110.235.108" 
URL_1 = f"http://{PUBLIEK_IP}:8081/api/v1/data"
URL_2 = f"http://{PUBLIEK_IP}:8082/api/v1/data"

st.set_page_config(page_title="Solar Piek", page_icon="☀️", layout="centered")
st.title("☀️ Solar Piek")

# --- RECORDS LADEN ---
# We gebruiken de secrets als startwaarde, maar houden ze in het geheugen bij
if 'p_symo' not in st.session_state:
    st.session_state.p_symo = st.secrets.get("symo_piek", 3740.0)
    st.session_state.p_galvo = st.secrets.get("galvo_piek", 0.0)
    st.session_state.p_total = st.secrets.get("totaal_piek", 3740.0)

try:
    # Live data ophalen
    res1 = requests.get(URL_1, timeout=3).json()
    res2 = requests.get(URL_2, timeout=3).json()
    
    val_symo = abs(float(res1['active_power_w']))
    val_galvo = abs(float(res2['active_power_w']))
    val_total = val_symo + val_galvo
    
    # Check voor nieuwe records in de huidige sessie
    if val_symo > st.session_state.p_symo:
        st.session_state.p_symo = val_symo
    if val_galvo > st.session_state.p_galvo:
        st.session_state.p_galvo = val_galvo
    if val_total > st.session_state.p_total:
        st.session_state.p_total = val_total
        st.balloons()

    # Display
    st.markdown(f"### 📊 Totaal: {val_total:,.0f} W")
    st.metric("🏆 Record Totaal", f"{st.session_state.p_total:,.0f} W")
    
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔹 Symo")
        st.metric("Nu", f"{val_symo:,.0f} W")
        st.metric("Piek", f"{st.session_state.p_symo:,.0f} W")
    with c2:
        st.subheader("🔸 Galvo")
        st.metric("Nu", f"{val_galvo:,.0f} W")
        st.metric("Piek", f"{st.session_state.p_galvo:,.0f} W")

except Exception:
    st.warning("⚠️ Live verbinding weg. Records uit geheugen zichtbaar.")
    st.metric("🏆 Hoogste Totaal (Record)", f"{st.session_state.p_total:,.0f} W")

st.caption(f"Check: {datetime.now().strftime('%H:%M:%S')} | Geheugen: Cloud Secrets")
time.sleep(2)
st.rerun()
