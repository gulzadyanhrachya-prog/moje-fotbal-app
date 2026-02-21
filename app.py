import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

# --- NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="WTA Tennis Rankings", layout="wide")

st.title("🎾 WTA Tennis Rankings Dashboard")
st.markdown("Přehled aktuálního žebříčku tenistek (Data z Tennis API).")

# --- 1. FUNKCE PRO NAČTENÍ DAT ---
@st.cache_data(ttl=3600)  # Cache na 1 hodinu
def get_data():
    # Správná URL pro tvé nové API
    url = "https://tennisapi1.p.rapidapi.com/api/tennis/rankings/wta"
    
    # Kontrola, zda jsou nastaveny klíče
    if "RAPIDAPI_KEY" not in st.secrets or "RAPIDAPI_HOST" not in st.secrets:
        st.error("Chybí API klíče! Nastav je v .streamlit/secrets.toml nebo v nastavení cloudu.")
        return None

    headers = {
        "X-RapidAPI-Key": st.secrets["RAPIDAPI_KEY"],
        "X-RapidAPI-Host": st.secrets["RAPIDAPI_HOST"]
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Vyvolá chybu, pokud API vrátí 4xx nebo 5xx
        return response.json()
    except requests.exceptions.HTTPError as err:
        st.error(f"HTTP Chyba: {err}")
        return None
    except Exception as e:
        st.error(f"Jiná chyba: {e}")
        return None

# --- 2. ZPRACOVÁNÍ A ZOBRAZENÍ ---
data = get_data()

if data and "rankings" in data:
    rankings_list = []
    
    # Procházení JSONu a výběr dat
    for item in data["rankings"]:
        # Bezpečné získání země (vnořený slovník)
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

    # Vytvoření tabulky (DataFrame)
    df = pd.DataFrame(rankings_list)

    # --- 3. METRIKY A FILTRY ---
    
    # Horní panel s čísly
    col1, col2, col3 = st.columns(3)
    with col1:
        if not df.empty:
            top_player = df.iloc[0]["Jméno"]
            st.metric("Aktuální jednička", top_player)
    with col2:
        st.metric("Počet hráček v datech", len(df))
    with col3:
        avg_points = round(df["Body"].mean()) if not df.empty else 0
        st.metric("Průměrný počet bodů", avg_points)

    st.divider()

    # Filtr podle země
    all_countries = sorted(df["Země"].unique().tolist())
    selected_country = st.selectbox("Filtrovat podle země:", ["Všechny"] + all_countries)

    if selected_country != "Všechny":
        df_display = df[df["Země"] == selected_country]
    else:
        df_display = df

    # --- 4. TABULKA A GRAF ---
    
    col_table, col_graph = st.columns([3, 2])

    with col_table:
        st.subheader("Tabulka žebříčku")
        
        # Funkce pro barvy (Zelená pro posun nahoru, Červená dolů)
        def color_change(val):
            if val > 0:
                return 'color: green'
            elif val < 0:
                return 'color: red'
            return 'color: gray'

        st.dataframe(
            df_display.style.map(color_change, subset=['Změna']),
            use_container_width=True,
            hide_index=True,
            height=600
        )

    with col_graph:
        st.subheader("TOP 10 Hráček (Body)")
        
        # Vezmeme top 10 z filtrovaných dat (nebo celkových, pokud je filtr prázdný)
        # Pokud je filtr zapnutý, ukáže top 10 z dané země
        top_10_graph = df_display.head(10).sort_values("Body", ascending=True)
        
        if not top_10_graph.empty:
            fig, ax = plt.subplots(figsize=(5, 8))
            ax.barh(top_10_graph["Jméno"], top_10_graph["Body"], color="#374df5")
            ax.set_xlabel("Body")
            ax.set_title("Body v žebříčku")
            st.pyplot(fig)
        else:
            st.info("Žádná data pro graf.")

else:
    st.warning("Nepodařilo se načíst data. Zkontroluj API klíč a připojení.")
