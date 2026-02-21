import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from thefuzz import process

# ==============================================================================
# 1. KONFIGURACE A STYLY
# ==============================================================================
st.set_page_config(page_title="Tennis AI Analyst (No-API)", layout="wide", page_icon="🎾")

st.markdown("""
<style>
    .tip-card { background-color: #d4edda; padding: 15px; border-radius: 10px; border-left: 5px solid #28a745; margin-bottom: 10px; }
    .match-card { background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 5px; border: 1px solid #ddd; }
    .high-conf { color: #28a745; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🎾 Tennis AI: Web Scraper & Predictor")
st.caption("Zdroj dat: Jeff Sackmann (Historie) + TennisExplorer (Dnešní program)")

# ==============================================================================
# 2. NAČTENÍ HISTORICKÝCH DAT (MOZEK)
# ==============================================================================
@st.cache_data(ttl=3600)
def load_historical_data():
    base_atp = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{}.csv"
    base_wta = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_{}.csv"
    
    years = [2024, 2025, 2026] 
    data_frames = []
    
    status_text = st.empty()
    status_text.text("⏳ Načítám historickou databázi...")
    
    for year in years:
        try:
            df_atp = pd.read_csv(base_atp.format(year), on_bad_lines='skip')
            df_atp['tour'] = 'ATP'
            data_frames.append(df_atp)
            
            df_wta = pd.read_csv(base_wta.format(year), on_bad_lines='skip')
            df_wta['tour'] = 'WTA'
            data_frames.append(df_wta)
        except: pass
            
    status_text.empty()
    
    if not data_frames: return pd.DataFrame()
    
    full_df = pd.concat(data_frames, ignore_index=True)
    full_df['tourney_date'] = pd.to_datetime(full_df['tourney_date'], format='%Y%m%d', errors='coerce')
    return full_df

df_history = load_historical_data()

if not df_history.empty:
    db_players = pd.concat([df_history['winner_name'], df_history['loser_name']]).unique()
    db_players = [str(p) for p in db_players if isinstance(p, str)]
    db_players.sort()
else:
    db_players = []

# ==============================================================================
# 3. FUNKCE PRO SCRAPING (NOVÝ ZDROJ PROGRAMU)
# ==============================================================================
@st.cache_data(ttl=1800) # Cache na 30 minut
def scrape_tennis_explorer():
    # Stáhneme dnešní zápasy z TennisExplorer.com
    # Používáme pandas read_html, což je nejjednodušší scraper tabulek
    url = "https://www.tennisexplorer.com/matches/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        r = requests.get(url, headers=headers)
        if r.status_code != 200: return []
        
        # Pandas najde všechny tabulky na stránce
        dfs = pd.read_html(r.text)
        
        matches = []
        
        # Projdeme tabulky a hledáme tu se zápasy
        for df in dfs:
            # Tabulka zápasů má obvykle sloupce, kde jsou jména hráčů
            # TennisExplorer má specifickou strukturu, musíme filtrovat
            if len(df.columns) > 4:
                # Převedeme na stringy
                df = df.astype(str)
                
                for index, row in df.iterrows():
                    # Hledáme řádky, kde jsou jména hráčů
                    # TennisExplorer formát: [Čas, Hráč1, Výsledek, Hráč2, ...]
                    # Zkusíme jednoduchou heuristiku
                    try:
                        # Sloupce nemají jména, musíme podle indexů
                        # Obvykle: 0=Time, 1=Player1, ..., Player2 je dál
                        row_text = " ".join(row.values)
                        
                        # Pokud řádek obsahuje jména, zkusíme je vytáhnout
                        # Toto je zjednodušené, protože scraping je křehký
                        # Pro TennisExplorer je lepší iterovat a hledat buňky s textem
                        pass
                    except: continue
        
        # ALTERNATIVA: Protože read_html může být zmatený, uděláme to jednodušeji
        # Vrátíme jen informaci, že scraping běží, a použijeme manuální vstup
        # nebo zkusíme najít konkrétní tabulku
        
        # Pro účely tohoto dema a stability na Streamlit Cloudu:
        # Scraping často selže kvůli ochraně webů.
        # Vytvoříme raději "Simulovaný" seznam nebo vyzveme uživatele k manuálnímu zadání.
        
        return [] # Vracíme prázdno, pokud se nepodaří spolehlivě parsovat
        
    except Exception as e:
        return []

# ==============================================================================
# 4. POMOCNÉ FUNKCE
# ==============================================================================
def find_player_in_db(name_query):
    if not name_query or not db_players: return None
    match = process.extractOne(name_query, db_players)
    if match and match[1] > 85: return match[0]
    return None

def calculate_win_prob(player, surface):
    if df_history.empty: return 0.5
    
    wins = df_history[df_history['winner_name'] == player]
    losses = df_history[df_history['loser_name'] == player]
    
    total = len(wins) + len(losses)
    if total < 5: return 0.5 
    
    wins_surf = wins[wins['surface'] == surface]
    losses_surf = losses[losses['surface'] == surface]
    surf_total = len(wins_surf) + len(losses_surf)
    
    wr_total = len(wins) / total
    wr_surf = len(wins_surf) / surf_total if surf_total > 0 else wr_total
    
    return (wr_surf * 0.7) + (wr_total * 0.3)

# ==============================================================================
# 5. UI APLIKACE
# ==============================================================================

# Záložky
tab1, tab2 = st.tabs(["🔍 Manuální Analýza (Spolehlivé)", "🌍 Web Scraper (Beta)"])

# --- TAB 1: MANUÁLNÍ ANALÝZA (HLAVNÍ FUNKCE) ---
with tab1:
    st.header("⚔️ Analýza zápasu")
    st.caption("Vyber dva hráče z databáze a zjisti, kdo má větší šanci.")
    
    col_s, col_p1, col_p2 = st.columns(3)
    surface_man = col_s.selectbox("Povrch:", ["Hard", "Clay", "Grass"], index=0)
    
    if not df_history.empty:
        # Defaultní indexy
        idx1 = db_players.index("Jannik Sinner") if "Jannik Sinner" in db_players else 0
        idx2 = db_players.index("Carlos Alcaraz") if "Carlos Alcaraz" in db_players else 1

        p1_man = col_p1.selectbox("Hráč 1:", db_players, index=idx1)
        p2_man = col_p2.selectbox("Hráč 2:", db_players, index=idx2)
        
        if st.button("🚀 Analyzovat duel", type="primary"):
            prob1 = calculate_win_prob(p1_man, surface_man)
            prob2 = calculate_win_prob(p2_man, surface_man)
            
            total = prob1 + prob2
            if total > 0:
                final1 = prob1 / total
                final2 = prob2 / total
            else:
                final1 = 0.5
                final2 = 0.5
            
            # Výpočet kurzů
            odd1 = round(1/final1, 2) if final1 > 0 else 99
            odd2 = round(1/final2, 2) if final2 > 0 else 99
            
            # Zobrazení výsledku
            st.divider()
            c1, c2, c3 = st.columns([2, 1, 2])
            
            with c1:
                st.markdown(f"<h2 style='text-align: center; color: #333;'>{p1_man}</h2>", unsafe_allow_html=True)
                if final1 > 0.5:
                    st.success(f"🏆 FAVORIT ({int(final1*100)}%)")
                else:
                    st.write(f"Šance: {int(final1*100)}%")
                st.metric("Férový kurz", odd1)
                
            with c2:
                st.markdown("<h3 style='text-align: center; padding-top: 20px;'>VS</h3>", unsafe_allow_html=True)
                
            with c3:
                st.markdown(f"<h2 style='text-align: center; color: #333;'>{p2_man}</h2>", unsafe_allow_html=True)
                if final2 > 0.5:
                    st.success(f"🏆 FAVORIT ({int(final2*100)}%)")
                else:
                    st.write(f"Šance: {int(final2*100)}%")
                st.metric("Férový kurz", odd2)
            
            st.progress(final1)
            
            # H2H Historie
            st.subheader("📜 Vzájemné zápasy (2024-2026)")
            h2h = df_history[((df_history['winner_name'] == p1_man) & (df_history['loser_name'] == p2_man)) | 
                             ((df_history['winner_name'] == p2_man) & (df_history['loser_name'] == p1_man))]
            
            if not h2h.empty:
                st.dataframe(h2h[['tourney_date', 'winner_name', 'score', 'surface', 'tour']], hide_index=True, use_container_width=True)
            else:
                st.info("V databázi nejsou žádné vzájemné zápasy z posledních let.")

# --- TAB 2: SCRAPER (EXPERIMENTÁLNÍ) ---
with tab2:
    st.header("🌍 Dnešní program (TennisExplorer)")
    st.caption("Pokusí se stáhnout program z webu. Pokud to nefunguje (blokace), použij Manuální analýzu.")
    
    if st.button("📡 Zkusit stáhnout program"):
        try:
            # Jednoduchý pokus o načtení tabulek
            url = "https://www.tennisexplorer.com/matches/?type=atp-single"
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers)
            
            dfs = pd.read_html(r.text)
            found_matches = []
            
            # Hledáme tabulku s nejvíce řádky
            main_df = max(dfs, key=len)
            
            # Zobrazíme surová data pro výběr
            st.dataframe(main_df.head(20))
            st.info("Scraping je složitý. Pro přesnou predikci doporučuji použít záložku 'Manuální Analýza' a zadat jména hráčů, které vidíš v tabulce výše.")
            
        except Exception as e:
            st.error(f"Nepodařilo se stáhnout data z webu (ochrana proti botům). Chyba: {e}")
            st.info("💡 Tip: Otevři si v prohlížeči Livesport/Flashscore a jména přepiš do záložky 'Manuální Analýza'. Je to nejjistější.")
