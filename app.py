import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from thefuzz import process

# ==============================================================================\
# 1. KONFIGURACE A STYLY\
# ==============================================================================\

st.set_page_config(page_title="Tennis Betting AI 2026", layout="wide", page_icon="🎾")

st.markdown("""
<style>
    .tip-card { background-color: #d4edda; padding: 15px; border-radius: 10px; border-left: 5px solid #28a745; margin-bottom: 10px; }
    .match-card { background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 5px; border: 1px solid #ddd; }
    .high-conf { color: #28a745; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🎾 Tennis AI: Live Matches & Predictions (2026 Ready)")

# ==============================================================================\
# 2. NAČTENÍ HISTORICKÝCH DAT (MOZEK)\
# ==============================================================================\

@st.cache_data(ttl=3600)
def load_historical_data():
    # Stahujeme data ATP a WTA z open-source databáze Jeffa Sackmanna
    base_atp = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{}.csv"
    base_wta = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_{}.csv"
    
    # Data včetně roku 2026
    years = [2024, 2025, 2026] 
    data_frames = []
    
    status_text = st.empty()
    status_text.text("⏳ Aktualizuji databázi o výsledky z roku 2026...")
    
    for year in years:
        try:
            # ATP Data
            df_atp = pd.read_csv(base_atp.format(year), on_bad_lines='skip')
            df_atp['tour'] = 'ATP'
            data_frames.append(df_atp)
            
            # WTA Data
            df_wta = pd.read_csv(base_wta.format(year), on_bad_lines='skip')
            df_wta['tour'] = 'WTA'
            data_frames.append(df_wta)
        except:
            pass
            
    status_text.empty()
    
    if not data_frames: 
        return pd.DataFrame()
    
    full_df = pd.concat(data_frames, ignore_index=True)
    full_df['tourney_date'] = pd.to_datetime(full_df['tourney_date'], format='%Y%m%d', errors='coerce')
    return full_df

df_history = load_historical_data()

# Seznam všech hráčů v databázi pro vyhledávání
if not df_history.empty:
    db_players = pd.concat([df_history['winner_name'], df_history['loser_name']]).unique()
    db_players = [str(p) for p in db_players if isinstance(p, str)]
else:
    db_players = []

# ==============================================================================\
# 3. FUNKCE PRO API (ROZVRH) - OPRAVENÁ URL\
# ==============================================================================\

def get_todays_matches(api_key, date_str):
    # OPRAVA: Správný endpoint pro Matchstat API je obvykle '/schedule'
    url = "https://tennis-api-atp-wta-itf.p.rapidapi.com/tennis/v1/schedule"
    host = "tennis-api-atp-wta-itf.p.rapidapi.com"
    
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": host
    }
    params = {"date": date_str}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        return response.json()
    except:
        return None

# ==============================================================================\
# 4. POMOCNÉ FUNKCE (PREDIKCE & PÁROVÁNÍ)\
# ==============================================================================\

def find_player_in_db(api_name):
    # Zkusí najít jméno z API v naší databázi (Fuzzy matching)
    if not api_name or not db_players: return None
    
    match = process.extractOne(api_name, db_players)
    
    if match and match[1] > 85: 
        return match[0]
    return None

def calculate_win_prob(player, surface):
    # Zjednodušený model: Win Rate na povrchu + Celkový Win Rate
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
# 5. UI APLIKACE\
# ==============================================================================\

# Sidebar - API Klíč
try:
    api_key = st.secrets["RAPIDAPI_KEY"]
    st.sidebar.success("✅ API Klíč načten")
except:
    api_key = st.sidebar.text_input("Vlož X-RapidAPI-Key:", type="password")

# Záložky
tab1, tab2 = st.tabs(["📅 Dnešní Zápasy & Tipy", "🔍 Manuální Analýza"])

# --- TAB 1: LIVE ZÁPASY ---
with tab1:
    st.header("Dnešní nabídka zápasů")
    st.caption("Stáhne program z RapidAPI a porovná ho s databází (2024-2026).")
    
    col_date, col_btn = st.columns([3, 1])
    selected_date = col_date.date_input("Vyber datum:", datetime.now())
    
    if col_btn.button("📡 Stáhnout program"):
        if not api_key:
            st.error("Chybí API klíč!")
        else:
            with st.spinner("Stahuji zápasy z API a počítám predikce..."):
                api_data = get_todays_matches(api_key, selected_date.strftime("%Y-%m-%d"))
                
                matches_found = []
                
                # Logika pro parsování JSONu
                raw_matches = []
                
                # Kontrola chyb API
                if api_data and "message" in api_data:
                    st.error(f"Chyba API: {api_data['message']}")
                else:
                    if api_data and 'data' in api_data:
                        raw_matches = api_data['data']
                    elif isinstance(api_data, list):
                        raw_matches = api_data
                    elif api_data and 'results' in api_data:
                        raw_matches = api_data['results']
                    
                    if not raw_matches:
                        st.warning("Žádné zápasy nenalezeny. Zkus jiné datum.")
                        if api_data: 
                            with st.expander("Zobrazit odpověď API"):
                                st.json(api_data)
                    else:
                        for m in raw_matches:
                            try:
                                # Získání jmen z API (struktura se může lišit)
                                p1_api = m.get('player1', {}).get('name') or m.get('home_player')
                                p2_api = m.get('player2', {}).get('name') or m.get('away_player')
                                tournament = m.get('tournament', {}).get('name', 'Unknown')
                                
                                surface_api = m.get('tournament', {}).get('surface', 'Hard')
                                
                                surface_db = "Hard"
                                if surface_api and "Clay" in surface_api: surface_db = "Clay"
                                elif surface_api and "Grass" in surface_api: surface_db = "Grass"
                                elif surface_api and "Carpet" in surface_api: surface_db = "Carpet"
                                
                                if p1_api and p2_api:
                                    p1_db = find_player_in_db(p1_api)
                                    p2_db = find_player_in_db(p2_api)
                                    
                                    if p1_db and p2_db:
                                        prob1 = calculate_win_prob(p1_db, surface_db)
                                        prob2 = calculate_win_prob(p2_db, surface_db)
                                        
                                        total_prob = prob1 + prob2
                                        if total_prob > 0:
                                            final_p1 = prob1 / total_prob
                                            final_p2 = prob2 / total_prob
                                        else:
                                            final_p1 = 0.5
                                            final_p2 = 0.5
                                        
                                        matches_found.append({
                                            "p1": p1_db, "p2": p2_db,
                                            "prob1": final_p1, "prob2": final_p2,
                                            "tour": tournament, "surface": surface_db
                                        })
                            except: continue

                        if matches_found:
                            st.success(f"Analyzováno {len(matches_found)} zápasů s historií v DB.")
                            
                            matches_found.sort(key=lambda x: abs(x['prob1'] - 0.5), reverse=True)
                            
                            st.subheader("🔥 TOP TIPY DNE")
                            for match in matches_found[:5]:
                                p1 = match['p1']
                                p2 = match['p2']
                                prob = match['prob1'] if match['prob1'] > 0.5 else match['prob2']
                                winner = p1 if match['prob1'] > 0.5 else p2
                                
                                if prob > 0.60:
                                    st.markdown(f"""
                                    <div class="tip-card">
                                        <h4>🏆 {winner}</h4>
                                        <p>{p1} vs {p2} | {match['tour']} ({match['surface']})</p>
                                        <p>Důvěra modelu: <strong>{int(prob*100)}%</strong> (Fair kurz: {round(1/prob, 2)})</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                            
                            st.divider()
                            st.subheader("📋 Všechny analyzované zápasy")
                            for match in matches_found:
                                c1, c2, c3 = st.columns([2, 1, 2])
                                with c1: 
                                    st.write(f"**{match['p1']}**")
                                    if match['prob1'] > 0.5: st.progress(match['prob1'])
                                with c2: st.caption(f"{match['surface']}")
                                with c3: 
                                    st.write(f"**{match['p2']}**")
                                    if match['prob2'] > 0.5: st.progress(match['prob2'])
                                st.markdown("---")
                                
                        else:
                            st.info("Zápasy staženy, ale nenašel jsem hráče v historické databázi.")
                            if raw_matches:
                                with st.expander("Zobrazit surová data z API"):
                                    st.json(raw_matches)

# --- TAB 2: MANUÁLNÍ ANALÝZA ---
with tab2:
    st.header("Manuální H2H Analýza")
    
    col_s, col_p1, col_p2 = st.columns(3)
    surface_man = col_s.selectbox("Povrch:", ["Hard", "Clay", "Grass"])
    
    if not df_history.empty:
        idx1 = 0
        idx2 = 1
        if "Novak Djokovic" in db_players: idx1 = db_players.index("Novak Djokovic")
        if "Carlos Alcaraz" in db_players: idx2 = db_players.index("Carlos Alcaraz")

        p1_man = col_p1.selectbox("Hráč 1:", db_players, index=idx1)
        p2_man = col_p2.selectbox("Hráč 2:", db_players, index=idx2)
        
        if st.button("Analyzovat duel"):
            prob1 = calculate_win_prob(p1_man, surface_man)
            prob2 = calculate_win_prob(p2_man, surface_man)
            
            total = prob1 + prob2
            final1 = prob1 / total
            
            st.metric(f"Šance {p1_man}", f"{int(final1*100)}%")
            st.metric(f"Šance {p2_man}", f"{int((1-final1)*100)}%")
            
            st.subheader("Vzájemné zápasy v DB")
            h2h = df_history[((df_history['winner_name'] == p1_man) & (df_history['loser_name'] == p2_man)) | 
                             ((df_history['winner_name'] == p2_man) & (df_history['loser_name'] == p1_man))]
            if not h2h.empty:
                st.dataframe(h2h[['tourney_date', 'winner_name', 'score', 'surface']], hide_index=True)
            else:
                st.info("Žádné vzájemné zápasy v databázi (2024-2026).")
