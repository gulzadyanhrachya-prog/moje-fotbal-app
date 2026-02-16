import streamlit as st
import requests
import pandas as pd
import json

# ==============================================================================
# 1. NASTAVENÍ STRÁNKY
# ==============================================================================
st.set_page_config(page_title="Můj RapidAPI Projekt", layout="wide")
st.title("🚀 RapidAPI Data Viewer")

# ==============================================================================
# 2. NAČTENÍ KLÍČE (BEZPEČNĚ)
# ==============================================================================
# Aplikace se nejdřív podívá do tajných "Secrets" na Streamlit Cloudu.
# Pokud tam klíč není (např. testuješ lokálně), zeptá se tě v bočním menu.
try:
    api_key = st.secrets["RAPIDAPI_KEY"]
    st.sidebar.success("✅ API Klíč načten ze systému")
except:
    api_key = st.sidebar.text_input("Vlož svůj X-RapidAPI-Key:", type="password")
    if not api_key:
        st.warning("⬅️ Pro pokračování vlož API klíč do menu vlevo.")
        st.stop()

# ==============================================================================
# 3. KONFIGURACE API (Zde zadáš údaje z RapidAPI webu)
# ==============================================================================
st.sidebar.header("Nastavení Endpointu")
st.sidebar.info("Tyto údaje najdeš na RapidAPI v sekci 'Code Snippets'")

# Předvyplněné hodnoty (můžeš si je v kódu změnit na své API, abys to nemusel vypisovat)
default_url = "https://api-football-v1.p.rapidapi.com/v3/leagues"
default_host = "api-football-v1.p.rapidapi.com"

url = st.sidebar.text_input("URL Endpointu:", value=default_url)
host = st.sidebar.text_input("X-RapidAPI-Host:", value=default_host)
params_input = st.sidebar.text_input("Parametry (volitelné, např. {'id':'39'}):", value="{}")

# ==============================================================================
# 4. STAŽENÍ A ZOBRAZENÍ DAT
# ==============================================================================
if st.button("📡 Stáhnout data z API"):
    if not url or not host:
        st.error("Chybí URL nebo Host!")
    else:
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host
        }
        
        # Převod parametrů z textu na slovník
        try:
            querystring = json.loads(params_input)
        except:
            st.error("Chyba v parametrech. Musí to být platný JSON (např. {}).")
            st.stop()

        with st.spinner("Komunikuji se serverem..."):
            try:
                response = requests.get(url, headers=headers, params=querystring)
                
                # Kontrola stavu
                if response.status_code != 200:
                    st.error(f"Chyba API: {response.status_code}")
                    st.text(response.text)
                else:
                    data = response.json()
                    st.success("Data úspěšně stažena!")

                    # A. Zobrazení surových dat (pro vývojáře)
                    with st.expander("🔍 Zobrazit surový JSON (Struktura dat)", expanded=True):
                        st.json(data)

                    # B. Pokus o tabulku
                    st.subheader("📊 Náhled dat")
                    # RapidAPI vrací data často v klíči 'response', 'data' nebo 'results'
                    found_data = None
                    if isinstance(data, list):
                        found_data = data
                    elif 'response' in data:
                        found_data = data['response']
                    elif 'data' in data:
                        found_data = data['data']
                    
                    if found_data and isinstance(found_data, list):
                        df = pd.json_normalize(found_data)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Data nejsou v jednoduchém seznamu, podívej se do JSONu výše.")

            except Exception as e:
                st.error(f"Nastala chyba v aplikaci: {e}")
