import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# 1. SEITENKONFIGURATION (Vollbild & Wide)
st.set_page_config(page_title="ABUS Batteriecheck", page_icon="🔋", layout="wide")

# Vollbild-Fix & Design-Optimierung
st.markdown("""
    <meta name="apple-mobile-web-app-capable" content="yes">
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. TITEL
st.title("🔋 ABUS Batteriecheck")

# --- STABILE VERBINDUNG (Das Handy-Sicherheitsnetz) ---
def get_connection():
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except:
        time.sleep(1)
        return st.connection("gsheets", type=GSheetsConnection)

conn = get_connection()

@st.cache_data(ttl=300, show_spinner="Lade Datenbank...")
def load_data():
    return conn.read(spreadsheet=st.secrets["spreadsheet"], ttl=0)

# --- DATEN LADEN ---
try:
    df = load_data()
except Exception as e:
    st.error("Verbindung zu Google unterbrochen.")
    if st.button("🔄 Verbindung neu aufbauen"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

# --- SPALTEN-DEFINITION ---
COL_NAME = "Sender Name"
COL_ORT = "Standort"
COL_LETZTER = "Letzter Batteriewechsel"
COL_NAECHSTER = "Nächster Wechsel (geplant)"
COL_VERMERK = "Vermerke (z.B. Batterie)"
COL_STATUS = "Status"

# --- LOGIK & DATUM-REPARATUR ---
if df is not None and not df.empty and COL_NAME in df.columns:
    # Datum konvertieren
    df[COL_LETZTER] = pd.to_datetime(df[COL_LETZTER], errors='coerce').dt.date
    df[COL_NAECHSTER] = pd.to_datetime(df[COL_NAECHSTER], errors='coerce').dt.date
    
    # Automatische Ergänzung (+547 Tage)
    maske = df[COL_LETZTER].notnull() & df[COL_NAECHSTER].isnull()
    df.loc[maske, COL_NAECHSTER] = df.loc[maske, COL_LETZTER] + timedelta(days=547)
    
    df_clean = df.dropna(subset=[COL_NAME]).copy()
    df_clean = df_clean[df_clean[COL_NAME].astype(str).str.lower() != "none"]
    heute = datetime.now().date()

    # Hilfsfunktionen für Design
    def format_date(d):
        return d.strftime('%d.%m.%Y') if pd.notnull(d) and hasattr(d, 'strftime') else ""

    def style_status(row):
        n = row[COL_NAECHSTER]
        if pd.isna(n): return [''] * len(row)
        if n < heute:
            return ['background-color: #ffcccc; color: black; font-weight: bold'] * len(row)
        elif n < heute + timedelta(days=30):
            return ['background-color: #fff3cd; color: black; font-weight: bold'] * len(row)
        else:
            return ['background-color: #d4edda; color: black'] * len(row)

    # --- DASHBOARD ---
    df_aktuell_check = df_clean.sort_values(by=COL_LETZTER, ascending=False).drop_duplicates(subset=[COL_NAME])
    kritisch = len(df_aktuell_check[df_aktuell_check[COL_NAECHSTER] < heute])
    bald = len(df_aktuell_check[(df_aktuell_check[COL_NAECHSTER] >= heute) & (df_aktuell_check[COL_NAECHSTER] < heute + timedelta(days=30))])

    c1, c2, c3 = st.columns(3)
    if kritisch > 0: c1.error(f"⚠️ {kritisch} überfällig!")
    else: c1.success("✅ Alles OK")
    if bald > 0: c2.warning(f"🔔 {bald} bald fällig")
    c3.metric("Sender gesamt", len(df_aktuell_check))

    # --- EINGABEFORMULAR ---
    with st.expander("➕ Neuen Batteriewechsel registrieren"):
        with st.form("entry_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            n_in = col_a.text_input("Sender Name").strip()
            d_in = col_b.date_input("Wechseldatum", heute, format="DD.MM.YYYY")
            
            b_ort = ""
            if n_in and not df_clean.empty:
                t = df_clean[df_clean[COL_NAME].astype(str) == n_in]
                if not t.empty: b_ort = str(t.iloc[-1][COL_ORT])
            
            o_in = st.text_input("Standort", value=b_ort)
            v_in = st.text_input("Vermerke")
            
            if st.form_submit_button("Speichern"):
                if n_in:
                    naechster = d_in + timedelta(days=547)
                    new_row = pd.DataFrame([{COL_NAME: n_in, COL_ORT: o_in, COL_LETZTER: d_in, COL_NAECHSTER: naechster, COL_VERMERK: v_in, COL_STATUS: "OK"}])
                    df_final = pd.concat([df, new_row], ignore_index=True)
                    conn.update(data=df_final)
                    st.cache_data.clear()
                    st.success("Erfolgreich gespeichert!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Name fehlt!")

    # --- ANZEIGE MIT FILTER ---
    st.markdown("---")
    st.subheader("📡 Aktueller Status")
    alle_standorte = sorted(df_clean[COL_ORT].dropna().unique())
    filter_ort = st.selectbox("Standort filtern:", ["Alle"] + alle_standorte)
    
    df_view = df_aktuell_check.copy()
    if filter_ort != "Alle":
        df_view = df_view[df_view[COL_ORT] == filter_ort]

    st.dataframe(
        df_view.style.apply(style_status, axis=1).format({COL_LETZTER: format_date, COL_NAECHSTER: format_date}),
        use_container_width=True, hide_index=True
    )

    # --- HISTORIE ---
    with st.expander("🕒 Historie & Verlauf"):
        alle_sender = sorted(df_clean[COL_NAME].unique())
        f_sender = st.selectbox("Sender wählen:", ["Alle"] + alle_sender)
        df_h = df_clean.sort_values(by=COL_LETZTER, ascending=False).copy()
        if f_sender != "Alle":
            df_h = df_h[df_h[COL_NAME] == f_sender]
        
        df_h[COL_LETZTER] = df_h[COL_LETZTER].apply(format_date)
        df_h[COL_NAECHSTER] = df_h[COL_NAECHSTER].apply(format_date)
        st.table(df_h[[COL_NAME, COL_ORT, COL_LETZTER, COL_NAECHSTER, COL_VERMERK]])

    if st.button("🔄 Daten aktualisieren"):
        st.cache_data.clear()
        st.rerun()

else:
    st.info("Warte auf Daten oder Tabelle ist leer...")
