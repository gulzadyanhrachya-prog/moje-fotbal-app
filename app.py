import streamlit as st
import requests
import pandas as pd
import json

# 1. Nastavení stránky
st.set_page_config(page_title="RapidAPI Explorer", layout="wide")
st.title("🚀 RapidAPI Data Viewer")
st.caption("Nejdřív musíme zjistit, jak tvé API posílá data, abychom mohli postavit model.")

# 2. Načtení klíče (Bezpečně ze Secrets)
try:
    api_key = st.secrets["RAPIDAPI_KEY"]
    st.sidebar.success("✅ API Klíč načten")
except:
    api_key = st.sidebar.text_input("Vlož X-RapidAPI-Key:", type="password")

# 3. Konfigurace API (Zde zadáš údaje z webu RapidAPI)
st.sidebar.header("Nastavení Endpointu")
url = st.sidebar.text_input("URL (např. https://api-football-v1...):")
host = st.sidebar.text_input("Host (např. api-football-v1.p.rapidapi.com):")
params_str = st.sidebar.text_input("Parametry (JSON, např. {'league':'39', 'season':'2023'}):", value="{}")

# 4. Tlačítko pro stažení
if st.button("📡 Stáhnout data"):
    if not api_key or not url or not host:
        st.error("Chybí klíč, URL nebo Host!")
    else:
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host
        }
        
        try:
            # Převod parametrů z textu na slovník
            params = json.loads(params_str)
            
            with st.spinner("Stahuji data..."):
                response = requests.get(url, headers=headers, params=params)
                
                if response.status_code != 200:
                    st.error(f"Chyba API: {response.status_code}")
                    st.text(response.text)
                else:
                    data = response.json()
                    st.success("Data stažena!")
                    
                    # Zobrazení JSONu (tohle potřebujeme vidět!)
                    st.subheader("🔍 Struktura dat (JSON)")
                    st.json(data)
                    
                    # Pokus o tabulku
                    st.subheader("📊 Tabulka")
                    # RapidAPI má data často v 'response'
                    if 'response' in data:
                        df = pd.json_normalize(data['response'])
                        st.dataframe(df)
                    else:
                        st.write("Data nejsou v klíči 'response', podívej se do JSONu výše.")

        except Exception as e:
            st.error(f"Chyba: {e}")
