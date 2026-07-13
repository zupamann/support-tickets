import datetime
import pandas as pd
import streamlit as st
import altair as alt

# Postavke stranice
st.set_page_config(page_title="Support tickets", page_icon="🎫", layout="wide")
st.title("🎫 Support tickets")
st.write(
    """
    Ova aplikacija omogućuje upravljanje podrškom kroz 5 različitih podkategorija.
    Možete dodavati nove tikete s rokovima, uređivati postojeće unutar pripadajućih tablica i pratiti statistiku te rokove izvršenja.
    """
)

# Definiranje 5 podkategorija
KATEGORIJE = ["BEMV", "BMV", "PN", "Ostalo", "Privatno", "Logg reader"]

# Inicijalizacija praznog Dataframe-a u session state ako već ne postoji
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(
        columns=["ID", "Kategorija", "Issue", "Status", "Priority", "Datum stavljeno", "Deadline"]
    )

# --- SEKCIJA ZA DODAVANJE TIKETA ---
st.header("Dodaj novi tiket")

with st.form("add_ticket_form", clear_on_submit=True):
    issue = st.text_area("Opišite problem")
    kategorija = st.selectbox("Podkategorija", KATEGORIJE)
    priority = st.selectbox("Prioritet", ["High", "Medium", "Low"])
    
    # Odabir datuma
    datum_stavljeno = st.date_input("Datum stavljeno", datetime.date.today())
    
    # Rok (Deadline) s opcijom "Neodređeno"
    col_date, col_check = st.columns([3, 1])
    with col_date:
        deadline_date = st.date_input("Deadline", datetime.date.today() + datetime.timedelta(days=7))
    with col_check:
        st.write("") # Poravnanje
        st.write("") 
        neodredeno = st.checkbox("Neodređeno rok")
        
    submitted = st.form_submit_button("Podnesi tiket")

