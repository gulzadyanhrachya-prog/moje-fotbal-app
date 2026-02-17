import streamlit as st
import requests
import pandas as pd
import json

st.set_page_config(page_title="Tennis Matchstat Explorer", layout="wide", page_icon="🎾")
st.title("🎾 Tennis API Explorer (Matchstat)")
st.caption("Průzkumník pro ATP/WTA/ITF data. Potřebujeme zjistit strukturu pro predikce.")

# 1. NAČTENÍ KLÍČE
try:
    api_key = st.secrets["RAPIDAPI_KEY"]
    st.sidebar.success("✅ API Klíč načten")
except:
    api_key = st.sidebar.text_input("Vlož X-RapidAPI-Key:", type="password")

# 2. NASTAVENÍ ENDPOINTU
st.sidebar.header("Nastavení")
st.sidebar.info("Jdi na RapidAPI -> Code Snippets -> Python Requests")

# Předvyplněné hodnoty pro Matchstat API
default_host = "tennis-api-atp-wta-itf.p.rapidapi.com"
# Zkusíme endpoint pro H2H (Head to Head), to je pro predikce nejdůležitější
default_url = "https://tennis-api-atp-wta-itf.p.rapidapi.com/tennis/v1/h2h"

url = st.sidebar.text_input("URL Endpointu:", value=default_url)
host = st.sidebar.text_input("X-RapidAPI-Host:", value=default_host)

# 3. PARAMETRY (Hledání hráčů)
st.sidebar.subheader("Parametry")
st.sidebar.caption("Pro H2H obvykle potřebujeme ID hráčů. Zkusme nejdřív zjistit, jestli API umí hledat podle jména, nebo jestli musíme zadat ID.")

# Univerzální vstup pro parametry
params_str = st.sidebar.text_area(
    "Parametry (JSON):", 
    value='{"player1_id": "ranking", "player2_id": "ranking"}' 
    # Poznámka: Některá API berou "ranking" jako zástupný znak pro top hráče, 
    # nebo budeme muset najít endpoint "Search Player".
)

if st.button("📡 Stáhnout data"):
    if not api_key or not url:
        st.error("Chybí Klíč nebo URL!")
    else:
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host
        }
        
        try:
            # Převod textu na JSON parametry
            params = json.loads(params_str)
            
            with st.spinner("Stahuji tenisová data..."):
                response = requests.get(url, headers=headers, params=params)
                data = response.json()
                
                # 1. Zobrazení JSONu (To nejdůležitější)
                st.subheader("🔍 Struktura dat")
                st.write("Hledej: 'player_id', 'winner', 'surface', 'score'")
                st.json(data)
                
                # 2. Pokus o tabulku (pokud je to seznam)
                if isinstance(data, list):
                    st.dataframe(pd.DataFrame(data))
                elif 'results' in data:
                    st.dataframe(pd.DataFrame(data['results']))
                elif 'response' in data:
                    st.dataframe(pd.DataFrame(data['response']))

        except Exception as e:
            st.error(f"Chyba: {e}")
            st.warning("Zkontroluj, jestli máš správně formát JSON v parametrech (uvozovky, závorky).")
