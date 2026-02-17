import streamlit as st
import requests
import pandas as pd
import json

# ==============================================================================
# 1. NASTAVENÍ STRÁNKY
# ==============================================================================
st.set_page_config(page_title="Tennis Pro Analyst", layout="wide", page_icon="🎾")

st.markdown("""
<style>
    .winner-box { border: 2px solid #4CAF50; padding: 20px; border-radius: 10px; background-color: #f0fff4; text-align: center; }
    .vs-text { font-size: 30px; font-weight: bold; color: #555; text-align: center; padding-top: 20px; }
</style>
""", unsafe_allow_html=True)

st.title("🎾 Tennis H2H Predictor (Final)")

# ==============================================================================
# 2. NAČTENÍ KLÍČE
# ==============================================================================
try:
    api_key = st.secrets["RAPIDAPI_KEY"]
    st.sidebar.success("✅ API Klíč aktivní")
except:
    api_key = st.sidebar.text_input("Vlož X-RapidAPI-Key:", type="password")

# ==============================================================================
# 3. VSTUPY
# ==============================================================================
st.sidebar.header("Nastavení Zápasu")
p1_id = st.sidebar.text_input("ID Hráče 1:", value="5992") # Djokovič
p2_id = st.sidebar.text_input("ID Hráče 2:", value="677")  # Nadal

# Pevně daná URL (stejná jako v Exploreru)
url = "https://tennis-api-atp-wta-itf.p.rapidapi.com/tennis/v1/h2h"
host = "tennis-api-atp-wta-itf.p.rapidapi.com"

# ==============================================================================
# 4. LOGIKA APLIKACE
# ==============================================================================
if st.button("🚀 Analyzovat zápas"):
    if not api_key:
        st.error("Chybí API klíč!")
    else:
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host
        }
        
        # Zkusíme poslat ID jako čísla (int), to je pro API bezpečnější
        try:
            params = {
                "player1_id": int(p1_id),
                "player2_id": int(p2_id)
            }
        except:
            st.error("ID musí být čísla!")
            st.stop()
        
        with st.spinner("Stahuji data..."):
            try:
                # Používáme GET (stejně jako v Exploreru)
                response = requests.get(url, headers=headers, params=params)
                
                # --- DEBUG SEKCE (Pro zjištění chyby) ---
                with st.expander("🛠️ Debug Info (Pokud to nefunguje, podívej se sem)"):
                    st.write(f"**URL:** {url}")
                    st.write(f"**Status Code:** {response.status_code}")
                    st.write(f"**Posílané parametry:** {params}")
                    st.write("**Odpověď serveru:**")
                    st.text(response.text)
                # ----------------------------------------

                data = response.json()

                # Kontrola chyb
                if response.status_code != 200:
                    st.error(f"Chyba komunikace: {response.status_code}")
                    st.stop()

                if "message" in data:
                    st.error(f"API hlásí chybu: {data['message']}")
                    st.stop()

                # Zpracování dat
                match_data = None
                
                # Logika pro nalezení správných dat v JSONu
                if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                    match_data = data['data'][0]
                elif isinstance(data, list) and len(data) > 0:
                    match_data = data[0]
                
                if not match_data:
                    st.warning("API vrátilo prázdná data. Zkontroluj ID hráčů.")
                else:
                    # ==========================================================
                    # 5. VÝPOČTY A PREDIKCE
                    # ==========================================================
                    # Bezpečné načtení hodnot (s ochranou proti chybějícím klíčům)
                    p1_obj = match_data.get('player1', {})
                    p2_obj = match_data.get('player2', {})
                    
                    p1_name = p1_obj.get('name', 'Hráč 1')
                    p1_wins = int(p1_obj.get('wins', 0))
                    p1_country = p1_obj.get('countryAcr', '')
                    
                    p2_name = p2_obj.get('name', 'Hráč 2')
                    p2_wins = int(p2_obj.get('wins', 0))
                    p2_country = p2_obj.get('countryAcr', '')
                    
                    total_matches = p1_wins + p2_wins
                    
                    # Výpočet pravděpodobnosti
                    if total_matches > 0:
                        p1_prob = p1_wins / total_matches
                        p2_prob = p2_wins / total_matches
                        
                        p1_odd = round(1 / p1_prob, 2) if p1_prob > 0 else 99.0
                        p2_odd = round(1 / p2_prob, 2) if p2_prob > 0 else 99.0
                    else:
                        p1_prob = 0.5
                        p2_prob = 0.5
                        p1_odd = 2.00
                        p2_odd = 2.00

                    # ==========================================================
                    # 6. VYKRESLENÍ UI
                    # ==========================================================
                    
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
                    
                    st.subheader("📊 Predikce modelu")
                    st.write(f"Pravděpodobnost výhry: **{p1_name} ({int(p1_prob*100)}%)** vs **{p2_name} ({int(p2_prob*100)}%)**")
                    st.progress(p1_prob)
                    
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

            except Exception as e:
                st.error(f"Chyba aplikace: {e}")
