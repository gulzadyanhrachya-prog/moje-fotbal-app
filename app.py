import streamlit as st
import requests
import pandas as pd
import json

st.set_page_config(page_title="Match Finder", layout="wide")
st.title("⚽ Hledání zápasů (Premier League)")

# 1. Načtení klíče
try:
    api_key = st.secrets["RAPIDAPI_KEY"]
    st.sidebar.success("✅ API Klíč načten")
except:
    api_key = st.sidebar.text_input("Vlož X-RapidAPI-Key:", type="password")

# 2. Nastavení Endpointu
st.sidebar.header("Nastavení")
st.info("Jdi na RapidAPI -> Matches by League -> Zkopíruj URL")

# Zde vlož tu NOVOU URL, kterou najdeš (ne tu pro ligy!)
url = st.sidebar.text_input("URL Endpointu (Matches):", value="https://api-fotmob.p.rapidapi.com/leagues") 
host = st.sidebar.text_input("X-RapidAPI-Host:", value="api-fotmob.p.rapidapi.com")

# 3. Parametry (Nastaveno pro Premier League)
# Zkoušíme sezónu 2025/2026. Pokud to nepůjde, zkusíme 2024/2025.
season_option = st.sidebar.selectbox("Vyber sezónu:", ["2025/2026", "2024/2025", "2023/2024"])
params = {
    "id": "47",  # ID pro Premier League ve FotMobu
    "season": season_option
}

if st.button("📡 Stáhnout zápasy"):
    if not api_key or not url:
        st.error("Chybí Klíč nebo URL!")
    else:
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host
        }
        
        with st.spinner(f"Stahuji zápasy pro sezónu {season_option}..."):
            try:
                response = requests.get(url, headers=headers, params=params)
                data = response.json()
                
                # Zobrazení JSONu
                st.subheader("🔍 Výsledek")
                st.json(data)
                
                # Hledání zápasů v datech
                # FotMob vrací zápasy často v: matches -> allMatches
                matches = []
                if 'matches' in data and 'allMatches' in data['matches']:
                    matches = data['matches']['allMatches']
                elif 'matches' in data:
                    matches = data['matches']
                elif 'response' in data and 'matches' in data['response']:
                    matches = data['response']['matches']
                
                if matches:
                    st.success(f"Našel jsem {len(matches)} zápasů!")
                    # Ukázka prvního zápasu pro kontrolu struktury
                    st.write("Příklad prvního zápasu:")
                    st.write(matches[0])
                else:
                    st.warning("Data stažena, ale seznam zápasů je prázdný. Zkus změnit sezónu.")

            except Exception as e:
                st.error(f"Chyba: {e}")
