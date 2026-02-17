import streamlit as st
import requests
import pandas as pd
import json

st.set_page_config(page_title="Tennis Player Search", layout="wide", page_icon="🎾")
st.title("🎾 Hledání ID Tenistů")
st.caption("Krok 1: Musíme najít ID hráčů, abychom mohli predikovat jejich zápasy.")

# 1. NAČTENÍ KLÍČE
try:
    api_key = st.secrets["RAPIDAPI_KEY"]
    st.sidebar.success("✅ API Klíč načten")
except:
    api_key = st.sidebar.text_input("Vlož X-RapidAPI-Key:", type="password")

# 2. NASTAVENÍ ENDPOINTU (Hledáme hráče)
st.sidebar.header("Nastavení")
st.info("Jdi na RapidAPI -> Hledej endpoint 'Search Player' nebo 'Rankings'")

# Zde vlož URL pro vyhledávání hráčů
# Tip: U Matchstat API to bývá často POST request na '/player/search'
url = st.sidebar.text_input("URL Endpointu (Search/Rankings):", value="https://tennis-api-atp-wta-itf.p.rapidapi.com/tennis/v1/player/search")
host = st.sidebar.text_input("X-RapidAPI-Host:", value="tennis-api-atp-wta-itf.p.rapidapi.com")

# 3. VYHLEDÁVÁNÍ
search_query = st.text_input("Zadej jméno hráče (např. Djokovic):", value="Djokovic")

if st.button("🔍 Najít hráče"):
    if not api_key or not url:
        st.error("Chybí Klíč nebo URL!")
    else:
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host,
            "Content-Type": "application/json"
        }
        
        # Matchstat API obvykle vyžaduje POST request s parametrem 'query'
        payload = {"query": search_query}
        
        with st.spinner(f"Hledám hráče '{search_query}'..."):
            try:
                # Zkusíme POST (nejčastější pro search)
                response = requests.post(url, headers=headers, json=payload)
                
                # Pokud POST nefunguje (vrátí chybu), zkusíme GET
                if response.status_code != 200:
                    st.warning("POST nefungoval, zkouším GET...")
                    response = requests.get(url, headers=headers, params={"q": search_query})

                data = response.json()
                
                # Zobrazení výsledků
                st.subheader("Výsledky hledání:")
                st.json(data)
                
                # Pokus o tabulku
                if isinstance(data, list):
                    st.dataframe(pd.DataFrame(data))
                elif 'data' in data:
                    st.dataframe(pd.DataFrame(data['data']))
                
            except Exception as e:
                st.error(f"Chyba: {e}")
