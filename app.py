import streamlit as st
import pandas as pd
import numpy as np
import requests
import re
from datetime import datetime, timedelta
from thefuzz import process

# ==============================================================================
# 1. KONFIGURACE A STYLY
# ==============================================================================
st.set_page_config(page_title="Tennis Betting AI v7.0", layout="wide", page_icon="🎾")

st.markdown("""
<style>
    .tip-card { background-color: #d4edda; padding: 15px; border-radius: 10px; border-left: 5px solid #28a745; margin-bottom: 10px; }
    .market-box { background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 5px; border: 1px solid #eee; font-size: 0.9em; }
    .high-conf { color: #28a745; font-weight: bold; }
    .risk-conf { color: #dc3545; font-weight: bold; }
    .section-title { font-size: 1.2em; font-weight: bold; margin-top: 10px; margin-bottom: 5px; color: #333; }
</style>
""", unsafe_allow_html=True)

st.title("🎾 Tennis AI: Advanced Markets & Predictions")
st.caption("Analýza 18 sázkových trhů | Data: Jeff Sackmann (2024-2026) | Scraper: TennisExplorer")

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
    status_text.text("⏳ Načítám databázi hráčů a statistik...")
    
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
    
    # Převedení statistik servisu na čísla (pro analýzu holdů)
    cols_to_numeric = ['w_SvGms', 'w_bpSaved', 'w_bpFaced', 'l_SvGms', 'l_bpSaved', 'l_bpFaced']
    for col in cols_to_numeric:
        if col in full_df.columns:
            full_df[col] = pd.to_numeric(full_df[col], errors='coerce').fillna(0)
            
    return full_df

df_history = load_historical_data()

if not df_history.empty:
    db_players = pd.concat([df_history['winner_name'], df_history['loser_name']]).unique()
    db_players = [str(p) for p in db_players if isinstance(p, str)]
    db_players.sort()
else:
    db_players = []

# ==============================================================================
# 3. POKROČILÝ STATISTICKÝ ENGINE
# ==============================================================================
def parse_score(score_str):
    """Rozparsuje skóre (např. '6-4 7-6(5)') na sety a gamy."""
    if not isinstance(score_str, str) or 'RET' in score_str or 'W/O' in score_str:
        return None
    
    sets = score_str.split(' ')
    parsed_sets = []
    
    for s in sets:
        # Odstranění tiebreak čísel v závorce
        s_clean = re.sub(r'\(\d+\)', '', s)
        if '-' in s_clean:
            try:
                w, l = map(int, s_clean.split('-'))
                parsed_sets.append((w, l))
            except: pass
            
    return parsed_sets

