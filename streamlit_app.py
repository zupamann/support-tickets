import datetime
import pandas as pd
import streamlit as st
import altair as alt

# Postavke stranice
st.set_page_config(page_title="Support tickets", page_icon="🎫")
st.title("🎫 Support tickets")
st.write(
    """
    Ova aplikacija omogućuje upravljanje podrškom kroz 5 različitih podkategorija.
    Možete dodavati nove tikete, uređivati postojeće unutar pripadajućih tablica i pratiti statistiku.
    """
)

# Definiranje 5 podkategorija
KATEGORIJE = ["BEMV", "BMV", "PN", "Ostalo", "Privatno"]

# Inicijalizacija praznog Dataframe-a u session state ako već ne postoji
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(
        columns=["ID", "Kategorija", "Issue", "Status", "Priority", "Date Submitted"]
    )

# --- SEKCIJA ZA DODAVANJE TIKETA ---
st.header("Dodaj novi tiket")

with st.form("add_ticket_form", clear_on_submit=True):
    issue = st.text_area("Opišite problem")
    kategorija = st.selectbox("Podkategorija", KATEGORIJE)
    priority = st.selectbox("Prioritet", ["High", "Medium", "Low"])
    submitted = st.form_submit_button("Podnesi tiket")

if submitted and issue.strip() != "":
    if len(st.session_state.df) == 0:
        next_id = 1101
    else:
        id_brojevi = st.session_state.df["ID"].apply(lambda x: int(x.split("-")[1]))
        next_id = max(id_brojevi) + 1

    today = datetime.date.today()
    
    df_new = pd.DataFrame(
        [
            {
                "ID": f"TICKET-{next_id}",
                "Kategorija": kategorija,
                "Issue": issue,
                "Status": "Open",
                "Priority": priority,
                "Date Submitted": today,
            }
        ]
    )

    st.session_state.df = pd.concat([df_new, st.session_state.df], axis=0).reset_index(drop=True)
    st.success(f"Tiket uspješno dodan u kategoriju {kategorija}!")
elif submitted and issue.strip() == "":
    st.error("Molimo unesite opis problema prije slanja.")


# --- SEKCIJA ZA PRIKAZ I UREĐIVANJE PO KATEGORIJAMA ---
st.header("Postojeći tiketi")
st.write(f"Ukupan broj tiketa u sustavu: `{len(st.session_state.df)}`")

st.info(
    "Tikete možete uređivati dvostrukim klikom na ćeliju unutar pripadajuće tablice kategorije.",
    icon="✍️",
)

# Kreiranje tabova za svaku podkategoriju
tabs = st.tabs(KATEGORIJE)

# Prolazimo kroz svaki tab
for tab, kat in zip(tabs, KATEGORIJE):
    with tab:
        # Filtriramo i resetiramo indeks kako bi data_editor ispravno pratio retke (0, 1, 2...)
        df_kat = st.session_state.df[st.session_state.df["Kategorija"] == kat].reset_index()
        
        st.write(f"Broj tiketa u ovoj kategoriji: `{len(df_kat)}`")
        
        editor_key = f"editor_{kat}"
        
        edited_kat_df = st.data_editor(
            df_kat.drop(columns=["index"]), # Sakrivamo pomoćni indeks iz prikaza
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Open", "In Progress", "Closed"],
                    required=True,
                ),
                "Priority": st.column_config.SelectboxColumn(
                    "Priority",
                    options=["High", "Medium", "Low"],
                    required=True,
                ),
                "Kategorija": None, 
            },
            disabled=["ID", "Date Submitted"],
            key=editor_key
        )
        
        # Provjera je li korisnik stvarno kliknuo i promijenio nešto u tablici
        if editor_key in st.session_state and st.session_state[editor_key]["edited_rows"]:
            promjene = st.session_state[editor_key]["edited_rows"]
            
            # Prolazimo kroz sve uredi-redove i mapiramo ih natrag u st.session_state.df pomoću originalnog indeksa
            for lokalni_indeks, izmijenjene_vrijednosti in promjene.items():
                originalni_indeks = df_kat.loc[int(lokalni_indeks), "index"]
                for stupac, nova_vrijednost in izmijenjene_vrijednosti.items():
                    st.session_state.df.at[originalni_indeks, stupac] = nova_vrijednost
            
            st.rerun()


# --- STATISTIKA (GRAFOVI) ---
st.header("Statistika")

# Grafove crtamo samo ako imamo barem 1 tiket u sustavu
if len(st.session_state.df) > 0:
    col1, col2, col3 = st.columns(3)
    num_open_tickets = len(st.session_state.df[st.session_state.df.Status == "Open"])
    col1.metric(label="Broj otvorenih tiketa", value=num_open_tickets)
    col2.metric(label="Vrijeme prvog odgovora (sati)", value=5.2)
    col3.metric(label="Prosječno vrijeme rješavanja (sati)", value=16)

    # Čišćenje podataka prije slanja u Altair grafikon
    graf_df = st.session_state.df.copy()
    
    # Filtriramo van bilo kakve potencijalno prazne redove (sigurnosni korak)
    graf_df = graf_df.dropna(subset=["Date Submitted", "Status", "Priority"])
    graf_df = graf_df[graf_df["ID"].astype(str).str.strip() != ""]
    
    # Pretvaranje u pravi datetime format
    graf_df["Date Submitted"] = pd.to_datetime(graf_df["Date Submitted"])

    # Graf 1: Status tiketa kroz mjesece
    st.write("")
    st.write("##### Status tiketa po mjesecima")
    status_plot = (
        alt.Chart(graf_df)
        .mark_bar()
        .encode(
            x="month(Date Submitted):O",
            y="count():Q",
            xOffset="Status:N",
            color="Status:N",
        )
        .configure_legend(
            orient="bottom", titleFontSize=14, labelFontSize=14, titlePadding=5
        )
    )
    st.altair_chart(status_plot, use_container_width=True, theme="streamlit")

    # Graf 2: Prioriteti
    st.write("##### Trenutni prioriteti tiketa")
    priority_plot = (
        alt.Chart(graf_df)
        .mark_arc()
        .encode(theta="count():Q", color="Priority:N")
        .properties(height=300)
        .configure_legend(
            orient="bottom", titleFontSize=14, labelFontSize=14, titlePadding=5
        )
    )
    st.altair_chart(priority_plot, use_container_width=True, theme="streamlit")
else:
    st.write("Trenutno nema podataka za prikaz statistike. Dodajte nekoliko tiketa kako biste vidjeli grafikone.")
