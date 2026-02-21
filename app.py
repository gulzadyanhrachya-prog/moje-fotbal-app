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
st.set_page_config(page_title="Tennis Pro Analyst v8.0", layout="wide", page_icon="🎾")

st.markdown("""
<style>
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 8px; border-left: 4px solid #4CAF50; margin-bottom: 10px; }
    .risk-card { background-color: #fff0f0; padding: 15px; border-radius: 8px; border-left: 4px solid #ff4b4b; margin-bottom: 10px; }
    .stat-row { display: flex; justify-content: space-between; font-size: 0.9em; border-bottom: 1px solid #eee; padding: 3px 0; }
    .big-stat { font-size: 1.2em; font-weight: bold; color: #333; }
    .winner-green { color: #28a745; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🎾 Tennis AI: Advanced Statistical Model")
st.caption("Metrics: Service Efficiency, Return Pressure, Break Points, TPW Dominance")

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
    status.text("⏳ Načítám detailní statistiky (Servis, Return, BP)...")
    
    for year in years:
        try:
            # Načtení s ošetřením chybějících sloupců
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
    
    # Konverze numerických sloupců (klíčové pro statistiky)
    cols = ['w_ace', 'w_df', 'w_svpt', 'w_1stIn', 'w_1stWon', 'w_2ndWon', 'w_SvGms', 'w_bpSaved', 'w_bpFaced',
            'l_ace', 'l_df', 'l_svpt', 'l_1stIn', 'l_1stWon', 'l_2ndWon', 'l_SvGms', 'l_bpSaved', 'l_bpFaced']
    
    for c in cols:
        if c in full_df.columns:
            full_df[c] = pd.to_numeric(full_df[c], errors='coerce').fillna(0)
            
    return full_df

df = load_data()

# Index hráčů
if not df.empty:
    db_players = pd.concat([df['winner_name'], df['loser_name']]).unique()
    db_players = sorted([str(p) for p in db_players if isinstance(p, str)])
else:
    db_players = []

# ==============================================================================
# 3. POKROČILÝ STATISTICKÝ ENGINE (THE BRAIN)
# ==============================================================================
def calculate_advanced_metrics(player_name, surface, last_n=30):
    """
    Vypočítá pokročilé metriky (Serve Efficiency, Return Pressure, TPW)
    pro posledních N zápasů na daném povrchu.
    """
    if df.empty: return None
    
    # 1. Filtrace zápasů hráče
    p_wins = df[df['winner_name'] == player_name]
    p_loss = df[df['loser_name'] == player_name]
    
    # 2. Filtrace povrchu (pokud je dost dat, jinak bereme vše)
    p_wins_surf = p_wins[p_wins['surface'] == surface]
    p_loss_surf = p_loss[p_loss['surface'] == surface]
    
    if len(p_wins_surf) + len(p_loss_surf) < 5:
        # Fallback: Všechny povrchy, pokud na tomto málo hrál
        matches = pd.concat([p_wins, p_loss]).sort_values('tourney_date', ascending=False).head(last_n)
    else:
        matches = pd.concat([p_wins_surf, p_loss_surf]).sort_values('tourney_date', ascending=False).head(last_n)
        
    if matches.empty: return None
    
    # 3. Agregace statistik
    stats = {
        "matches": len(matches),
        "wins": 0,
        "losses": 0,
        # Serve Stats
        "serve_points_total": 0,
        "serve_points_won": 0,
        "first_serve_in_count": 0,
        "first_serve_won_count": 0,
        "second_serve_won_count": 0,
        "service_games": 0,
        "bp_faced": 0,
        "bp_saved": 0,
        # Return Stats
        "return_points_total": 0,
        "return_points_won": 0,
        "return_games": 0,
        "bp_opportunities": 0,
        "bp_converted": 0
    }
    
    for _, row in matches.iterrows():
        is_winner = row['winner_name'] == player_name
        
        if is_winner:
            stats["wins"] += 1
            # Serve (Winner stats)
            stats["serve_points_total"] += row['w_svpt']
            stats["serve_points_won"] += (row['w_1stWon'] + row['w_2ndWon'])
            stats["first_serve_in_count"] += row['w_1stIn']
            stats["first_serve_won_count"] += row['w_1stWon']
            stats["second_serve_won_count"] += row['w_2ndWon']
            stats["service_games"] += row['w_SvGms']
            stats["bp_faced"] += row['w_bpFaced']
            stats["bp_saved"] += row['w_bpSaved']
            # Return (Opponent stats inverted)
            stats["return_points_total"] += row['l_svpt']
            stats["return_points_won"] += (row['l_svpt'] - (row['l_1stWon'] + row['l_2ndWon']))
            stats["return_games"] += row['l_SvGms']
            stats["bp_opportunities"] += row['l_bpFaced']
            stats["bp_converted"] += (row['l_bpFaced'] - row['l_bpSaved'])
        else:
            stats["losses"] += 1
            # Serve (Loser stats)
            stats["serve_points_total"] += row['l_svpt']
            stats["serve_points_won"] += (row['l_1stWon'] + row['l_2ndWon'])
            stats["first_serve_in_count"] += row['l_1stIn']
            stats["first_serve_won_count"] += row['l_1stWon']
            stats["second_serve_won_count"] += row['l_2ndWon']
            stats["service_games"] += row['l_SvGms']
            stats["bp_faced"] += row['l_bpFaced']
            stats["bp_saved"] += row['l_bpSaved']
            # Return (Opponent stats inverted)
            stats["return_points_total"] += row['w_svpt']
            stats["return_points_won"] += (row['w_svpt'] - (row['w_1stWon'] + row['w_2ndWon']))
            stats["return_games"] += row['w_SvGms']
            stats["bp_opportunities"] += row['w_bpFaced']
            stats["bp_converted"] += (row['w_bpFaced'] - row['w_bpSaved'])

    # 4. Výpočet procent (Metrics)
    def safe_div(a, b): return a / b if b > 0 else 0
    
    # Serve Metrics
    first_serve_pct = safe_div(stats["first_serve_in_count"], stats["serve_points_total"])
    first_serve_won_pct = safe_div(stats["first_serve_won_count"], stats["first_serve_in_count"])
    second_serve_won_pct = safe_div(stats["second_serve_won_count"], (stats["serve_points_total"] - stats["first_serve_in_count"]))
    bp_saved_pct = safe_div(stats["bp_saved"], stats["bp_faced"])
    hold_pct = safe_div(stats["service_games"] - (stats["bp_faced"] - stats["bp_saved"]), stats["service_games"]) # Approx
    
    # Return Metrics
    return_points_won_pct = safe_div(stats["return_points_won"], stats["return_points_total"])
    bp_converted_pct = safe_div(stats["bp_converted"], stats["bp_opportunities"])
    break_pct = safe_div(stats["bp_converted"], stats["return_games"]) # Approx
    
    # Total Points Won (TPW) - The Holy Grail
    total_points_played = stats["serve_points_total"] + stats["return_points_total"]
    total_points_won = stats["serve_points_won"] + stats["return_points_won"]
    tpw_ratio = safe_div(total_points_won, total_points_played)
    
    return {
        "matches": stats["matches"],
        "win_rate": safe_div(stats["wins"], stats["matches"]),
        "tpw": tpw_ratio, # Total Points Won %
        "serve_rating": (first_serve_won_pct * 0.4) + (second_serve_won_pct * 0.3) + (hold_pct * 0.3),
        "return_rating": (return_points_won_pct * 0.6) + (break_pct * 0.4),
        "stats": {
            "1st_srv_in": first_serve_pct,
            "1st_srv_won": first_serve_won_pct,
            "2nd_srv_won": second_serve_won_pct,
            "bp_saved": bp_saved_pct,
            "rtn_pts_won": return_points_won_pct,
            "bp_conv": bp_converted_pct
        }
    }

def predict_winner_advanced(p1_stats, p2_stats):
    """
    Vytvoří predikci na základě porovnání Serve vs Return a TPW Dominance.
    """
    # 1. TPW Dominance (Nejsilnější indikátor)
    # Hráč s TPW > 52% je obvykle jasný favorit.
    tpw_diff = p1_stats['tpw'] - p2_stats['tpw']
    
    # 2. Serve vs Return Matchup
    # Jak dobře P1 servíruje vs Jak dobře P2 returnuje
    p1_serve_adv = p1_stats['serve_rating'] - p2_stats['return_rating']
    p2_serve_adv = p2_stats['serve_rating'] - p1_stats['return_rating']
    
    matchup_diff = p1_serve_adv - p2_serve_adv
    
    # 3. Finální skóre (Vážený průměr)
    # TPW má váhu 60%, Matchup 40%
    final_score = (tpw_diff * 0.6) + (matchup_diff * 0.4)
    
    # Převod skóre na pravděpodobnost (Sigmoid funkce)
    # K faktor určuje strmost křivky
    k = 10 
    prob_p1 = 1 / (1 + np.exp(-k * final_score))
    
    return prob_p1

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
    # Zkusíme otočit jméno (Alcaraz C. -> C. Alcaraz)
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

# --- TAB 1: PROGRAM ---
with tab1:
    col_d, col_b = st.columns([3, 1])
    sel_date = col_d.date_input("Datum:", datetime.now(), min_value=datetime.now(), max_value=datetime.now()+timedelta(days=7))
    
    if col_b.button("📡 Analyzovat program", type="primary"):
        with st.spinner("Stahuji data a počítám TPW metriky..."):
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
                    
                    # Povrch
                    surf = "Hard"
                    if "clay" in m['tour'].lower(): surf = "Clay"
                    elif "grass" in m['tour'].lower(): surf = "Grass"
                    
                    if p1 and p2:
                        s1 = calculate_advanced_metrics(p1, surf)
                        s2 = calculate_advanced_metrics(p2, surf)
                        
                        if s1 and s2:
                            prob = predict_winner_advanced(s1, s2)
                            results.append({
                                "info": m, "p1": p1, "p2": p2, "prob": prob, 
                                "s1": s1, "s2": s2, "surf": surf
                            })
                    progress.progress((i+1)/len(matches))
                
                # Vykreslení
                results.sort(key=lambda x: abs(x['prob'] - 0.5), reverse=True)
                
                st.subheader("🔥 Nejlepší sázkové příležitosti")
                
                for res in results:
                    prob = res['prob']
                    winner = res['p1'] if prob > 0.5 else res['p2']
                    win_prob = prob if prob > 0.5 else 1-prob
                    
                    # Filtr: Ukazujeme vše nad 55% (méně přísné, ale s daty)
                    if win_prob > 0.55:
                        with st.container():
                            st.markdown(f"""
                            <div class="metric-card">
                                <div style="display:flex; justify-content:space-between;">
                                    <span><strong>{res['info']['time']}</strong> | {res['info']['tour']} ({res['surf']})</span>
                                    <span style="color:#555;">Férový kurz: <strong>{round(1/win_prob, 2)}</strong></span>
                                </div>
                                <h3 style="margin:5px 0;">{res['p1']} vs {res['p2']}</h3>
                                <div class="stat-row">
                                    <span>🏆 <strong>Tip: {winner}</strong></span>
                                    <span>Důvěra modelu: <strong>{int(win_prob*100)}%</strong></span>
                                </div>
                                <hr style="margin:5px 0;">
                                <div style="display:flex; justify-content:space-between; font-size:0.85em; color:#444;">
                                    <div>
                                        <div>TPW (Dominance): <strong>{int(res['s1']['tpw']*100)}%</strong> vs {int(res['s2']['tpw']*100)}%</div>
                                        <div>1st Serve Won: {int(res['s1']['stats']['1st_srv_won']*100)}% vs {int(res['s2']['stats']['1st_srv_won']*100)}%</div>
                                    </div>
                                    <div style="text-align:right;">
                                        <div>Return Pts Won: {int(res['s1']['stats']['rtn_pts_won']*100)}% vs {int(res['s2']['stats']['rtn_pts_won']*100)}%</div>
                                        <div>BP Saved: {int(res['s1']['stats']['bp_saved']*100)}% vs {int(res['s2']['stats']['bp_saved']*100)}%</div>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

# --- TAB 2: DETAILNÍ ANALÝZA ---
with tab2:
    st.header("🔬 Detailní srovnání hráčů")
    c1, c2, c3 = st.columns(3)
    mp1 = c1.selectbox("Hráč 1", db_players, index=0)
    mp2 = c2.selectbox("Hráč 2", db_players, index=1)
    msurf = c3.selectbox("Povrch", ["Hard", "Clay", "Grass"])
    
    if st.button("Analyzovat statistiky"):
        s1 = calculate_advanced_metrics(mp1, msurf)
        s2 = calculate_advanced_metrics(mp2, msurf)
        
        if s1 and s2:
            prob = predict_winner_advanced(s1, s2)
            
            st.markdown(f"<h2 style='text-align:center;'>{int(prob*100)}% vs {int((1-prob)*100)}%</h2>", unsafe_allow_html=True)
            st.progress(prob)
            
            # Tabulka metrik
            metrics = [
                ("Total Points Won (Dominance)", s1['tpw'], s2['tpw'], True),
                ("Win Rate (Surface)", s1['win_rate'], s2['win_rate'], True),
                ("1st Serve Points Won", s1['stats']['1st_srv_won'], s2['stats']['1st_srv_won'], True),
                ("2nd Serve Points Won", s1['stats']['2nd_srv_won'], s2['stats']['2nd_srv_won'], True),
                ("Return Points Won", s1['stats']['rtn_pts_won'], s2['stats']['rtn_pts_won'], True),
                ("Break Points Converted", s1['stats']['bp_conv'], s2['stats']['bp_conv'], True),
                ("Break Points Saved", s1['stats']['bp_saved'], s2['stats']['bp_saved'], True),
            ]
            
            st.subheader("Klíčové metriky")
            for name, v1, v2, is_pct in metrics:
                val1 = f"{int(v1*100)}%" if is_pct else round(v1, 2)
                val2 = f"{int(v2*100)}%" if is_pct else round(v2, 2)
                
                color1 = "green" if v1 > v2 else "black"
                color2 = "green" if v2 > v1 else "black"
                weight1 = "bold" if v1 > v2 else "normal"
                weight2 = "bold" if v2 > v1 else "normal"
                
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; border-bottom:1px solid #eee; padding:5px;">
                    <span style="color:{color1}; font-weight:{weight1}; width:20%;">{val1}</span>
                    <span style="text-align:center; width:60%;">{name}</span>
                    <span style="color:{color2}; font-weight:{weight2}; width:20%; text-align:right;">{val2}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("Nedostatek dat pro jednoho z hráčů.")
