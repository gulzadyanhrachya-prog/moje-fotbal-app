import streamlit as st
import requests
import pandas as pd
import json

# ==============================================================================\n# 1. NASTAVENÍ STRÁNKY\n# ==============================================================================\nst.set_page_config(page_title="Tennis Pro Analyst", layout="wide", page_icon="🎾")

st.markdown("""
<style>
    .big-font { font-size: 24px !important; font-weight: bold; }
    .winner-box { border: 2px solid #4CAF50; padding: 20px; border-radius: 10px; background-color: #f0fff4; text-align: center; }
    .vs-text { font-size: 30px; font-weight: bold; color: #555; text-align: center; padding-top: 20px; }
</style>
""", unsafe_allow_html=True)

st.title("🎾 Tennis H2H Predictor")
st.caption("Analýza vzájemných zápasů a výpočet férových kurzů.")

# ==============================================================================\n# 2. NAČTENÍ KLÍČE\n# ==============================================================================\ntry:
    api_key = st.secrets["RAPIDAPI_KEY"]
    st.sidebar.success("✅ API Klíč aktivní")
except:
    api_key = st.sidebar.text_input("Vlož X-RapidAPI-Key:", type="password")

# ==============================================================================\n# 3. VSTUPY (ID HRÁČŮ)\n# ==============================================================================\nst.sidebar.header("Nastavení Zápasu")
# Předvyplněno: Djokovič (5992) vs Nadal (677)
p1_id = st.sidebar.text_input("ID Hráče 1:", value="5992")
p2_id = st.sidebar.text_input("ID Hráče 2:", value="677")

# URL Endpointu (H2H)
url = "https://tennis-api-atp-wta-itf.p.rapidapi.com/tennis/v1/h2h"
host = "tennis-api-atp-wta-itf.p.rapidapi.com"

# ==============================================================================\n# 4. LOGIKA APLIKACE\n# ==============================================================================\nif st.button("🚀 Analyzovat zápas"):
    if not api_key:
        st.error("Chybí API klíč!")
    else:
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host
        }
        
        # Parametry pro API
        params = {
            "player1_id": p1_id,
            "player2_id": p2_id
        }
        
        with st.spinner("Stahuji historická data..."):
            try:
                response = requests.get(url, headers=headers, params=params)
                data = response.json()
                
                # Zpracování dat
                # API vrací seznam 'data', musíme najít správný záznam
                match_data = None
                
                # Pokud API vrátí seznam, hledáme v něm
                raw_list = []
                if 'data' in data:
                    raw_list = data['data']
                elif isinstance(data, list):
                    raw_list = data
                
                # Projdeme seznam a najdeme naše dva hráče
                for item in raw_list:
                    # Získáme ID z dat (pozor, mohou být jako string nebo int)
                    id1_api = str(item.get('player1', {}).get('id'))
                    id2_api = str(item.get('player2', {}).get('id'))
                    
                    # Kontrola, zda to jsou naši hráči (v jakémkoliv pořadí)
                    if (id1_api == p1_id and id2_api == p2_id) or (id1_api == p2_id and id2_api == p1_id):
                        match_data = item
                        break
                
                if not match_data:
                    st.warning("Nebyla nalezena žádná vzájemná historie pro tato ID.")
                    st.json(data) # Ukážeme co přišlo, pro kontrolu
                else:
                    # ==========================================================\n                    # 5. VÝPOČTY A PREDIKCE\n                    # ==========================================================\n                    p1_name = match_data['player1']['name']
                    p1_wins = match_data['player1']['wins']
                    p1_country = match_data['player1'].get('countryAcr', '')
                    
                    p2_name = match_data['player2']['name']
                    p2_wins = match_data['player2']['wins']
                    p2_country = match_data['player2'].get('countryAcr', '')
                    
                    total_matches = p1_wins + p2_wins
                    
                    if total_matches > 0:
                        p1_prob = p1_wins / total_matches
                        p2_prob = p2_wins / total_matches
                        
                        p1_odd = round(1 / p1_prob, 2)
                        p2_odd = round(1 / p2_prob, 2)
                    else:
                        p1_prob = 0.5
                        p2_prob = 0.5
                        p1_odd = 2.00
                        p2_odd = 2.00

                    # ==========================================================\n                    # 6. VYKRESLENÍ UI\n                    # ==========================================================\n                    
                    # Hlavička zápasu
                    c1, c2, c3 = st.columns([2, 1, 2])
                    with c1:
                        st.markdown(f"<h2 style='text-align: center;'>{p1_name} <small>({p1_country})</small></h2>", unsafe_allow_html=True)
                        st.metric("Celkové výhry", p1_wins)
                    with c2:
                        st.markdown("<div class='vs-text'>VS</div>", unsafe_allow_html=True)
                        st.caption(f"Celkem zápasů: {total_matches}")
                    with c3:
                        st.markdown(f"<h2 style='text-align: center;'>{p2_name} <small>({p2_country})</small></h2>", unsafe_allow_html=True)
                        st.metric("Celkové výhry", p2_wins)
                    
                    st.divider()
                    
                    # Predikce
                    st.subheader("📊 Predikce modelu")
                    
                    # Progress bar
                    st.write(f"Pravděpodobnost výhry: **{p1_name} ({int(p1_prob*100)}%)** vs **{p2_name} ({int(p2_prob*100)}%)**")
                    st.progress(p1_prob)
                    
                    # Karty s kurzy
                    col_pred1, col_pred2 = st.columns(2)
                    
                    with col_pred1:
                        if p1_prob > 0.5:
                            st.markdown(f"""
                            <div class='winner-box'>
                                <h3>🏆 Favorit: {p1_name}</h3>
                                <p>Férový kurz: <strong>{p1_odd}</strong></p>
                                <p>Důvěra: {int(p1_prob*100)}%</p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.metric(f"Kurz {p1_name}", p1_odd)
                            
                    with col_pred2:
                        if p2_prob > 0.5:
                            st.markdown(f"""
                            <div class='winner-box'>
                                <h3>🏆 Favorit: {p2_name}</h3>
                                <p>Férový kurz: <strong>{p2_odd}</strong></p>
                                <p>Důvěra: {int(p2_prob*100)}%</p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.metric(f"Kurz {p2_name}", p2_odd)
                            
                    # Zobrazení surových dat (pro kontrolu)
                    with st.expander("🔍 Zobrazit detailní JSON data"):
                        st.json(match_data)

            except Exception as e:
                st.error(f"Chyba aplikace: {e}")