def get_advanced_stats(player, surface):
    """Vypočítá detailní statistiky hráče pro všechny trhy."""
    if df_history.empty: return None
    
    # Filtrujeme zápasy
    wins = df_history[df_history['winner_name'] == player]
    losses = df_history[df_history['loser_name'] == player]
    
    # Filtrujeme povrch (pokud je málo dat, bereme vše)
    wins_surf = wins[wins['surface'] == surface]
    losses_surf = losses[losses['surface'] == surface]
    
    if len(wins_surf) + len(losses_surf) < 5:
        # Fallback na všechny povrchy
        all_wins = wins
        all_losses = losses
    else:
        all_wins = wins_surf
        all_losses = losses_surf
        
    total_matches = len(all_wins) + len(all_losses)
    if total_matches == 0: return None
    
    stats = {
        "matches": total_matches,
        "win_rate": len(all_wins) / total_matches,
        "first_set_win_rate": 0,
        "tiebreak_rate": 0,
        "bagel_rate": 0, # 6-0
        "avg_games_won": 0,
        "avg_games_lost": 0,
        "hold_serve_rate": 0.75, # Default ATP průměr
        "break_serve_rate": 0.20 # Default ATP průměr
    }
    
    # Analýza skóre
    first_set_wins = 0
    tiebreaks = 0
    bagels = 0
    total_games_won = 0
    total_games_lost = 0
    
    # Procházíme výhry
    for _, row in all_wins.iterrows():
        sets = parse_score(row['score'])
        if not sets: continue
        
        # 1. set
        if sets[0][0] > sets[0][1]: first_set_wins += 1
        
        # Gamy a Tiebreaky
        for w_g, l_g in sets:
            total_games_won += w_g
            total_games_lost += l_g
            if w_g == 7 or l_g == 7: tiebreaks += 1
            if w_g == 6 and l_g == 0: bagels += 1 # Dal kanára
            
    # Procházíme prohry
    for _, row in all_losses.iterrows():
        sets = parse_score(row['score'])
        if not sets: continue
        
        # 1. set (z pohledu poraženého, takže první číslo je vítěz zápasu, druhé poražený)
        # V DB je skóre vždy z pohledu vítěze, např. 6-4. Poražený tedy prohrál 4-6.
        if sets[0][1] > sets[0][0]: first_set_wins += 1 # Poražený vyhrál 1. set
        
        for w_g, l_g in sets:
            total_games_won += l_g # Poražený získal l_g
            total_games_lost += w_g
            if w_g == 7 or l_g == 7: tiebreaks += 1
            if w_g == 6 and l_g == 0: bagels += 1 # Dostal kanára (počítáme výskyt v zápase)

    stats["first_set_win_rate"] = first_set_wins / total_matches
    stats["tiebreak_rate"] = tiebreaks / total_matches # Pravděpodobnost TB v zápase
    stats["bagel_rate"] = bagels / total_matches
    stats["avg_games_won"] = total_games_won / total_matches
    stats["avg_games_lost"] = total_games_lost / total_matches
    
    # Analýza servisu (pokud jsou data)
    sv_gms = all_wins['w_SvGms'].sum() + all_losses['l_SvGms'].sum()
    bp_faced = all_wins['w_bpFaced'].sum() + all_losses['l_bpFaced'].sum()
    bp_saved = all_wins['w_bpSaved'].sum() + all_losses['l_bpSaved'].sum()
    
    if sv_gms > 0:
        # Odhad hold rate: (Service Games - Breaks Conceded) / Service Games
        breaks_conceded = bp_faced - bp_saved
        stats["hold_serve_rate"] = max(0, (sv_gms - breaks_conceded) / sv_gms)
        
    return stats

