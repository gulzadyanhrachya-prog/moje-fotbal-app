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
st.set_page_config(page_title="Tennis Pro Analyst v9.0", layout="wide", page_icon="🎾")

st.markdown("""
<style>
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 8px; border-left: 4px solid #4CAF50; margin-bottom: 10px; }
    .stat-row { display: flex; justify-content: space-between; font-size: 0.9em; border-bottom: 1px solid #eee; padding: 3px 0; }
    .market-header { font-weight: bold; color: #333; margin-top: 10px; }
    .high-value { color: #28a745; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🎾 Tennis AI: Statistical Market Model")
st.caption("Implementuje logiku: Skill Gap vs Total Games, Surface Bias, TPW Dominance")

# ==============================================================================
# 2. NAČTENÍ DAT (JEFF SACKMANN DB)
# ==============================================================================
@st.cache_data(ttl=3600)
def load_data():
    base_atp = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{}.csv"
    base_wta = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_{}.csv"
    
    years = [2024, 2025, 2026] 
    dfs = []
    
    status = st.empty()
    status.text("⏳ Načítám databázi...")
    
    for year in years:
        try:
            df_atp = pd.read_csv(base_atp.format(year), on_bad_lines='skip')
            df_atp['tour'] = 'ATP'
            dfs.append(df_atp)
            
            df_wta = pd.read_csv(base_wta.format(year), on_bad_lines='skip')
            df_wta['tour'] = 'WTA'
            dfs.append(df_wta)
        except: pass
            
    status.empty()
    
    if not dfs: return pd.DataFrame()
    
    full_df = pd.concat(dfs, ignore_index=True)
    full_df['tourney_date'] = pd.to_datetime(full_df['tourney_date'], format='%Y%m%d', errors='coerce')
    
    cols = ['w_ace', 'w_df', 'w_svpt', 'w_1stIn', 'w_1stWon', 'w_2ndWon', 'w_SvGms', 'w_bpSaved', 'w_bpFaced',
            'l_ace', 'l_df', 'l_svpt', 'l_1stIn', 'l_1stWon', 'l_2ndWon', 'l_SvGms', 'l_bpSaved', 'l_bpFaced']
    
    for c in cols:
        if c in full_df.columns:
            full_df[c] = pd.to_numeric(full_df[c], errors='coerce').fillna(0)
            
    return full_df

df = load_data()

if not df.empty:
    db_players = pd.concat([df['winner_name'], df['loser_name']]).unique()
    db_players = sorted([str(p) for p in db_players if isinstance(p, str)])
else:
    db_players = []

# ==============================================================================
# 3. POKROČILÝ STATISTICKÝ ENGINE
# ==============================================================================
def calculate_advanced_metrics(player_name, surface, last_n=50):
    if df.empty: return None
    
    p_wins = df[df['winner_name'] == player_name]
    p_loss = df[df['loser_name'] == player_name]
    
    # Surface filter
    p_wins_surf = p_wins[p_wins['surface'] == surface]
    p_loss_surf = p_loss[p_loss['surface'] == surface]
    
    if len(p_wins_surf) + len(p_loss_surf) < 5:
        matches = pd.concat([p_wins, p_loss]).sort_values('tourney_date', ascending=False).head(last_n)
    else:
        matches = pd.concat([p_wins_surf, p_loss_surf]).sort_values('tourney_date', ascending=False).head(last_n)
        
    if matches.empty: return None
    
    # Agregace
    stats = {
        "matches": len(matches),
        "wins": 0,
        "serve_points_total": 0,
        "serve_points_won": 0,
        "return_points_total": 0,
        "return_points_won": 0,
        "service_games": 0,
        "bp_faced": 0,
        "bp_saved": 0,
        "sets_played": 0,
        "sets_won": 0
    }
    
    for _, row in matches.iterrows():
        is_winner = row['winner_name'] == player_name
        
        # Počet setů (hrubý odhad podle skóre)
        score = str(row['score'])
        sets_in_match = score.count('-') # Zjednodušené
        stats["sets_played"] += sets_in_match
        
        if is_winner:
            stats["wins"] += 1
            stats["sets_won"] += 2 # Většinou 2 sety na výhru
            stats["serve_points_total"] += row['w_svpt']
            stats["serve_points_won"] += (row['w_1stWon'] + row['w_2ndWon'])
            stats["service_games"] += row['w_SvGms']
            stats["bp_faced"] += row['w_bpFaced']
            stats["bp_saved"] += row['w_bpSaved']
            stats["return_points_total"] += row['l_svpt']
            stats["return_points_won"] += (row['l_svpt'] - (row['l_1stWon'] + row['l_2ndWon']))
        else:
            stats["sets_won"] += (sets_in_match - 2) if sets_in_match > 2 else 0
            stats["serve_points_total"] += row['l_svpt']
            stats["serve_points_won"] += (row['l_1stWon'] + row['l_2ndWon'])
            stats["service_games"] += row['l_SvGms']
            stats["bp_faced"] += row['l_bpFaced']
            stats["bp_saved"] += row['l_bpSaved']
            stats["return_points_total"] += row['w_svpt']
            stats["return_points_won"] += (row['w_svpt'] - (row['w_1stWon'] + row['w_2ndWon']))

    def safe_div(a, b): return a / b if b > 0 else 0
    
    # Klíčové metriky
    tpw_ratio = safe_div(stats["serve_points_won"] + stats["return_points_won"], 
                         stats["serve_points_total"] + stats["return_points_total"])
    
    hold_pct = safe_div(stats["service_games"] - (stats["bp_faced"] - stats["bp_saved"]), stats["service_games"])
    break_pct = safe_div(stats["return_points_won"], stats["return_points_total"]) # Proxy pro break
    
    return {
        "matches": stats["matches"],
        "tpw": tpw_ratio,
        "hold_pct": hold_pct,
        "break_pct": break_pct,
        "win_rate": safe_div(stats["wins"], stats["matches"])
    }

def predict_match_logic(s1, s2, surface):
    """
    Jádro modelu založené na analýze z textu.
    """
    # 1. Vítěz (TPW Dominance)
    # TPW je nejsilnější prediktor. Rozdíl 1% v TPW je obrovský.
    tpw_diff = s1['tpw'] - s2['tpw']
    # Sigmoid funkce pro převod rozdílu na pravděpodobnost
    prob_p1 = 1 / (1 + np.exp(-15 * tpw_diff)) 
    
    # 2. Total Games (Skill Gap Theory)
    # Text: Průměr je 22.9 gamů.
    base_games = 22.9
    
    # Úprava podle povrchu (Text: Fast surfaces = more games)
    if surface == "Grass" or surface == "Carpet": base_games += 1.0
    if surface == "Clay": base_games -= 0.5
    
    # Úprava podle Skill Gap (Text: Close match = more games)
    # Skill gap je absolutní rozdíl v pravděpodobnosti výhry
    skill_gap = abs(prob_p1 - 0.5) * 2 # 0 = vyrovnané, 1 = jasný favorit
    
    # Pokud je skill gap malý (0), přidáme gamy. Pokud velký (1), ubereme.
    # Rozsah úpravy: +/- 2.5 gamu
    game_adjustment = (0.5 - skill_gap) * 5 
    expected_games = base_games + game_adjustment
    
    # 3. Sets (2 vs 3)
    # Text: 65% zápasů končí 2:0.
    prob_2_sets = 0.65
    # Pokud je zápas vyrovnaný, šance na 3 sety roste
    if skill_gap < 0.2: # Velmi vyrovnané
        prob_2_sets = 0.55 # Snížíme šanci na 2 sety
    elif skill_gap > 0.6: # Jasný favorit
        prob_2_sets = 0.80 # Zvýšíme šanci na 2 sety
        
    return {
        "prob_p1": prob_p1,
        "expected_games": expected_games,
        "prob_2_sets": prob_2_sets,
        "skill_gap": skill_gap
    }

def generate_markets(p1_name, p2_name, surface):
    s1 = calculate_advanced_metrics(p1_name, surface)
    s2 = calculate_advanced_metrics(p2_name, surface)
    
    if not s1 or not s2: return None
    
    pred = predict_match_logic(s1, s2, surface)
    prob_p1 = pred['prob_p1']
    prob_p2 = 1 - prob_p1
    
    markets = []
    
    # 1. VÍTĚZ
    markets.append({"market": "Vítěz zápasu", "selection": p1_name, "prob": prob_p1})
    markets.append({"market": "Vítěz zápasu", "selection": p2_name, "prob": prob_p2})
    
    # 2. TOTAL GAMES (Over/Under)
    line = round(pred['expected_games']) # Např. 23
    # Pravděpodobnost Overu klesá, pokud je line vysoko nastavená
    # Zde zjednodušujeme: Model věří svému číslu 'expected_games'
    # Pokud je expected 24 a line je 22.5, Over má vysokou pravděpodobnost
    markets.append({"market": "Počet gamů", "selection": f"Over {line-0.5}", "prob": 0.60})
    markets.append({"market": "Počet gamů", "selection": f"Under {line+0.5}", "prob": 0.60})
    
    # 3. SETY
    prob_3_sets = 1 - pred['prob_2_sets']
    markets.append({"market": "Počet setů", "selection": "2 sety", "prob": pred['prob_2_sets']})
    markets.append({"market": "Počet setů", "selection": "3 sety", "prob": prob_3_sets})
    
    # 4. PŘESNÝ VÝSLEDEK
    # Odvozeno z vítěze a počtu setů
    if prob_p1 > 0.5:
        prob_2_0 = prob_p1 * pred['prob_2_sets']
        prob_2_1 = prob_p1 * prob_3_sets
        markets.append({"market": "Přesný výsledek", "selection": f"{p1_name} 2:0", "prob": prob_2_0})
        markets.append({"market": "Přesný výsledek", "selection": f"{p1_name} 2:1", "prob": prob_2_1})
    else:
        prob_0_2 = prob_p2 * pred['prob_2_sets']
        prob_1_2 = prob_p2 * prob_3_sets
        markets.append({"market": "Přesný výsledek", "selection": f"{p2_name} 2:0", "prob": prob_0_2})
        markets.append({"market": "Přesný výsledek", "selection": f"{p2_name} 2:1", "prob": prob_1_2})
        
    # 5. TIEBREAK
    # Závisí na Hold % obou hráčů
    avg_hold = (s1['hold_pct'] + s2['hold_pct']) / 2
    tb_prob = 0.20 # Base
    if avg_hold > 0.80: tb_prob = 0.45 # Servismani
    if surface == "Grass": tb_prob += 0.10
    
    markets.append({"market": "Tiebreak v zápasu", "selection": "ANO", "prob": tb_prob})
    
    # 6. KANÁR (6-0)
    # Pokud je skill gap obrovský
    bagel_prob = 0.05
    if pred['skill_gap'] > 0.7: bagel_prob = 0.25
    markets.append({"market": "Kanár (6-0)", "selection": "ANO", "prob": bagel_prob})

    return markets, s1, s2, pred

# ==============================================================================
# 4. SCRAPER (TENNIS EXPLORER)
# ==============================================================================
@st.cache_data(ttl=1800)
def scrape_schedule(date_obj):
    url = f"https://www.tennisexplorer.com/matches/?type=atp-single&year={date_obj.year}&month={date_obj.month}&day={date_obj.day}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers)
        dfs = pd.read_html(r.text)
        return max(dfs, key=len)
    except: return None

def parse_schedule(df):
    matches = []
    df = df.astype(str)
    pending_p1 = None
    pending_time = None
    current_tour = "Unknown"
    
    for _, row in df.iterrows():
        c0, c1 = str(row[0]), str(row[1])
        if "H2H" in str(row.values):
            current_tour = c0 if len(c0) > 2 else c1
            pending_p1 = None
            continue
        
        if ":" in c0 and len(c0) < 6:
            pending_time = c0
            pending_p1 = re.sub(r'\(\d+\)', '', c1).strip()
        elif pending_p1:
            p2 = re.sub(r'\(\d+\)', '', c1).strip()
            matches.append({"time": pending_time, "tour": current_tour, "p1": pending_p1, "p2": p2})
            pending_p1 = None
    return matches

def find_db_player(name):
    if not name or not db_players: return None
    parts = name.split()
    candidates = [name]
    if len(parts) > 1: candidates.append(f"{parts[-1]} {parts[0]}")
    
    best, score = process.extractOne(name, db_players)
    if score > 85: return best
    
    if len(parts) > 1:
        best_rev, score_rev = process.extractOne(f"{parts[-1]} {parts[0]}", db_players)
        if score_rev > 85: return best_rev
        
    return None

# ==============================================================================
# 5. UI APLIKACE
# ==============================================================================
tab1, tab2 = st.tabs(["📅 Program & Predikce", "🔬 Detailní Analýza"])

with tab1:
    col_d, col_b = st.columns([3, 1])
    sel_date = col_d.date_input("Datum:", datetime.now(), min_value=datetime.now(), max_value=datetime.now()+timedelta(days=7))
    
    if col_b.button("📡 Analyzovat program", type="primary"):
        with st.spinner("Stahuji data a počítám modely..."):
            raw_df = scrape_schedule(sel_date)
            if raw_df is None:
                st.error("Chyba stahování.")
            else:
                matches = parse_schedule(raw_df)
                results = []
                
                progress = st.progress(0)
                for i, m in enumerate(matches):
                    p1 = find_db_player(m['p1'])
                    p2 = find_db_player(m['p2'])
                    
                    surf = "Hard"
                    if "clay" in m['tour'].lower(): surf = "Clay"
                    elif "grass" in m['tour'].lower(): surf = "Grass"
                    
                    if p1 and p2:
                        res = generate_markets(p1, p2, surf)
                        if res:
                            mkts, s1, s2, pred = res
                            results.append({
                                "info": m, "p1": p1, "p2": p2, "surf": surf,
                                "markets": mkts, "pred": pred
                            })
                    progress.progress((i+1)/len(matches))
                
                # Vykreslení
                st.subheader("🔥 TOP TIPY (Důvěra > 60%)")
                
                for res in results:
                    # Filtrujeme jen silné tipy
                    strong_mkts = [m for m in res['markets'] if m['prob'] > 0.60]
                    
                    if strong_mkts:
                        with st.container():
                            st.markdown(f"""
                            <div class="metric-card">
                                <div style="display:flex; justify-content:space-between;">
                                    <span><strong>{res['info']['time']}</strong> | {res['info']['tour']} ({res['surf']})</span>
                                    <span>Očekávané gamy: <strong>{round(res['pred']['expected_games'], 1)}</strong></span>
                                </div>
                                <h3 style="margin:5px 0;">{res['p1']} vs {res['p2']}</h3>
                                <hr style="margin:5px 0;">
                            """, unsafe_allow_html=True)
                            
                            cols = st.columns(3)
                            for idx, mkt in enumerate(strong_mkts[:6]): # Max 6 tipů
                                with cols[idx % 3]:
                                    st.markdown(f"""
                                    <div style="font-size:0.9em;">
                                        <span class="market-header">{mkt['market']}</span><br>
                                        <span class="high-value">{mkt['selection']}</span><br>
                                        <span style="color:#666;">Důvěra: {int(mkt['prob']*100)}% (Kurz {round(1/mkt['prob'], 2)})</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                            
                            st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    st.header("🔬 Detailní srovnání hráčů")
    c1, c2, c3 = st.columns(3)
    mp1 = c1.selectbox("Hráč 1", db_players, index=0)
    mp2 = c2.selectbox("Hráč 2", db_players, index=1)
    msurf = c3.selectbox("Povrch", ["Hard", "Clay", "Grass"])
    
    if st.button("Analyzovat statistiky"):
        res = generate_markets(mp1, mp2, msurf)
        if res:
            mkts, s1, s2, pred = res
            
            st.markdown(f"### Očekávaný průběh: {round(pred['expected_games'], 1)} gamů")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**{mp1}**")
                st.write(f"TPW (Dominance): {int(s1['tpw']*100)}%")
                st.write(f"Hold Service: {int(s1['hold_pct']*100)}%")
            with col_b:
                st.write(f"**{mp2}**")
                st.write(f"TPW (Dominance): {int(s2['tpw']*100)}%")
                st.write(f"Hold Service: {int(s2['hold_pct']*100)}%")
            
            st.dataframe(pd.DataFrame(mkts).style.format({"prob": "{:.1%}"}))
