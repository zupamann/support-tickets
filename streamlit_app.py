import datetime
import pandas as pd
import streamlit as st
import altair as alt
import requests
import json

# Postavke stranice
st.set_page_config(page_title="Support tickets", page_icon="🎫", layout="wide")
st.title("🎫 Support tickets")
st.write(
    """
    Ova aplikacija omogućuje upravljanje podrškom kroz 5 različitih podkategorija.
    Podaci se trajno i automatski spremaju u vašu **Google Tablicu** u realnom vremenu!
    """
)

# --- POSTAVKE GOOGLE SHEETS VEZE ---
SHEET_ID = "1LiC2lADL7cw4NULG058ne3XAodL6Mc0gxQcIhGNWr6g"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyVhadipAuP71cUw_e7Xb2eA5pli_6RIa_sd9KoLYqeGwwvPlSvFAzU5_7TCjve-4nUgg/exec"

KATEGORIJE = ["BEMV", "BMV", "PN", "Ostalo", "Privatno", "Logg reader"]
STUPCI = ["ID", "Kategorija", "Issue", "Status", "Priority", "Datum stavljeno", "Deadline"]

# --- FUNKCIJE ZA UPRAVLJANJE BAZOM ---
@st.cache_data(ttl=2)
def ucitaj_podatke():
    """Učitava podatke izravno iz Google Sheets CSV izvoza."""
    try:
        df = pd.read_csv(CSV_URL, dtype=str)
        # Popunjavanje stupaca ako neki nedostaje
        for col in STUPCI:
            if col not in df.columns:
                df[col] = ""
        # Filtriramo prazne redove
        df = df.dropna(subset=["ID"])
        df = df[df["ID"].astype(str).str.strip() != ""]
        return df[STUPCI].reset_index(drop=True)
    except Exception as e:
        st.error(f"Greška prilikom učitavanja s Google Sheets: {e}")
        return pd.DataFrame(columns=STUPCI).astype(str)

def spremi_podatke_u_sheets(df):
    """Sprema cijeli DataFrame natrag u Google Sheets preko tvoje Web aplikacije."""
    try:
        # Pretvaramo DataFrame u JSON format spreman za slanje
        df_clean = df.fillna("")
        podaci_json = df_clean.to_dict(orient="records")
        
        # Slanje POST zahtjeva tvojoj Google skripti
        response = requests.post(
            APPS_SCRIPT_URL, 
            data=json.dumps(podaci_json), 
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            # Brišemo predmemoriju (cache) kako bi iduće učitavanje povuklo svježe stanje
            ucitaj_podatke.clear()
            return True
        else:
            st.error(f"Google Sheets je vratio grešku: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Nije uspjelo povezivanje s Google skriptom: {e}")
        return False

# Inicijalizacija session state-a pri prvom pokretanju ili na klik gumba
if "df" not in st.session_state or st.button("🔄 Osvježi podatke iz Google Tablice"):
    st.session_state.df = ucitaj_podatke()

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
    ).astype(str)

    # Spajamo novi tiket na vrh lokalne tablice i šaljemo na Google Sheets
    privremeni_df = pd.concat([df_new, st.session_state.df], axis=0).reset_index(drop=True)
    
    with st.spinner("Spremanje u Google Tablicu..."):
        if spremi_podatke_u_sheets(privremeni_df):
            st.session_state.df = privremeni_df
            st.success(f"Tiket uspješno dodan u kategoriju {kategorija} i spremljen na Google Sheets!")
            st.rerun()
elif submitted and issue.strip() == "":
    st.error("Molimo unesite opis problema prije slanja.")


# --- SEKCIJA ZA PRIKAZ I UREĐIVANJE PO KATEGORIJAMA ---
st.header("Postojeći tiketi")
st.write(f"Ukupan broj tiketa u sustavu: `{len(st.session_state.df)}`")

st.info(
    "Uredite podatke dvostrukim klikom na ćeliju. Promjene se automatski sinkroniziraju s vašim Google Sheets računom.",
    icon="✍️",
)

tabs = st.tabs(KATEGORIJE)

for tab, kat in zip(tabs, KATEGORIJE):
    with tab:
        df_kat = st.session_state.df[st.session_state.df["Kategorija"] == kat]
        st.write(f"Broj tiketa u ovoj kategoriji: `{len(df_kat)}`")
        
        df_prikaz = df_kat.drop(columns=["Kategorija"]).reset_index(drop=True).astype(str)
        
        editor_key = f"editor_{kat}"
        
        edited_df = st.data_editor(
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
            key=editor_key
        )
        
        # Slušamo promjene na data_editoru i šaljemo ih na Google Sheets
        if editor_key in st.session_state and "edited_rows" in st.session_state[editor_key]:
            promjene = st.session_state[editor_key]["edited_rows"]
            if promjene:
                kopija_df = st.session_state.df.copy()
                for lokalni_indeks_str, stavke in promjene.items():
                    lokalni_idx = int(lokalni_indeks_str)
                    pravi_idx = df_kat.index[lokalni_idx]
                    
                    for stupac, nova_vrijednost in stavke.items():
                        kopija_df.at[pravi_idx, stupac] = str(nova_vrijednost)
                
                with st.spinner("Ažuriranje Google Tablice..."):
                    if spremi_podatke_u_sheets(kopija_df):
                        st.session_state.df = kopija_df
                        st.rerun()


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
