import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

# --- NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="WTA Tennis Rankings", layout="wide")

st.title("🎾 WTA Tennis Rankings Dashboard")
st.markdown("Kompletní přehled ženského tenisu s analýzou a simulátorem.")

# --- 1. FUNKCE PRO NAČTENÍ DAT ---
@st.cache_data(ttl=3600)  # Cache na 1 hodinu šetří API requesty
def get_data():
    # Správná URL pro tvé nové API (Tennis API)
    url = "https://tennisapi1.p.rapidapi.com/api/tennis/rankings/wta"
    
    # Kontrola klíčů
    if "RAPIDAPI_KEY" not in st.secrets or "RAPIDAPI_HOST" not in st.secrets:
        st.error("Chybí API klíče! Nastav je v .streamlit/secrets.toml nebo v nastavení cloudu.")
        return None

    headers = {
        "X-RapidAPI-Key": st.secrets["RAPIDAPI_KEY"],
        "X-RapidAPI-Host": st.secrets["RAPIDAPI_HOST"]
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        st.error(f"HTTP Chyba (zkontroluj Host/Key): {err}")
        return None
    except Exception as e:
        st.error(f"Jiná chyba: {e}")
        return None

# --- 2. ZPRACOVÁNÍ DAT ---
data = get_data()

if data and "rankings" in data:
    rankings_list = []
    
    # Procházení JSONu
    for item in data["rankings"]:
        # Bezpečné získání země
        try:
            country = item.get("team", {}).get("country", {}).get("name", "N/A")
        except AttributeError:
            country = "N/A"

        player = {
            "Rank": item.get("ranking"),
            "Jméno": item.get("rowName"),
            "Země": country,
            "Body": item.get("points"),
            "Změna": item.get("previousRanking", 0) - item.get("ranking", 0),
            "Nejlepší Rank": item.get("bestRanking"),
            "ID": item.get("id")
        }
        rankings_list.append(player)

    # Vytvoření DataFrame
    df = pd.DataFrame(rankings_list)

    # --- 3. METRIKY A FILTRY ---
    
    # Horní panel
    col1, col2, col3 = st.columns(3)
    with col1:
        top_player = df.iloc[0]["Jméno"]
        st.metric("Aktuální jednička", top_player, delta="WTA #1")
    with col2:
        st.metric("Počet hráček v datech", len(df))
    with col3:
        avg_points = round(df["Body"].mean())
        st.metric("Průměrný počet bodů", avg_points)

    st.divider()

    # Filtr
    all_countries = sorted(df["Země"].unique().tolist())
    selected_country = st.selectbox("Filtrovat podle země:", ["Všechny"] + all_countries)

    if selected_country != "Všechny":
        df_display = df[df["Země"] == selected_country]
    else:
        df_display = df

    # --- 4. TABULKA A GRAF ---
    
    col_table, col_graph = st.columns([3, 2])

    with col_table:
        st.subheader(f"Žebříček ({selected_country})")
        
        def color_change(val):
            if val > 0: return 'color: green'
            elif val < 0: return 'color: red'
            return 'color: gray'

        st.dataframe(
            df_display.style.map(color_change, subset=['Změna']),
            use_container_width=True,
            hide_index=True,
            height=500
        )

    with col_graph:
        st.subheader("TOP 10 Hráček (Body)")
        top_10_graph = df_display.head(10).sort_values("Body", ascending=True)
        
        if not top_10_graph.empty:
            fig, ax = plt.subplots(figsize=(5, 6))
            ax.barh(top_10_graph["Jméno"], top_10_graph["Body"], color="#374df5")
            ax.set_xlabel("Body")
            st.pyplot(fig)
        else:
            st.info("Žádná data pro graf.")

    # --- 5. ANALÝZA ZEMÍ ---
    st.divider()
    st.subheader("🌍 Dominance zemí v TOP 100")
    
    # Vezmeme jen top 100 pro statistiku zemí
    df_top100 = df.head(100)
    country_counts = df_top100["Země"].value_counts().head(10) # Top 10 zemí
    
    col_pie1, col_pie2 = st.columns([2, 1])
    
    with col_pie1:
        fig2, ax2 = plt.subplots()
        ax2.pie(country_counts, labels=country_counts.index, autopct='%1.1f%%', startangle=90)
        ax2.axis('equal')
        st.pyplot(fig2)
    
    with col_pie2:
        st.write("Nejvíce zastoupené země v první stovce:")
        st.dataframe(country_counts, use_container_width=True)

    # --- 6. SIMULÁTOR ZÁPASU ---
    st.divider()
    st.header("🔮 Simulátor zápasu (Papírový favorit)")
    st.caption("Vyber dvě hráčky a zjisti, kdo má statisticky větší šanci na výhru podle aktuálních bodů.")
    
    col_sim1, col_sim2 = st.columns(2)
    player_names = df["Jméno"].tolist()
    
    with col_sim1:
        player_a = st.selectbox("Hráčka 1", player_names, index=0)
    with col_sim2:
        # Zkusíme vybrat druhou hráčku jako default, pokud existuje
        default_idx = 1 if len(player_names) > 1 else 0
        player_b = st.selectbox("Hráčka 2", player_names, index=default_idx)

    if st.button("Analyzovat duel"):
        if player_a == player_b:
            st.warning("Vyber prosím dvě různé hráčky.")
        else:
            # Načtení dat
            p1_data = df[df["Jméno"] == player_a].iloc[0]
            p2_data = df[df["Jméno"] == player_b].iloc[0]
            
            diff = p1_data["Body"] - p2_data["Body"]
            favorite = player_a if diff > 0 else player_b
            
            # Výpočet pravděpodobnosti (jednoduchý model na základě podílu bodů)
            total_pts = p1_data["Body"] + p2_data["Body"]
            p1_prob = p1_data["Body"] / total_pts
            p2_prob = p2_data["Body"] / total_pts

            # Zobrazení výsledku
            c1, c2, c3 = st.columns([1, 0.5, 1])
            
            with c1:
                st.info(f"**{player_a}**")
                st.write(f"Rank: #{p1_data['Rank']}")
                st.write(f"Body: {p1_data['Body']}")
                
            with c2:
                st.markdown("<h1 style='text-align: center;'>VS</h1>", unsafe_allow_html=True)
                
            with c3:
                st.info(f"**{player_b}**")
                st.write(f"Rank: #{p2_data['Rank']}")
                st.write(f"Body: {p2_data['Body']}")
            
            st.success(f"🏆 Favoritkou je **{favorite}** (o {abs(diff)} bodů)")
            
            st.write("Pravděpodobnost výhry:")
            st.progress(p1_prob, text=f"{player_a}: {round(p1_prob*100)}%")
            st.progress(p2_prob, text=f"{player_b}: {round(p2_prob*100)}%")

else:
    st.warning("Nepodařilo se načíst data. Zkontroluj API klíč a připojení.")
