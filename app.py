import streamlit as st
import requests
import pandas as pd
import json

st.set_page_config(page_title="Tennis H2H Explorer", layout="wide", page_icon="🎾")
st.title("🎾 Tennis H2H (Vzájemné zápasy)")

# 1. NAČTENÍ KLÍČE
try:
    api_key = st.secrets["RAPIDAPI_KEY"]
    st.sidebar.success("✅ API Klíč načten")
except:
    api_key = st.sidebar.text_input("Vlož X-RapidAPI-Key:", type="password")

# 2. NASTAVENÍ ENDPOINTU
st.sidebar.header("Nastavení")
st.info("Jdi na RapidAPI -> Hledej endpoint 'H2H' nebo 'Head to Head'")

# Předvyplněné hodnoty pro Matchstat API (nejčastější varianta)
default_url = "https://tennis-api-atp-wta-itf.p.rapidapi.com/tennis/v1/h2h"
default_host = "tennis-api-atp-wta-itf.p.rapidapi.com"

url = st.sidebar.text_input("URL Endpointu (H2H):", value=default_url)
host = st.sidebar.text_input("X-RapidAPI-Host:", value=default_host)

# 3. ZADÁNÍ HRÁČŮ
st.subheader("Vyber dva hráče (podle ID)")
st.caption("ID získáš z předchozího kroku (Search Player).")

col1, col2 = st.columns(2)
with col1:
    p1_id = st.text_input("ID Hráče 1:", value="356") # 356 bývá často Djokovic v Matchstat API
with col2:
    p2_id = st.text_input("ID Hráče 2:", value="258") # 258 bývá často Nadal

if st.button("📡 Stáhnout vzájemné zápasy"):
    if not api_key or not url:
        st.error("Chybí Klíč nebo URL!")
    else:
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host
        }
        
        # Parametry pro H2H
        params = {
            "player1_id": p1_id,
            "player2_id": p2_id
        }
        
        with st.spinner("Stahuji historii zápasů..."):
            try:
                response = requests.get(url, headers=headers, params=params)
                data = response.json()
                
                # 1. Zobrazení JSONu (Tohle potřebuji vidět!)
                st.subheader("🔍 Struktura dat")
                st.write("Hledej slova jako 'winner', 'surface', 'score', 'stats'.")
                st.json(data)
                
                # 2. Pokus o výpis zápasů
                # Matchstat vrací data často v klíči 'h2h' nebo přímo seznam
                matches = []
                if 'h2h' in data:
                    matches = data['h2h']
                elif isinstance(data, list):
                    matches = data
                
                if matches:
                    st.success(f"Nalezeno {len(matches)} vzájemných zápasů.")
                else:
                    st.warning("Žádné zápasy nenalezeny nebo jiná struktura dat.")

            except Exception as e:
                st.error(f"Chyba: {e}")
