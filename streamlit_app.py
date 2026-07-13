import datetime
import random

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

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
    # Stvaramo prazan dataframe s točno definiranim stupcima i tipovima podataka
    st.session_state.df = pd.DataFrame(
        columns=["ID", "Kategorija", "Issue", "Status", "Priority", "Date Submitted"]
    )

# --- SEKCIJA ZA DODAVANJE TIKETA ---
st.header("Dodaj novi tiket")

with st.form("add_ticket_form"):
    issue = st.text_area("Opišite problem")
    kategorija = st.selectbox("Podkategorija", KATEGORIJE)
    priority = st.selectbox("Prioritet", ["High", "Medium", "Low"])
    submitted = st.form_submit_button("Podnesi tiket")

if submitted and issue.strip() != "":
    # Generiranje ID-a (ako je tablica prazna kreće od 1101, inače uvećava najveći postojeći)
    if len(st.session_state.df) == 0:
        next_id = 1101
    else:
        # Izvlačimo brojeve iz ID-eva i tražimo maksimum
        id_brojevi = st.session_state.df["ID"].apply(lambda x: int(x.split("-")[1]))
        next_id = max(id_brojevi) + 1

    # Za grafove je najbolje koristiti standardni date objekt ili datetime
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

    # Spajanje novog tiketa na početak tablice
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

# Prolazimo kroz svaki tab i prikazujemo samo tikete koji pripadaju toj kategoriji
for tab, kat in zip(tabs, KATEGORIJE):
    with tab:
        # Filtriramo dataframe za trenutnu kategoriju
        df_kat = st.session_state.df[st.session_state.df["Kategorija"] == kat]
        
        st.write(f"Broj tiketa u ovoj kategoriji: `{len(df_kat)}`")
        
        # Prikaz i uređivanje tablice za specifičnu kategoriju
        edited_kat_df = st.data_editor(
            df_kat,
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
                # Skrivamo stupac kategorije u tabu jer se već nalazi unutar tog taba
                "Kategorija": None, 
            },
            disabled=["ID", "Date Submitted"],
            key=f"editor_{kat}" # Jedinstveni ključ za svaki data_editor
        )
        
        # Ako je korisnik napravio promjene u ovoj tablici, spremamo ih natrag u glavni st.session_state.df
        if not edited_kat_df.equals(df_kat):
            st.session_state.df.update(edited_kat_df)
            st.rerun()


# --- STATISTIKA (GRAFOVI) ---
st.header("Statistika")

if len(st.session_state.df) > 0:
    # Metrike na vrhu statistike
    col1, col2, col3 = st.columns(3)
    num_open_tickets = len(st.session_state.df[st.session_state.df.Status == "Open"])
    col1.metric(label="Broj otvorenih tiketa", value=num_open_tickets)
    col2.metric(label="Vrijeme prvog odgovora (sati)", value=5.2)
    col3.metric(label="Prosječno vrijeme rješavanja (sati)", value=16)

    # Osiguravanje ispravnog formata datuma za Altair graf
    graf_df = st.session_state.df.copy()
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
