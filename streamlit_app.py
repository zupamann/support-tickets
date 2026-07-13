import datetime
import os
import pandas as pd
import streamlit as st
import altair as alt

# Postavke stranice
st.set_page_config(page_title="Support tickets", page_icon="🎫", layout="wide")
st.title("🎫 Support tickets")
st.write(
    """
    Ova aplikacija omogućuje upravljanje podrškom kroz 5 različitih podkategorija.
    Podaci se trajno spremaju u lokalnu bazu pa nećete izgubiti tikete nakon osvežavanja stranice.
    """
)

DB_FILE = "tickets_db.csv"
KATEGORIJE = ["BEMV", "BMV", "PN", "Ostalo", "Privatno","Logg reader"]

# --- FUNKCIJE ZA UPRAVLJANJE BAZOM ---
def ucitaj_podatke():
    """Učitava podatke iz CSV datoteke ako postoji, inače stvara prazan DataFrame."""
    def_cols = ["ID", "Kategorija", "Issue", "Status", "Priority", "Datum stavljeno", "Deadline"]
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE, dtype=str)
            # Osiguraj da imamo sve potrebne stupce
            for col in def_cols:
                if col not in df.columns:
                    df[col] = ""
            return df[def_cols]
        except Exception:
            pass
            
    return pd.DataFrame(columns=def_cols)

def spremi_podatke(df):
    """Sprema trenutni DataFrame natrag u CSV datoteku."""
    df.to_csv(DB_FILE, index=False)

# Inicijalizacija u session state na samom početku
if "df" not in st.session_state:
    st.session_state.df = ucitaj_podatke()

# --- CALLBACK FUNKCIJA ZA SIGURNO SPREMANJE PROMJENA ---
def spremi_promjene_iz_tablice(kat_ime):
    """Službena Streamlit metoda za spremanje promjena iz data_editora bez rušenja aplikacije."""
    editor_key = f"editor_{kat_ime}"
    
    if editor_key in st.session_state:
        promjene = st.session_state[editor_key].get("edited_rows", {})
        if promjene:
            # Filtriramo točnu kategoriju kako bismo znali prave indekse
            df_kat = st.session_state.df[st.session_state.df["Kategorija"] == kat_ime]
            
            for lokalni_indeks_str, izmjene in promjene.items():
                lokalni_indeks = int(lokalni_indeks_str)
                # Pronalazimo stvarni indeks u glavnoj tablici
                pravi_indeks = df_kat.index[lokalni_indeks]
                
                for stupac, nova_vrijednost in izmjene.items():
                    st.session_state.df.at[pravi_indeks, stupac] = nova_vrijednost
            
            # Trajno zapiši na disk
            spremi_podatke(st.session_state.df)

# --- SEKCIJA ZA DODAVANJE TIKETA ---
st.header("Dodaj novi tiket")

with st.form("add_ticket_form", clear_on_submit=True):
    issue = st.text_area("Opišite problem")
    kategorija = st.selectbox("Podkategorija", KATEGORIJE)
    priority = st.selectbox("Prioritet", ["High", "Medium", "Low"])
    
    datum_stavljeno = st.date_input("Datum stavljeno", datetime.date.today())
    
    col_date, col_check = st.columns([3, 1])
    with col_date:
        deadline_date = st.date_input("Deadline", datetime.date.today() + datetime.timedelta(days=7))
    with col_check:
        st.write("") 
        st.write("") 
        neodredeno = st.checkbox("Neodređeno rok")
        
    submitted = st.form_submit_button("Podnesi tiket")

if submitted and issue.strip() != "":
    if len(st.session_state.df) == 0:
        next_id = 1101
    else:
        id_brojevi = st.session_state.df["ID"].dropna().apply(lambda x: int(str(x).split("-")[1]) if "-" in str(x) else 1100)
        next_id = max(id_brojevi) + 1 if len(id_brojevi) > 0 else 1101

    final_deadline = "Neodređeno" if neodredeno else deadline_date.strftime("%Y-%m-%d")
    str_datum_stavljeno = datum_stavljeno.strftime("%Y-%m-%d")
    
    df_new = pd.DataFrame(
        [
            {
                "ID": f"TICKET-{next_id}",
                "Kategorija": kategorija,
                "Issue": issue,
                "Status": "Open",
                "Priority": priority,
                "Datum stavljeno": str_datum_stavljeno,
                "Deadline": final_deadline,
            }
        ]
    )

    st.session_state.df = pd.concat([df_new, st.session_state.df], axis=0).reset_index(drop=True)
    spremi_podatke(st.session_state.df)
    st.success(f"Tiket uspješno dodan u kategoriju {kategorija}!")
elif submitted and issue.strip() == "":
    st.error("Molimo unesite opis problema prije slanja.")


# --- SEKCIJA ZA PRIKAZ I UREĐIVANJE PO KATEGORIJAMA ---
st.header("Postojeći tiketi")
st.write(f"Ukupan broj tiketa u sustavu: `{len(st.session_state.df)}`")

st.info(
    "Tikete možete uređivati dvostrukim klikom na ćeliju. Promjene se automatski spremaju čim kliknete izvan ćelije.",
    icon="✍️",
)

tabs = st.tabs(KATEGORIJE)

