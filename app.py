import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime

# --- NASTAVENÍ STRÁNKY ---\nst.set_page_config(page_title="Tennis Dashboard", layout="wide")

st.title("🎾 Tennis Dashboard: Žebříček & Live Výsledky")

# --- KONTROLA KLÍČŮ ---
if "RAPIDAPI_KEY" not in st.secrets or "RAPIDAPI_HOST" not in st.secrets:
    st.error("Chybí API klíče! Nastav je v .streamlit/secrets.toml")
    st.stop()

headers = {
    "X-RapidAPI-Key": st.secrets["RAPIDAPI_KEY"],
    "X-RapidAPI-Host": st.secrets["RAPIDAPI_HOST"]
}

# --- 1. FUNKCE PRO ŽEBŘÍČEK (CACHE 1 HODINA) ---
@st.cache_data(ttl=3600)
def get_rankings():
    url = "https://tennisapi1.p.rapidapi.com/api/tennis/rankings/wta"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None

# --- 2. FUNKCE PRO LIVE ZÁPASY (CACHE 1 MINUTA) ---
# Toto nahrazuje ten F# bot - stahuje živá data
@st.cache_data(ttl=60) 
def get_live_matches():
    # Endpoint pro live zápasy
    url = "https://tennisapi1.p.rapidapi.com/api/tennis/events/live"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None

# --- ROZCESTNÍK (ZÁLOŽKY) ---
tab1, tab2 = st.tabs(["🏆 Žebříček WTA", "🔴 Live Zápasy (Bot)"])

# ==========================================
# ZÁLOŽKA 1: ŽEBŘÍČEK (To co už jsme měli)
# ==========================================
with tab1:
    data_rankings = get_rankings()
    
    if data_rankings and "rankings" in data_rankings:
        rankings_list = []
        for item in data_rankings["rankings"]:
            try:
                country = item.get("team", {}).get("country", {}).get("name", "N/A")
            except:
                country = "N/A"

            rankings_list.append({
                "Rank": item.get("ranking"),
                "Jméno": item.get("rowName"),
                "Země": country,
                "Body": item.get("points"),
                "Změna": item.get("previousRanking", 0) - item.get("ranking", 0),
            })

        df_rank = pd.DataFrame(rankings_list)
        
        # Filtry a tabulka
        selected_country = st.selectbox("Filtrovat zemi:", ["Všechny"] + sorted(df_rank["Země"].unique().tolist()))
        if selected_country != "Všechny":
            df_rank = df_rank[df_rank["Země"] == selected_country]

        def color_change(val):
            if val > 0: return 'color: green'
            elif val < 0: return 'color: red'
            return 'color: gray'

        st.dataframe(df_rank.style.map(color_change, subset=['Změna']), use_container_width=True, hide_index=True)
    else:
        st.warning("Nepodařilo se načíst žebříček.")

# ==========================================
# ZÁLOŽKA 2: LIVE ZÁPASY (Náhrada F# Bota)
# ==========================================
with tab2:
    st.header("🔴 Aktuální Live Skóre")
    st.caption("Data se aktualizují každou minutu. Simulace funkcionality Bfexplorer bota.")
    
    if st.button("🔄 Obnovit data"):
        get_live_matches.clear() # Vymaže cache pro okamžitý refresh
        st.rerun()

    live_data = get_live_matches()

    if live_data and "events" in live_data:
        live_matches_list = []
        
        for event in live_data["events"]:
            # Zpracování skóre je složité, API ho vrací různě. Zkusíme základní extrakci.
            home_team = event.get("homeTeam", {}).get("name", "Unknown")
            away_team = event.get("awayTeam", {}).get("name", "Unknown")
            
            # Získání aktuálního skóre
            home_score = event.get("homeScore", {})
            away_score = event.get("awayScore", {})
            
            # Formátování skóre do tabulky (Set 1, Set 2...)
            match_info = {
                "Hráč 1 (Domácí)": home_team,
                "Hráč 2 (Hosté)": away_team,
                "Set 1": f"{home_score.get('period1', '-')}:{away_score.get('period1', '-')}",
                "Set 2": f"{home_score.get('period2', '-')}:{away_score.get('period2', '-')}",
                "Set 3": f"{home_score.get('period3', '-')}:{away_score.get('period3', '-')}",
                "Aktuální bod": f"{home_score.get('current', '-')}:{away_score.get('current', '-')}",
                "Status": event.get("status", {}).get("type", "Live")
            }
            
            # Pokus o získání kurzů (pokud je API posílá v 'winnerCode' nebo podobně)
            # Poznámka: RapidAPI verze často neposílá live Betfair kurzy (Back/Lay), 
            # ale zobrazíme alespoň ID zápasu pro referenci.
            match_info["ID Zápasu"] = event.get("id")
            
            live_matches_list.append(match_info)

        if live_matches_list:
            df_live = pd.DataFrame(live_matches_list)
            st.dataframe(df_live, use_container_width=True, hide_index=True)
        else:
            st.info("Právě se nehrají žádné live zápasy.")
            
    else:
        st.info("Žádná data o live zápasech nebo chyba API.")
