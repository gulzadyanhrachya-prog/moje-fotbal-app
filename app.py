import streamlit as st
import requests
import pandas as pd
import json

st.set_page_config(page_title="FotMob Data Explorer", layout="wide")
st.title("⚽ FotMob Match Data Viewer")

# 1. Načtení klíče
try:
    api_key = st.secrets["RAPIDAPI_KEY"]
    st.sidebar.success("✅ API Klíč načten")
except:
    api_key = st.sidebar.text_input("Vlož X-RapidAPI-Key:", type="password")

# 2. Nastavení Endpointu (Hledáme zápasy)
st.sidebar.header("Nastavení")

# Zde vlož URL z RapidAPI sekce 'Matches' nebo 'League Matches'
# Příklad pro FotMob API: https://.../leagues or https://.../matches
url = st.sidebar.text_input("URL Endpointu (Matches/League):")
host = st.sidebar.text_input("X-RapidAPI-Host:")

# 3. Parametry pro FotMob
# FotMob většinou vyžaduje ID ligy (47 = Premier League) a sezónu
st.sidebar.info("Zkusíme stáhnout zápasy pro Premier League (ID 47)")
params_str = st.sidebar.text_input("Parametry (JSON):", value='{"id": "47", "season": "2023/2024"}')

if st.button("📡 Stáhnout zápasy"):
    if not api_key or not url:
        st.error("Chybí Klíč nebo URL!")
    else:
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host
        }
        
        try:
            params = json.loads(params_str)
            with st.spinner("Stahuji zápasy..."):
                response = requests.get(url, headers=headers, params=params)
                data = response.json()
                
                # 1. Zobrazení JSONu (Tohle je klíčové!)
                st.subheader("🔍 Struktura dat")
                st.write("Hledej slova jako 'matches', 'fixtures', 'results', 'home', 'away'.")
                st.json(data)
                
                # 2. Pokus o nalezení zápasů v datech
                # FotMob má často strukturu: response -> matches -> allMatches
                found_matches = []
                
                # Univerzální hledač seznamů
                if 'matches' in data:
                    found_matches = data['matches']
                elif 'response' in data and 'matches' in data['response']:
                    found_matches = data['response']['matches']
                elif 'allMatches' in data:
                    found_matches = data['allMatches']
                
                if found_matches:
                    st.success(f"Nalezeno {len(found_matches)} zápasů!")
                    # Ukázka prvního zápasu
                    st.info(f"První zápas v datech: {found_matches[0]}")
                else:
                    st.warning("Data stažena, ale nenašel jsem seznam zápasů. Podívej se do JSONu výše.")

        except Exception as e:
            st.error(f"Chyba: {e}")