def generate_all_markets(p1_name, p2_name, surface):
    """Generuje pravděpodobnosti pro všech 18 trhů."""
    s1 = get_advanced_stats(p1_name, surface)
    s2 = get_advanced_stats(p2_name, surface)
    
    if not s1 or not s2: return None
    
    markets = []
    
    # 1. VÍTĚZ ZÁPASU
    prob_p1 = (s1['win_rate'] * 0.6 + s1['hold_serve_rate'] * 0.4)
    prob_p2 = (s2['win_rate'] * 0.6 + s2['hold_serve_rate'] * 0.4)
    total = prob_p1 + prob_p2
    p1_win_prob = prob_p1 / total
    
    markets.append({"market": "Vítěz zápasu", "selection": p1_name, "prob": p1_win_prob})
    markets.append({"market": "Vítěz zápasu", "selection": p2_name, "prob": 1 - p1_win_prob})
    
    # 2. VÍTĚZ 1. SETU
    p1_fs_prob = (s1['first_set_win_rate'] + (1 - s2['first_set_win_rate'])) / 2
    markets.append({"market": "Vítěz 1. setu", "selection": p1_name, "prob": p1_fs_prob})
    
    # 3. POČET GAMŮ V 1. SETU (Over 9.5)
    # Pokud oba dobře servírují, bude to over
    avg_hold = (s1['hold_serve_rate'] + s2['hold_serve_rate']) / 2
    prob_over_95 = 0.3 + (avg_hold * 0.6) # Heuristika
    markets.append({"market": "Počet gamů 1. set", "selection": "Over 9.5", "prob": prob_over_95})
    
    # 4. TIEBREAK V ZÁPASU
    tb_prob = (s1['tiebreak_rate'] + s2['tiebreak_rate']) / 2
    # Zvýšíme pravděpodobnost, pokud je to rychlý povrch
    if surface in ['Grass', 'Hard']: tb_prob *= 1.2
    markets.append({"market": "Tiebreak v zápasu", "selection": "ANO", "prob": min(tb_prob, 0.8)})
    
    # 5. VYHRAJE SVŮJ PRVNÍ SERVIS GAME
    # Odvozeno z Hold Rate
    markets.append({"market": "Vyhraje 1. servis game", "selection": p1_name, "prob": s1['hold_serve_rate']})
    markets.append({"market": "Vyhraje 1. servis game", "selection": p2_name, "prob": s2['hold_serve_rate']})
    
    # 6. PŘESNÝ VÝSLEDEK (Zápas)
    # Zjednodušený model pro 2-setové zápasy
    if p1_win_prob > 0.7:
        markets.append({"market": "Přesný výsledek", "selection": "2:0", "prob": p1_win_prob * 0.7})
    elif p1_win_prob < 0.3:
        markets.append({"market": "Přesný výsledek", "selection": "0:2", "prob": (1-p1_win_prob) * 0.7})
    else:
        markets.append({"market": "Přesný výsledek", "selection": "2:1 / 1:2", "prob": 0.6}) # Vyrovnané
        
    # 7. HANDICAP GAMŮ (Zápas)
    # Odhad rozdílu gamů
    diff = (s1['avg_games_won'] - s1['avg_games_lost']) - (s2['avg_games_won'] - s2['avg_games_lost'])
    handicap_line = round(diff)
    if handicap_line == 0: handicap_line = -0.5 if p1_win_prob > 0.5 else 0.5
    
    markets.append({"market": "Handicap gamů", "selection": f"{p1_name} ({handicap_line})", "prob": 0.55}) # 50/50 line
    
    # 8. POČET GAMŮ V ZÁPASU (Total)
    avg_games = (s1['avg_games_won'] + s1['avg_games_lost'] + s2['avg_games_won'] + s2['avg_games_lost']) / 2
    markets.append({"market": "Počet gamů v zápasu", "selection": f"Over {int(avg_games)}", "prob": 0.55})
    
    # 9. KANÁR (6-0)
    bagel_prob = (s1['bagel_rate'] + s2['bagel_rate']) / 2
    markets.append({"market": "Kanár v zápasu (6-0)", "selection": "ANO", "prob": bagel_prob})
    markets.append({"market": "Kanár v zápasu (6-0)", "selection": "NE", "prob": 1 - bagel_prob})
    
    # 10. HRÁČ VYHRAJE ALESPOŇ SET
    # Pokud je favorit, je to vysoké
    p1_set_prob = p1_win_prob + (1-p1_win_prob) * 0.4 # Šance na výhru + šance na prohru 1:2
    markets.append({"market": "Vyhraje alespoň set", "selection": p1_name, "prob": min(p1_set_prob, 0.95)})
    
    # 11. 1. SET / ZÁPAS (Double Result)
    # P1/P1
    markets.append({"market": "1. Set / Zápas", "selection": f"{p1_name} / {p1_name}", "prob": p1_win_prob * p1_fs_prob})
    
    # 12. PŘESNÝ POČET SETŮ
    prob_3_sets = 0.3 + (0.4 if abs(p1_win_prob - 0.5) < 0.1 else 0) # Pokud je to vyrovnané, roste šance na 3 sety
    markets.append({"market": "Přesný počet setů", "selection": "3", "prob": prob_3_sets})
    markets.append({"market": "Přesný počet setů", "selection": "2", "prob": 1 - prob_3_sets})

    return markets

