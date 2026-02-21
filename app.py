import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

# Nastavení stránky
st.set_page_config(page_title="WTA Tennis Rankings", layout="wide")

st.title("🎾 WTA Tennis Rankings Dashboard")
st.markdown("Přehled aktuálního žebříčku tenistek na základě dat z RapidAPI.")

# --- 1. NAČTENÍ DAT ---
@st.cache_data(ttl=3600) # Ukládá data do cache na 1 hodinu, aby se šetřily API requesty
def get_data():
    # ZDE DOPLŇ SVOU URL Z RAPIDAPI (např. 'https://tennis-live-data.p.rapidapi.com/rankings/wta')
    url = "URL_TVÉ_RAPID_API_ZDE" 
    
    # API klíč se načte z "Secrets" ve Streamlitu (bezpečné uložení)
    # Pokud testuješ lokálně, můžeš klíč vložit přímo, ale na GitHub ho nedávej!
    headers = {
        "X-RapidAPI-Key": st.secrets["RAPIDAPI_KEY"],
        "X-RapidAPI-Host": st.secrets["RAPIDAPI_HOST"]
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Zkontroluje chyby
        return response.json()
    except Exception as e:
        st.error(f"Chyba při načítání dat z API: {e}")
        return None

# Pokud nemáš nastavené API klíče, použijeme pro ukázku tvá data (HARDCODED DEMO)
# Až to nasadíš s klíči, tento blok 'else' se přeskočí nebo ho můžeš smazat.
if "RAPIDAPI_KEY" not in st.secrets:
    st.warning("⚠️ Pozor: Jedeš v demo režimu bez API klíče. Zobrazují se statická data.")
    # Zde simulujeme tvůj JSON (zkráceno pro přehlednost kódu, v reálu by to šlo z API)
    # Pro účely ukázky předpokládáme, že data přišla z API funkce výše.
    # V reálném nasazení odkomentuj řádek níže:
    # data = get_data()
    st.stop() # Zastaví aplikaci, pokud nejsou klíče, aby nespadla (v reálu smaž a nastav klíče)
else:
    data = get_data()

# --- 2. ZPRACOVÁNÍ DAT ---
if data and "rankings" in data:
    rankings_list = []
    
    for item in data["rankings"]:
        # Vytáhneme jen to důležité z vnořeného JSONu
        player = {
            "Rank": item.get("ranking"),
            "Jméno": item.get("rowName"),
            "Země": item.get("team", {}).get("country", {}).get("name", "N/A"),
            "Body": item.get("points"),
            "Změna": item.get("previousRanking", 0) - item.get("ranking", 0), # Kladné číslo = posun nahoru
            "Nejlepší Rank": item.get("bestRanking"),
            "Zápasy": item.get("tournamentsPlayed", 0) # Pokud je v datech
        }
        rankings_list.append(player)

    df = pd.DataFrame(rankings_list)

    # --- 3. VIZUALIZACE ---
    
    # Metriky nahoře
    col1, col2, col3 = st.columns(3)
    with col1:
        top_player = df.iloc[0]["Jméno"]
        st.metric("Aktuální jednička", top_player)
    with col2:
        total_players = len(df)
        st.metric("Počet hráček v žebříčku", total_players)
    with col3:
        avg_points = round(df["Body"].mean())
        st.metric("Průměrný počet bodů", avg_points)

    # Filtrování podle země
    countries = ["Všechny"] + sorted(df["Země"].unique().tolist())
    selected_country = st.selectbox("Filtrovat podle země:", countries)

    if selected_country != "Všechny":
        df_display = df[df["Země"] == selected_country]
    else:
        df_display = df

    # Zobrazení tabulky
    st.subheader("Tabulka žebříčku")
    
    # Formátování tabulky (obarvení sloupce Změna)
    def color_change(val):
        color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
        return f'color: {color}'

    st.dataframe(
        df_display.style.map(color_change, subset=['Změna']),
        use_container_width=True,
        hide_index=True
    )

    # Graf TOP 10
    st.subheader("TOP 10 Hráček podle bodů")
    top_10 = df.head(10).sort_values("Body", ascending=True) # Sort pro graf
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(top_10["Jméno"], top_10["Body"], color="#374df5")
    ax.set_xlabel("Body")
    st.pyplot(fig)

else:
    st.write("Žádná data k zobrazení.")
