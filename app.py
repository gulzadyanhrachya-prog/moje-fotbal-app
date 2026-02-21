import streamlit as st
import pandas as pd
import requests

# --- KONFIGURACE ---
st.set_page_config(page_title="OddsCLI Web", layout="wide")
st.title("📊 OddsCLI Web: Srovnávač kurzů & Arbitráže")

# --- 1. NAČTENÍ KLÍČE ---
# Klíč musí být v .streamlit/secrets.toml jako ODDS_API_KEY = "tvuj_klic"
if "ODDS_API_KEY" not in st.secrets:
    st.error("Chybí API klíč pro The Odds API! Nastav ho v Secrets.")
    st.stop()

API_KEY = st.secrets["ODDS_API_KEY"]
BASE_URL = "https://api.the-odds-api.com/v4/sports"

# --- 2. FUNKCE PRO API ---

@st.cache_data(ttl=3600)
def get_sports():
    """Stáhne seznam dostupných sportů"""
    url = f"{BASE_URL}/?apiKey={API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Chyba při načítání sportů: {e}")
        return []

@st.cache_data(ttl=60) # Cache jen 1 minutu pro live kurzy
def get_odds(sport_key, region, markets):
    """Stáhne kurzy pro vybraný sport"""
    url = f"{BASE_URL}/{sport_key}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": region,
        "markets": markets,
        "oddsFormat": "decimal" # Používáme decimální kurzy (např. 1.95)
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Chyba při načítání kurzů: {e}")
        return []

# --- 3. SIDEBAR (NASTAVENÍ) ---
with st.sidebar:
    st.header("⚙️ Nastavení")
    
    # Výběr regionu (eu = Evropa, us = USA, uk = Británie)
    region = st.selectbox("Region sázkovek", ["eu", "us", "uk", "au"], index=0)
    
    # Načtení sportů
    sports_data = get_sports()
    if not sports_data:
        st.stop()
        
    # Vytvoření slovníku {Název: Klíč}
    sports_dict = {s["title"]: s["key"] for s in sports_data if s["active"]}
    
    # Filtr sportů (např. jen Tenis)
    sport_filter = st.text_input("Hledat sport", "")
    filtered_sports = {k: v for k, v in sports_dict.items() if sport_filter.lower() in k.lower()}
    
    selected_sport_name = st.selectbox("Vyber sport", list(filtered_sports.keys()))
    selected_sport_key = filtered_sports[selected_sport_name]

    st.info(f"Kredit: Aplikace šetří requesty (cache).")

# --- 4. HLAVNÍ LOGIKA ---

if selected_sport_key:
    st.subheader(f"Kurzy pro: {selected_sport_name}")
    
    # Stáhneme data (h2h = vítěz zápasu)
    odds_data = get_odds(selected_sport_key, region, "h2h")
    
    if not odds_data:
        st.warning("Žádné kurzy nejsou momentálně k dispozici.")
    else:
        match_list = []
        
        for event in odds_data:
            home_team = event["home_team"]
            away_team = event["away_team"]
            start_time = event["commence_time"]
            
            # Hledání nejlepších kurzů
            best_home_odds = 0
            best_away_odds = 0
            bookie_home = ""
            bookie_away = ""
            
            all_bookies_str = []

            for bookmaker in event["bookmakers"]:
                try:
                    # Předpokládáme h2h market
                    market = next((m for m in bookmaker["markets"] if m["key"] == "h2h"), None)
                    if not market: continue
                    
                    # Získání kurzů
                    odds_home = next((o["price"] for o in market["outcomes"] if o["name"] == home_team), 0)
                    odds_away = next((o["price"] for o in market["outcomes"] if o["name"] == away_team), 0)
                    
                    # Uložení nejlepších kurzů
                    if odds_home > best_home_odds:
                        best_home_odds = odds_home
                        bookie_home = bookmaker["title"]
                    
                    if odds_away > best_away_odds:
                        best_away_odds = odds_away
                        bookie_away = bookmaker["title"]
                        
                    all_bookies_str.append(f"{bookmaker['title']}: {odds_home} / {odds_away}")
                    
                except Exception:
                    continue

            # Výpočet Arbitráže (Surebet)
            # Vzorec: (1/kurz1) + (1/kurz2) < 1 => Zisk
            if best_home_odds > 0 and best_away_odds > 0:
                arb_percent = (1 / best_home_odds) + (1 / best_away_odds)
                is_arb = arb_percent < 1.0
                profit = (1 - arb_percent) * 100 if is_arb else 0
            else:
                is_arb = False
                profit = 0

            match_list.append({
                "Zápas": f"{home_team} vs {away_team}",
                "Datum": start_time[:10], # Jen datum
                "Domácí (1)": home_team,
                "Nej kurz 1": best_home_odds,
                "Sázkovka 1": bookie_home,
                "Hosté (2)": away_team,
                "Nej kurz 2": best_away_odds,
                "Sázkovka 2": bookie_away,
                "Arbitráž %": round(profit, 2) if is_arb else 0.0,
                "Is_Arb": is_arb
            })

        # Vytvoření tabulky
        df = pd.DataFrame(match_list)
        
        # --- ZOBRAZENÍ ARBITRÁŽÍ (SUREBETS) ---
        arbs = df[df["Is_Arb"] == True]
        if not arbs.empty:
            st.success(f"💰 Nalezeno {len(arbs)} arbitrážních příležitostí (Jistý zisk)!")
            st.dataframe(
                arbs[["Zápas", "Nej kurz 1", "Sázkovka 1", "Nej kurz 2", "Sázkovka 2", "Arbitráž %"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Žádné arbitráže (surebets) momentálně nenalezeny.")

        st.divider()
        
        # --- ZOBRAZENÍ VŠECH KURZŮ ---
        st.subheader("Přehled všech zápasů")
        
        # Obarvení tabulky
        st.dataframe(
            df[["Datum", "Domácí (1)", "Nej kurz 1", "Sázkovka 1", "Hosté (2)", "Nej kurz 2", "Sázkovka 2"]],
            use_container_width=True,
            hide_index=True
        )
