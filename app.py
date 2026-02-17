import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime

# 1. Nastavení stránky
st.set_page_config(page_title="Sofascore API Explorer", layout="wide")
st.title("🕵️‍♂️ Průzkumník Sofascore/Sport API")
st.caption("Toto API je obrovské. Pojďme najít správná data pro predikce.")

# 2. Načtení klíče
try:
    api_key = st.secrets["RAPIDAPI_KEY"]
    st.sidebar.success("✅ API Klíč načten")
except:
    api_key = st.sidebar.text_input("Vlož X-RapidAPI-Key:", type="password")

# 3. Konfigurace Endpointu
st.sidebar.header("Nastavení")

# Zde vlož URL z RapidAPI (sekce 'Events', 'Matches' nebo 'Schedule')
# Příklad pro Sofascore klony: https://api-sofascore.p.rapidapi.com/events/schedule/date
default_url = st.sidebar.text_input("URL Endpointu:", value="")
default_host = st.sidebar.text_input("X-RapidAPI-Host:", value="")

# Výběr data (API většinou vyžaduje formát YYYY-MM-DD)
selected_date = st.sidebar.date_input("Vyber datum zápasů:", datetime.now())
date_str = selected_date.strftime("%Y-%m-%d")

# Parametry (Sofascore často používá 'date' nebo je datum přímo v URL)
# Zkusíme univerzální parametry
params = {
    "date": date_str,
    "sport": "football" # Někdy API vyžaduje specifikaci sportu
}

if st.button("📡 Stáhnout data"):
    if not api_key or not default_url:
        st.error("Chybí Klíč nebo URL!")
    else:
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": default_host
        }
        
        with st.spinner(f"Stahuji data pro {date_str}..."):
            try:
                # Některá API mají datum přímo v URL (např. .../events/2024-05-20)
                # Zkusíme poslat parametry, pokud to API podporuje
                response = requests.get(default_url, headers=headers, params=params)
                data = response.json()
                
                # 1. Zobrazení JSONu (Klíčové pro nás!)
                st.subheader("🔍 Struktura dat")
                st.write("Podívej se, jestli vidíš 'homeTeam', 'awayTeam', 'score'.")
                st.json(data)
                
                # 2. Pokus o nalezení seznamu zápasů
                # Sofascore často vrací data v klíči 'events' nebo 'tournaments'
                found_events = []
                
                if 'events' in data:
                    found_events = data['events']
                elif 'response' in data:
                    found_events = data['response']
                
                if found_events:
                    st.success(f"Nalezeno {len(found_events)} událostí!")
                    # Rychlý výpis prvních 3 zápasů pro kontrolu
                    for i, event in enumerate(found_events[:3]):
                        st.info(f"Zápas {i+1}: {event}")
                else:
                    st.warning("Nevidím klíč 'events' ani 'response'. Musíš prozkoumat JSON výše.")

            except Exception as e:
                st.error(f"Chyba: {e}")
