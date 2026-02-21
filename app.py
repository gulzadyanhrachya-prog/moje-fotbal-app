import streamlit as st
import pandas as pd
import numpy as np
import requests
import re
from datetime import datetime
from thefuzz import process

# ==============================================================================\
# 1. KONFIGURACE A STYLY
# ==============================================================================\
st.set_page_config(page_title="Tennis AI Betting v6.0", layout="wide", page_icon="🎾")

st.markdown("""
<style>
    .tip-card { background-color: #d4edda; padding: 15px; border-radius: 10px; border-left: 5px solid #28a745; margin-bottom: 10px; }
    .match-card { background-color: #ffffff; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #e0e0e0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .tour-header { font-size: 14px; color: #666; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
    .player-name { font-size: 18px; font-weight: bold; }
    .vs { color: #999; font-size: 14px; margin: 0 10px; }
    .prediction-box { margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee; }
</style>
""", unsafe_allow_html=True)

st.title("🎾 Tennis AI: Scraper & Predictor")
st.caption("Automaticky stahuje program z TennisExplorer, čistí data a počítá predikce.")

# ==============================================================================\
# 2. NAČTENÍ HISTORICKÝCH DAT (MOZEK)
# ==============================================================================\
@st.cache_data(ttl=3600)
def load_historical_data():
    base_atp = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{}.csv"
    base_wta = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_{}.csv"
    
    years = [2024, 2025, 2026] 
    data_frames = []
    
    status_text = st.empty()
    status_text.text("⏳ Načítám databázi hráčů...")
    
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
else:
    db_players = []

# ==============================================================================\
# 3. CHYTRÝ PARSER (ČISTIČKA DAT Z WEBU)
# ==============================================================================\
def clean_player_name(name):
    # Odstraní nasazení v závorce, např. "Alcaraz C. (1)" -> "Alcaraz C."
    name = re.sub(r'\(\d+\)', '', name).strip()
    # Odstraní "ret." nebo "w.o."
    name = name.replace("ret.", "").replace("w.o.", "").strip()
    return name

def parse_tennis_explorer(df):
    """
    Tato funkce vezme tu 'rozsypanou' tabulku a udělá z ní seznam zápasů.
    """
    matches = []
    current_tournament = "Unknown Tournament"
    
    # Procházíme tabulku řádek po řádku
    # Hledáme dvojice hráčů
    pending_player = None
    pending_time = None
    
    # Převedeme na stringy a zahodíme prázdné
    df = df.astype(str)
    
    for index, row in df.iterrows():
        # Sloupec 0 obvykle obsahuje Čas nebo je prázdný u turnaje
        # Sloupec 1 obvykle obsahuje Jméno hráče nebo Název turnaje
        
        col0 = str(row[0]).strip()
        col1 = str(row[1]).strip()
        
        # 1. DETEKCE TURNAJE
        # Pokud řádek obsahuje "H2H" nebo "S" (Set), je to hlavička turnaje
        if "H2H" in row.values or "S" in str(row.values):
            # Název turnaje bývá v prvním nebo druhém sloupci
            possible_name = col0 if len(col0) > 3 else col1
            if possible_name and "H2H" not in possible_name:
                current_tournament = possible_name
            pending_player = None # Reset
            continue
            
        # 2. DETEKCE ZÁPASU (Hledáme čas ve formátu HH:MM nebo slovo Live)
        is_match_row = False
        if ":" in col0 and len(col0) <= 5: is_match_row = True
        if "Live" in col0: is_match_row = True
        
        if is_match_row:
            # Jméno hráče je obvykle ve sloupci 1
            raw_name = col1
            
            # Pokud je jméno příliš krátké nebo je to skóre, ignorujeme
            if len(raw_name) < 3 or raw_name.replace('.','').isdigit():
                continue
                
            clean_name = clean_player_name(raw_name)
            
            if pending_player is None:
                # Našli jsme prvního hráče z dvojice
                pending_player = clean_name
                pending_time = col0
            else:
                # Našli jsme druhého hráče -> MÁME ZÁPAS!
                matches.append({
                    "tournament": current_tournament,
                    "time": pending_time,
                    "p1": pending_player,
                    "p2": clean_name
                })
                pending_player = None # Reset pro další dvojici
                
    return matches

# ==============================================================================\
# 4. PREDIKČNÍ LOGIKA
# ==============================================================================\
def find_player_in_db(scraped_name):
    # TennisExplorer: "Alcaraz C." -> DB: "Carlos Alcaraz"
    if not scraped_name or not db_players: return None
    
    # Zkusíme prohodit jméno a příjmení pro lepší shodu
    # "Alcaraz C." -> "C. Alcaraz"
    parts = scraped_name.split()
    if len(parts) > 1:
        reversed_name = f"{parts[-1]} {parts[0]}" # C. Alcaraz
    else:
        reversed_name = scraped_name
        
    # Hledáme nejlepší shodu pro obě varianty
    match1 = process.extractOne(scraped_name, db_players)
    match2 = process.extractOne(reversed_name, db_players)
    
    best_match = match1 if match1[1] >= match2[1] else match2
    
    if best_match and best_match[1] > 80: # 80% shoda stačí
        return best_match[0]
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