# ==============================================================================
# 4. SCRAPER (TENNIS EXPLORER) - DYNAMICKÉ DATUM
# ==============================================================================
@st.cache_data(ttl=1800)
def scrape_tennis_explorer(date_obj):
    # Dynamická URL podle data
    year = date_obj.year
    month = date_obj.month
    day = date_obj.day
    
    # TennisExplorer formát: year=2026&month=02&day=22
    url = f"https://www.tennisexplorer.com/matches/?type=atp-single&year={year}&month={month}&day={day}"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        r = requests.get(url, headers=headers)
        dfs = pd.read_html(r.text)
        
        # Hledáme největší tabulku
        main_df = max(dfs, key=len)
        return main_df
    except:
        return None

def clean_name(name):
    name = re.sub(r'\(\d+\)', '', str(name)).strip()
    return name

def parse_matches(df):
    matches = []
    current_tour = "Unknown"
    
    # Iterace (zjednodušená logika pro TennisExplorer)
    # Hledáme řádky s časem a jmény
    pending_p1 = None
    pending_time = None
    
    df = df.astype(str)
    
    for idx, row in df.iterrows():
        col0 = str(row[0])
        col1 = str(row[1])
        
        if "H2H" in str(row.values):
            current_tour = col0 if len(col0) > 2 else col1
            pending_p1 = None
            continue
            
        # Detekce času (např. 14:30)
        if ":" in col0 and len(col0) < 6:
            pending_time = col0
            pending_p1 = clean_name(col1)
        elif pending_p1:
            # Druhý řádek zápasu
            p2 = clean_name(col1)
            matches.append({
                "time": pending_time,
                "tour": current_tour,
                "p1": pending_p1,
                "p2": p2
            })
            pending_p1 = None
            
    return matches

def find_in_db(name):
    if not name or not db_players: return None
    # Zkusíme přímou shodu nebo otočení jména (Alcaraz C. -> C. Alcaraz)
    parts = name.split()
    candidates = [name]
    if len(parts) > 1: candidates.append(f"{parts[-1]} {parts[0]}")
    
    best_match = process.extractOne(name, db_players)
    if best_match and best_match[1] > 85: return best_match[0]
    
    # Zkusíme otočené
    if len(parts) > 1:
        best_match_rev = process.extractOne(f"{parts[-1]} {parts[0]}", db_players)
        if best_match_rev and best_match_rev[1] > 85: return best_match_rev[0]
        
    return None

# ==============================================================================
# 5. UI APLIKACE
# ==============================================================================

# Výběr data
col_d, col_b = st.columns([3, 1])
selected_date = col_d.date_input("Vyber datum zápasů:", datetime.now(), min_value=datetime.now(), max_value=datetime.now() + timedelta(days=7))

