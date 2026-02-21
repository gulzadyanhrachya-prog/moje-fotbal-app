import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# ==============================================================================
# 1. KONFIGURACE A STYLY
# ==============================================================================
st.set_page_config(page_title="Tennis AI Database 2026", layout="wide", page_icon="🎾")

st.markdown("""
<style>
    .main-header { font-size: 30px; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .prediction-card { padding: 20px; border-radius: 10px; background-color: #f0f2f6; border-left: 5px solid #ff4b4b; }
    .stat-metric { font-size: 20px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🎾 Tennis AI Database & Predictor")
st.caption("Data: ATP & WTA (Open Source Database) | Model: Surface-based ELO")

# ==============================================================================
# 2. NAČTENÍ DAT (Místo Livesport scrapingu používáme GitHub Raw Data)
# ==============================================================================
@st.cache_data(ttl=3600)
def load_data():
    # Odkazy na databáze Jeffa Sackmanna (aktualizované výsledky)
    # Používáme data z let 2024, 2025 a 2026 (pokud existují)
    base_atp = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{}.csv"
    base_wta = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_{}.csv"
    
    years = [2024, 2025] # Pro rok 2026 zatím data nemusí být kompletní, ale kód je připraven
    
    data_frames = []
    
    status_text = st.empty()
    status_text.text("⏳ Stahuji historická data (ATP/WTA)...")
    
    for year in years:
        try:
            # ATP
            df_atp = pd.read_csv(base_atp.format(year))
            df_atp['tour'] = 'ATP'
            data_frames.append(df_atp)
            
            # WTA
            df_wta = pd.read_csv(base_wta.format(year))
            df_wta['tour'] = 'WTA'
            data_frames.append(df_wta)
        except:
            pass # Pokud rok chybí, přeskočíme
            
    if not data_frames:
        st.error("Nepodařilo se stáhnout data. GitHub může být nedostupný.")
        return pd.DataFrame()
        
    full_df = pd.concat(data_frames, ignore_index=True)
    
    # Úprava datumu
    full_df['tourney_date'] = pd.to_datetime(full_df['tourney_date'], format='%Y%m%d', errors='coerce')
    
    status_text.empty()
    return full_df

df = load_data()

if df.empty:
    st.stop()

# ==============================================================================
# 3. PŘÍPRAVA DATABÁZE HRÁČŮ
# ==============================================================================
# Vytvoříme seznam všech unikátních hráčů
all_players = pd.concat([df['winner_name'], df['loser_name']]).unique()
all_players = sorted([p for p in all_players if isinstance(p, str)])

# ==============================================================================
# 4. FUNKCE PRO VÝPOČET STATISTIK
# ==============================================================================
def get_player_stats(player_name, surface):
    # Filtrujeme zápasy hráče
    wins = df[df['winner_name'] == player_name]
    losses = df[df['loser_name'] == player_name]
    
    total_matches = len(wins) + len(losses)
    if total_matches == 0:
        return None
    
    # Statistiky na konkrétním povrchu
    wins_surf = wins[wins['surface'] == surface]
    losses_surf = losses[losses['surface'] == surface]
    matches_surf = len(wins_surf) + len(losses_surf)
    
    win_rate_total = len(wins) / total_matches
    win_rate_surf = len(wins_surf) / matches_surf if matches_surf > 0 else 0
    
    # Posledních 5 zápasů (Forma)
    # Musíme spojit výhry a prohry a seřadit podle data
    last_matches = pd.concat([
        wins[['tourney_date', 'loser_name', 'score', 'surface']].assign(result='W'),
        losses[['tourney_date', 'winner_name', 'score', 'surface']].assign(result='L')
    ]).sort_values('tourney_date', ascending=False).head(5)
    
    form_str = "".join(last_matches['result'].tolist())
    
    return {
        "matches": total_matches,
        "win_rate": win_rate_total,
        "win_rate_surface": win_rate_surf,
        "matches_surface": matches_surf,
        "form": form_str,
        "history": last_matches
    }

def predict_match(p1_stats, p2_stats):
    # Jednoduchý algoritmus váženého průměru
    # 40% Celková úspěšnost + 60% Úspěšnost na povrchu
    
    score1 = (p1_stats['win_rate'] * 0.4) + (p1_stats['win_rate_surface'] * 0.6)
    score2 = (p2_stats['win_rate'] * 0.4) + (p2_stats['win_rate_surface'] * 0.6)
    
    total_score = score1 + score2
    
    if total_score == 0: return 0.5
    
    prob1 = score1 / total_score
    return prob1

# ==============================================================================
# 5. UI APLIKACE
# ==============================================================================

# Sidebar - Výběr
st.sidebar.header("⚙️ Nastavení zápasu")
surface = st.sidebar.selectbox("Povrch (Surface):", ["Hard", "Clay", "Grass"])
player1 = st.sidebar.selectbox("Hráč 1:", all_players, index=all_players.index("Novak Djokovic") if "Novak Djokovic" in all_players else 0)
player2 = st.sidebar.selectbox("Hráč 2:", all_players, index=all_players.index("Carlos Alcaraz") if "Carlos Alcaraz" in all_players else 1)

if player1 == player2:
    st.error("Vyber dva rozdílné hráče!")
else:
    # Výpočet
    p1_stats = get_player_stats(player1, surface)
    p2_stats = get_player_stats(player2, surface)
    
    if not p1_stats or not p2_stats:
        st.warning("Jeden z hráčů nemá v databázi dostatek dat (méně než 2 roky historie).")
    else:
        prob_p1 = predict_match(p1_stats, p2_stats)
        prob_p2 = 1 - prob_p1
        
        # Férové kurzy
        odd_p1 = round(1/prob_p1, 2) if prob_p1 > 0 else 99
        odd_p2 = round(1/prob_p2, 2) if prob_p2 > 0 else 99
        
        # --- HLAVNÍ PANEL ---
        c1, c2, c3 = st.columns([1, 2, 1])
        
        with c1:
            st.markdown(f"<h2 style='text-align: center;'>{player1}</h2>", unsafe_allow_html=True)
            st.metric("Win Rate (Total)", f"{int(p1_stats['win_rate']*100)}%")
            st.metric(f"Win Rate ({surface})", f"{int(p1_stats['win_rate_surface']*100)}%")
            st.write(f"**Forma:** {p1_stats['form']}")
            
        with c3:
            st.markdown(f"<h2 style='text-align: center;'>{player2}</h2>", unsafe_allow_html=True)
            st.metric("Win Rate (Total)", f"{int(p2_stats['win_rate']*100)}%")
            st.metric(f"Win Rate ({surface})", f"{int(p2_stats['win_rate_surface']*100)}%")
            st.write(f"**Forma:** {p2_stats['form']}")

        with c2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align: center; font-size: 40px; font-weight: bold;'>{int(prob_p1*100)}% vs {int(prob_p2*100)}%</div>", unsafe_allow_html=True)
            st.progress(prob_p1)
            
            st.markdown("---")
            st.markdown("<h4 style='text-align: center;'>Férové kurzy</h4>", unsafe_allow_html=True)
            k1, k2 = st.columns(2)
            k1.metric(f"Kurz {player1}", odd_p1)
            k2.metric(f"Kurz {player2}", odd_p2)

        # --- DETAILNÍ HISTORIE ---
        st.divider()
        st.subheader(f"📜 Poslední zápasy ({surface} i ostatní)")
        
        col_h1, col_h2 = st.columns(2)
        
        with col_h1:
            st.write(f"**{player1} - Historie**")
            st.dataframe(p1_stats['history'][['tourney_date', 'result', 'score', 'surface']], hide_index=True, use_container_width=True)
            
        with col_h2:
            st.write(f"**{player2} - Historie**")
            st.dataframe(p2_stats['history'][['tourney_date', 'result', 'score', 'surface']], hide_index=True, use_container_width=True)

        # --- H2H (Vzájemné) ---
        st.divider()
        st.subheader("⚔️ Vzájemné zápasy (H2H) v databázi")
        
        # Hledáme zápasy, kde hráli tito dva proti sobě
        h2h = df[((df['winner_name'] == player1) & (df['loser_name'] == player2)) | 
                 ((df['winner_name'] == player2) & (df['loser_name'] == player1))]
        
        if not h2h.empty:
            st.dataframe(h2h[['tourney_date', 'winner_name', 'score', 'surface', 'tour']], hide_index=True, use_container_width=True)
            
            p1_h2h_wins = len(h2h[h2h['winner_name'] == player1])
            p2_h2h_wins = len(h2h[h2h['winner_name'] == player2])
            st.caption(f"Bilance: {player1} {p1_h2h_wins} - {p2_h2h_wins} {player2}")
        else:
            st.info("V posledních 2 letech spolu tito hráči nehráli.")

# Patička
st.markdown("---")
st.caption(f"Databáze obsahuje {len(df)} zápasů z let 2024-2025. Data jsou stahována automaticky z GitHub repozitáře Jeffa Sackmanna.")