# ==============================================================================\
# 5. UI APLIKACE
# ==============================================================================\

# Tlačítko pro stažení
if st.button("📡 Stáhnout dnešní program (TennisExplorer)", type="primary"):
    
    with st.spinner("Stahuji data z webu a analyzuji..."):
        try:
            # 1. Scraping
            url = "https://www.tennisexplorer.com/matches/?type=atp-single" # ATP Singles
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers)
            
            # Načteme všechny tabulky
            dfs = pd.read_html(r.text)
            
            # Najdeme tu největší tabulku (to je ta s programem)
            main_df = max(dfs, key=len)
            
            # 2. Parsing (Čištění)
            parsed_matches = parse_tennis_explorer(main_df)
            
            if not parsed_matches:
                st.error("Nepodařilo se najít zápasy v tabulce. Web mohl změnit strukturu.")
                st.dataframe(main_df.head()) # Debug
            else:
                st.success(f"Nalezeno {len(parsed_matches)} zápasů! Počítám predikce...")
                
                # 3. Predikce pro každý zápas
                results = []
                
                progress_bar = st.progress(0)
                for i, m in enumerate(parsed_matches):
                    # Určení povrchu podle turnaje (zjednodušené)
                    surface = "Hard" # Default
                    tour_lower = m['tournament'].lower()
                    if "clay" in tour_lower or "rio" in tour_lower or "buenos" in tour_lower: surface = "Clay"
                    if "grass" in tour_lower: surface = "Grass"
                    if "doha" in tour_lower: surface = "Hard"
                    
                    # Hledání v DB
                    p1_db = find_player_in_db(m['p1'])
                    p2_db = find_player_in_db(m['p2'])
                    
                    prob = 0.5
                    winner = "Neznámý"
                    
                    if p1_db and p2_db:
                        prob1 = calculate_win_prob(p1_db, surface)
                        prob2 = calculate_win_prob(p2_db, surface)
                        
                        total = prob1 + prob2
                        if total > 0:
                            final1 = prob1 / total
                            if final1 > 0.5:
                                prob = final1
                                winner = p1_db
                            else:
                                prob = 1 - final1
                                winner = p2_db
                        
                        results.append({
                            "time": m['time'],
                            "tour": m['tournament'],
                            "p1_web": m['p1'], "p2_web": m['p2'],
                            "p1_db": p1_db, "p2_db": p2_db,
                            "winner": winner,
                            "prob": prob,
                            "surface": surface
                        })
                    progress_bar.progress((i + 1) / len(parsed_matches))
                
                # 4. Vykreslení výsledků
                
                # A) TOP TIPY (Důvěra > 65%)
                st.subheader("🔥 NEJLEPŠÍ TIPY DNE")
                results.sort(key=lambda x: x['prob'], reverse=True)
                
                top_tips = [r for r in results if r['prob'] > 0.65]
                
                if top_tips:
                    for tip in top_tips[:5]:
                        st.markdown(f"""
                        <div class="tip-card">
                            <div class="tour-header">{tip['tour']} ({tip['surface']}) | {tip['time']}</div>
                            <div class="player-name">🏆 {tip['winner']}</div>
                            <div class="vs">{tip['p1_db']} vs {tip['p2_db']}</div>
                            <div>Důvěra modelu: <strong>{int(tip['prob']*100)}%</strong></div>
                            <div>Férový kurz: <strong>{round(1/tip['prob'], 2)}</strong></div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("Dnes žádné 'tutovky' (nad 65%). Zápasy jsou vyrovnané.")
                
                # B) KOMPLETNÍ PROGRAM
                st.divider()
                st.subheader("📋 Kompletní program a analýza")
                
                for res in results:
                    with st.container():
                        c1, c2, c3, c4 = st.columns([1, 3, 2, 2])
                        with c1:
                            st.caption(res['time'])
                        with c2:
                            st.write(f"**{res['p1_web']}** vs **{res['p2_web']}**")
                            st.caption(f"{res['tour']}")
                        with c3:
                            if res['prob'] > 0.55:
                                st.markdown(f"<span style='color:green'>Tip: {res['winner']}</span>", unsafe_allow_html=True)
                            else:
                                st.write("Vyrovnané")
                        with c4:
                            st.progress(res['prob'])
                            st.caption(f"{int(res['prob']*100)}%")
                        st.markdown("---")

        except Exception as e:
            st.error(f"Chyba při stahování: {e}")
            st.info("Zkus to za chvíli znovu, web může být přetížený.")

# Manuální sekce pro jistotu
st.divider()
st.subheader("🔍 Nenašel jsi zápas? Zadej ho ručně")
col1, col2, col3 = st.columns(3)
with col1:
    man_p1 = st.selectbox("Hráč 1", db_players, key="m1")
with col2:
    man_p2 = st.selectbox("Hráč 2", db_players, key="m2")
with col3:
    if st.button("Analyzovat"):
        # ... (zde by byla stejná logika výpočtu)
        pass