if col_b.button("📡 Stáhnout program a analyzovat", type="primary"):
    
    with st.spinner(f"Stahuji program pro {selected_date.strftime('%d.%m.%Y')}..."):
        raw_df = scrape_tennis_explorer(selected_date)
        
        if raw_df is None:
            st.error("Nepodařilo se stáhnout data z TennisExplorer. Web může být nedostupný.")
        else:
            matches = parse_matches(raw_df)
            
            if not matches:
                st.warning("Nenašel jsem žádné zápasy. Zkontroluj datum nebo strukturu webu.")
                st.dataframe(raw_df.head())
            else:
                st.success(f"Nalezeno {len(matches)} zápasů. Počítám predikce pro 18 trhů...")
                
                # Analýza
                analyzed_matches = []
                
                progress = st.progress(0)
                for i, m in enumerate(matches):
                    p1_db = find_in_db(m['p1'])
                    p2_db = find_in_db(m['p2'])
                    
                    # Určení povrchu
                    surface = "Hard"
                    t_low = m['tour'].lower()
                    if "clay" in t_low or "rio" in t_low: surface = "Clay"
                    if "grass" in t_low: surface = "Grass"
                    
                    if p1_db and p2_db:
                        markets = generate_all_markets(p1_db, p2_db, surface)
                        if markets:
                            analyzed_matches.append({
                                "info": m,
                                "p1_db": p1_db,
                                "p2_db": p2_db,
                                "surface": surface,
                                "markets": markets
                            })
                    progress.progress((i+1)/len(matches))
                
                # --- VYKRESLENÍ VÝSLEDKŮ ---
                
                # 1. TOP TIPY (>60%)
                st.subheader("🔥 TOP TIPY DNE (Min. důvěra 60%)")
                
                top_tips_found = False
                for am in analyzed_matches:
                    # Najdeme nejlepší tipy v tomto zápase
                    best_market = max(am['markets'], key=lambda x: x['prob'])
                    
                    if best_market['prob'] >= 0.60:
                        top_tips_found = True
                        with st.container():
                            st.markdown(f"""
                            <div class="tip-card">
                                <div style="font-size: 0.8em; color: #555;">{am['info']['time']} | {am['info']['tour']} ({am['surface']})</div>
                                <div style="font-size: 1.1em; font-weight: bold;">{am['p1_db']} vs {am['p2_db']}</div>
                                <hr style="margin: 5px 0;">
                                <div style="font-size: 1.2em;">🎯 {best_market['market']}: <strong>{best_market['selection']}</strong></div>
                                <div>Důvěra: <strong>{int(best_market['prob']*100)}%</strong> | Fair Kurz: <strong>{round(1/best_market['prob'], 2)}</strong></div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                if not top_tips_found:
                    st.info("Dnes žádné vysoce pravděpodobné tipy (>60%).")
                
                st.divider()
                
                # 2. VŠECHNY ZÁPASY (Detailní rozpis)
                st.subheader("📋 Kompletní analýza zápasů")
                
                for am in analyzed_matches:
                    with st.expander(f"🎾 {am['info']['time']} | {am['p1_db']} vs {am['p2_db']}"):
                        c1, c2 = st.columns(2)
                        
                        # Rozdělení trhů do dvou sloupců
                        half = len(am['markets']) // 2
                        left_markets = am['markets'][:half]
                        right_markets = am['markets'][half:]
                        
                        with c1:
                            for m in left_markets:
                                color_class = "high-conf" if m['prob'] > 0.6 else ""
                                st.markdown(f"""
                                <div class="market-box">
                                    <div>{m['market']}</div>
                                    <div class="{color_class}">{m['selection']} ({int(m['prob']*100)}%)</div>
                                    <div style="font-size: 0.8em; color: #777;">Kurz: {round(1/m['prob'], 2)}</div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                        with c2:
                            for m in right_markets:
                                color_class = "high-conf" if m['prob'] > 0.6 else ""
                                st.markdown(f"""
                                <div class="market-box">
                                    <div>{m['market']}</div>
                                    <div class="{color_class}">{m['selection']} ({int(m['prob']*100)}%)</div>
                                    <div style="font-size: 0.8em; color: #777;">Kurz: {round(1/m['prob'], 2)}</div>
                                </div>
                                """, unsafe_allow_html=True)

# Manuální sekce (pokud scraper selže)
st.divider()
with st.expander("🔍 Manuální výběr hráčů (pokud zápas chybí)"):
    c1, c2, c3 = st.columns(3)
    mp1 = c1.selectbox("Hráč 1", db_players, key="m1")
    mp2 = c2.selectbox("Hráč 2", db_players, key="m2")
    msurf = c3.selectbox("Povrch", ["Hard", "Clay", "Grass"], key="ms")
    
    if st.button("Analyzovat manuálně"):
        markets = generate_all_markets(mp1, mp2, msurf)
        if markets:
            st.write("Výsledky analýzy:")
            st.dataframe(pd.DataFrame(markets).style.format({"prob": "{:.0%}"}))