for tab, kat in zip(tabs, KATEGORIJE):
    with tab:
        df_kat = st.session_state.df[st.session_state.df["Kategorija"] == kat].copy()
        st.write(f"Broj tiketa u ovoj kategoriji: `{len(df_kat)}`")
        
        # Priprema čistog prikaza (resetiramo indeks na 0,1,2... unutar taba radi lakšeg praćenja)
        df_prikaz = df_kat.drop(columns=["Kategorija"]).reset_index(drop=True)
        df_prikaz["Datum stavljeno"] = df_prikaz["Datum stavljeno"].astype(str)
        df_prikaz["Deadline"] = df_prikaz["Deadline"].astype(str)
        
        # Ovdje koristimo on_change poziv koji rješava problem rušenja aplikacije
        st.data_editor(
            df_prikaz, 
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.SelectboxColumn("Status", options=["Open", "In Progress", "Closed"], required=True),
                "Priority": st.column_config.SelectboxColumn("Priority", options=["High", "Medium", "Low"], required=True),
                "Datum stavljeno": st.column_config.TextColumn("Datum stavljeno (GGGG-MM-DD)", required=True),
                "Deadline": st.column_config.TextColumn("Deadline (Datum ili 'Neodređeno')", required=True),
            },
            disabled=["ID"],
            key=f"editor_{kat}",
            on_change=spremi_promjene_iz_tablice,
            args=(kat,)
        )


# --- PRAĆENJE RJEŠAVANJA I ROKOVA ---
st.header("📅 Praćenje rokova i rješavanja po danima")

if len(st.session_state.df) > 0:
    df_analiza = st.session_state.df.copy()
    df_analiza["Datum stavljeno"] = pd.to_datetime(df_analiza["Datum stavljeno"], errors='coerce').dt.date
    df_analiza = df_analiza.dropna(subset=["Datum stavljeno"])
    
    if not df_analiza.empty:
        st.write("##### Broj zaprimljenih tiketa po danima i njihov trenutni status")
        dnevni_graf = (
            alt.Chart(df_analiza).mark_bar().encode(
                x=alt.X("Datum stavljeno:T", title="Datum"),
                y=alt.Y("count():Q", title="Broj tiketa"),
                color="Status:N",
                tooltip=["Datum stavljeno", "Status", "count()"]
            ).properties(height=250)
        )
        st.altair_chart(dnevni_graf, use_container_width=True)
    else:
        st.write("Nema ispravnih datuma za prikaz grafikona.")

    df_rok = df_analiza[df_analiza["Deadline"] != "Neodređeno"].copy()
    df_rok["Deadline"] = pd.to_datetime(df_rok["Deadline"], errors='coerce').dt.date
    df_rok = df_rok.dropna(subset=["Deadline"])
    
    col_rok1, col_rok2 = st.columns(2)
    
    with col_rok1:
        st.write("##### Tiketi koji uskoro dospijevaju (Aktivni rokovi)")
        aktivni_rokovi = df_rok[df_rok["Status"] != "Closed"].sort_values(by="Deadline")
        if not aktivni_rokovi.empty:
            st.dataframe(aktivni_rokovi[["ID", "Issue", "Deadline", "Status", "Priority"]], use_container_width=True, hide_index=True)
        else:
            st.write("Nemate aktivnih tiketa s definiranim rokovima.")

    with col_rok2:
        st.write("##### Tiketi bez određenog roka (Neodređeno)")
        neodredeni_tiketi = st.session_state.df[st.session_state.df["Deadline"] == "Neodređeno"]
        if not neodredeni_tiketi.empty:
            st.dataframe(neodredeni_tiketi[["ID", "Kategorija", "Issue", "Status", "Priority"]], use_container_width=True, hide_index=True)
        else:
            st.write("Nema tiketa s neodređenim rokom.")
            
else:
    st.write("Nema unesenih tiketa za praćenje datuma.")


# --- STATISTIKA ---
st.header("Opća statistika")

if len(st.session_state.df) > 0:
    col1, col2, col3 = st.columns(3)
    num_open_tickets = len(st.session_state.df[st.session_state.df.Status == "Open"])
    col1.metric(label="Broj otvorenih tiketa", value=num_open_tickets)
    col2.metric(label="Vrijeme prvog odgovora (sati)", value=5.2)
    col3.metric(label="Prosječno vrijeme rješavanja (sati)", value=16)

    graf_df = st.session_state.df.copy()
    graf_df["Datum stavljeno"] = pd.to_datetime(graf_df["Datum stavljeno"], errors='coerce')
    graf_df = graf_df.dropna(subset=["Datum stavljeno", "Status", "Priority"])

    if not graf_df.empty:
        st.write("")
        st.write("##### Ukupni status tiketa po mjesecima (mjesec zaprimanja)")
        status_plot = (
            alt.Chart(graf_df).mark_bar().encode(
                x="month(Datum stavljeno):O",
                y="count():Q",
                xOffset="Status:N",
                color="Status:N",
            ).configure_legend(orient="bottom", titleFontSize=14, labelFontSize=14, titlePadding=5)
        )
        st.altair_chart(status_plot, use_container_width=True, theme="streamlit")

        st.write("##### Trenutni prioriteti tiketa")
        priority_plot = (
            alt.Chart(graf_df).mark_arc().encode(theta="count():Q", color="Priority:N").properties(height=300)
            .configure_legend(orient="bottom", titleFontSize=14, labelFontSize=14, titlePadding=5)
        )
        st.altair_chart(priority_plot, use_container_width=True, theme="streamlit")
else:
    st.write("Trenutno nema podataka za prikaz statistike.")