if submitted and issue.strip() != "":
    if len(st.session_state.df) == 0:
        next_id = 1101
    else:
        id_brojevi = st.session_state.df["ID"].apply(lambda x: int(str(x).split("-")[1]))
        next_id = max(id_brojevi) + 1

    # Definiranje vrijednosti za deadline
    final_deadline = "Neodređeno" if neodredeno else deadline_date
    
    df_new = pd.DataFrame(
        [
            {
                "ID": f"TICKET-{next_id}",
                "Kategorija": kategorija,
                "Issue": issue,
                "Status": "Open",
                "Priority": priority,
                "Datum stavljeno": datum_stavljeno,
                "Deadline": final_deadline,
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
    "Tikete možete uređivati dvostrukim klikom na ćeliju unutar pripadajuće tablice kategorije. Ovdje možete mijenjati i datume ili ručno upisati 'Neodređeno' u polje Deadline.",
    icon="✍️",
)

# Kreiranje tabova za svaku podkategoriju
tabs = st.tabs(KATEGORIJE)

# Prolazimo kroz svaki tab
for tab, kat in zip(tabs, KATEGORIJE):
    with tab:
        df_kat = st.session_state.df[st.session_state.df["Kategorija"] == kat].reset_index()
        st.write(f"Broj tiketa u ovoj kategoriji: `{len(df_kat)}`")
        
        editor_key = f"editor_{kat}"
        
        edited_kat_df = st.data_editor(
            df_kat.drop(columns=["index"]), 
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
                "Datum stavljeno": st.column_config.DateColumn(
                    "Datum stavljeno",
                    required=True,
                ),
                "Deadline": st.column_config.TextColumn(
                    "Deadline (Datum ili 'Neodređeno')",
                    required=True,
                ),
                "Kategorija": None, 
            },
            disabled=["ID"],
            key=editor_key
        )
        
        # Provjera i spremanje promjena natrag u glavni DataFrame
        if editor_key in st.session_state and st.session_state[editor_key]["edited_rows"]:
            promjene = st.session_state[editor_key]["edited_rows"]
            
            for lokalni_indeks, izmijenjene_vrijednosti in promjene.items():
                originalni_indeks = df_kat.loc[int(lokalni_indeks), "index"]
                for stupac, nova_vrijednost in izmijenjene_vrijednosti.items():
                    st.session_state.df.at[originalni_indeks, stupac] = nova_vrijednost
            
            st.rerun()


# --- NOVO: PRAĆENJE RJEŠAVANJA I ROKOVA ---
st.header("📅 Praćenje rokova i rješavanja po danima")

if len(st.session_state.df) > 0:
    # Priprema podataka za analizu datuma
    df_analiza = st.session_state.df.copy()
    
    # Pretvaramo u datum radi lakšeg grupiranja
    df_analiza["Datum stavljeno"] = pd.to_datetime(df_analiza["Datum stavljeno"]).dt.date
    
    # Prikaz broja otvorenih/zatvorenih tiketa po danu kreiranja
    st.write("##### Broj zaprimljenih tiketa po danima i njihov trenutni status")
    
    dnevni_graf = (
        alt.Chart(df_analiza)
        .mark_bar()
        .encode(
            x=alt.X("Datum stavljeno:T", title="Datum"),
            y=alt.Y("count():Q", title="Broj tiketa"),
            color="Status:N",
            tooltip=["Datum stavljeno", "Status", "count()"]
        )
        .properties(height=250)
    )
    st.altair_chart(dnevni_graf, use_container_width=True)

    # Filtriranje za tikete koji imaju stvarni rok (izbacujemo 'Neodređeno')
    df_rok = df_analiza[df_analiza["Deadline"] != "Neodređeno"].copy()
    df_rok["Deadline"] = pd.to_datetime(df_rok["Deadline"]).dt.date
    
    col_rok1, col_rok2 = st.columns(2)
    
    with col_rok1:
        st.write("##### Tiketi koji uskoro dospijevaju (Aktivni rokovi)")
        # Prikazujemo samo one koji nisu zatvoreni, a imaju rok
        aktivni_rokovi = df_rok[df_rok["Status"] != "Closed"].sort_values(by="Deadline")
        if not aktivni_rokovi.empty:
            st.dataframe(
                aktivni_rokovi[["ID", "Kategorija", "Issue", "Deadline", "Status", "Priority"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.write("Nemate aktivnih tiketa s definiranim rokovima.")

    with col_rok2:
        st.write("##### Tiketi bez određenog roka (Neodređeno)")
        neodredeni_tiketi = df_analiza[df_analiza["Deadline"] == "Neodređeno"]
        if not neodredeni_tiketi.empty:
            st.dataframe(
                neodredeni_tiketi[["ID", "Kategorija", "Issue", "Status", "Priority"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.write("Nema tiketa s neodređenim rokom.")
            
else:
    st.write("Nema unesenih tiketa za praćenje datuma.")


# --- STATISTIKA (OPĆENITI GRAFOVI) ---
st.header("Opća statistika")

if len(st.session_state.df) > 0:
    col1, col2, col3 = st.columns(3)
    num_open_tickets = len(st.session_state.df[st.session_state.df.Status == "Open"])
    col1.metric(label="Broj otvorenih tiketa", value=num_open_tickets)
    col2.metric(label="Vrijeme prvog odgovora (sati)", value=5.2)
    col3.metric(label="Prosječno vrijeme rješavanja (sati)", value=16)

    graf_df = st.session_state.df.copy()
    graf_df = graf_df.dropna(subset=["Datum stavljeno", "Status", "Priority"])
    graf_df["Datum stavljeno"] = pd.to_datetime(graf_df["Datum stavljeno"])

    st.write("")
    st.write("##### Ukupni status tiketa po mjesecima (mjesec zaprimanja)")
    status_plot = (
        alt.Chart(graf_df)
        .mark_bar()
        .encode(
            x="month(Datum stavljeno):O",
            y="count():Q",
            xOffset="Status:N",
            color="Status:N",
        )
        .configure_legend(
            orient="bottom", titleFontSize=14, labelFontSize=14, titlePadding=5
        )
    )
    st.altair_chart(status_plot, use_container_width=True, theme="streamlit")

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
