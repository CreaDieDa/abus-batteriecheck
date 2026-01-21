import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Seite konfigurieren
st.set_page_config(page_title="Sender-Batterie-Check", page_icon="🔋")

st.title("🔋 Sender-Batterie-Check")

# 1. Verbindung zur Google Tabelle
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Daten einlesen
df = conn.read()

# Definieren der Spaltennamen (Exakt wie in deiner Tabelle)
COL_NAME = "Name"
COL_ORT = "Standort"
COL_LETZTER = "Letzter Batteriewechsel"
COL_NAECHSTER = "Nächster Wechsel (geplant)"
COL_STATUS = "Status"

# Struktur prüfen/erstellen falls Tabelle leer ist
if df.empty:
    df = pd.DataFrame(columns=[COL_NAME, COL_ORT, COL_LETZTER, COL_NAECHSTER, COL_STATUS])

# Datumsformate bereinigen (verhindert Fehler bei leeren Zellen)
df[COL_LETZTER] = pd.to_datetime(df[COL_LETZTER], errors='coerce').dt.date
df[COL_NAECHSTER] = pd.to_datetime(df[COL_NAECHSTER], errors='coerce').dt.date

# --- FUNKTION: FARBLOGIK ---
def style_status(row):
    heute = datetime.now().date()
    naechster = row[COL_NAECHSTER]
    
    if pd.isna(naechster):
        return [''] * len(row)
    
    if naechster < heute:
        return ['background-color: #ffcccc'] * len(row) # Rot: Überfällig
    elif naechster < heute + timedelta(days=30):
        return ['background-color: #fff3cd'] * len(row) # Gelb: < 30 Tage
    else:
        return ['background-color: #d4edda'] * len(row) # Grün: OK

# --- EINGABEFORMULAR ---
with st.expander("➕ Neuen Batteriewechsel registrieren", expanded=True):
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name_input = col1.text_input("Name des Senders (z.B. Sender 01)")
        standort_input = col2.text_input("Standort (z.B. Wohnzimmer)")
        submit = st.form_submit_button("Wechsel speichern (Avis: 18 Monate)")

        if submit and name_input and standort_input:
            heute = datetime.now().date()
            naechster_avis = heute + timedelta(days=547) # 18 Monate
            
            new_row = pd.DataFrame([{
                COL_NAME: name_input, 
                COL_ORT: standort_input, 
                COL_LETZTER: heute, 
                COL_NAECHSTER: naechster_avis, 
                COL_STATUS: "OK"
            }])
            
            df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=df)
            st.success(f"Gespeichert! Nächster Wechsel für {name_input}: {naechster_avis.strftime('%d.%m.%Y')}")
            st.rerun()

# --- HAUPTANZEIGE: AKTUELLER STATUS ---
st.subheader("📡 Aktueller Batteriestatus")
if not df.empty:
    # Nur den jeweils NEUESTEN Eintrag pro Sender anzeigen (nach Datum sortiert)
    df_aktuell = df.sort_values(by=COL_LETZTER, ascending=False).drop_duplicates(subset=[COL_NAME])
    # Sortieren nach Fälligkeit
    df_aktuell = df_aktuell.sort_values(by=COL_NAECHSTER, ascending=True)
    
    st.dataframe(
        df_aktuell.style.apply(style_status, axis=1),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Noch keine Daten vorhanden.")

# --- HISTORIE: ALLE WECHSEL ---
if not df.empty:
    st.markdown("---")
    st.subheader("🕒 Historie & Verlauf")
    
    # Auswahlbox für alle vorhandenen Sender
    alle_sender = sorted(df[COL_NAME].unique())
    auswahl = st.selectbox("Verlauf für einen bestimmten Sender anzeigen:", ["Alle anzeigen"] + alle_sender)
    
    if auswahl == "Alle anzeigen":
        df_hist = df.sort_values(by=COL_LETZTER, ascending=False)
    else:
        df_hist = df[df[COL_NAME] == auswahl].sort_values(by=COL_LETZTER, ascending=False)
    
    st.write(f"Anzahl der Einträge: {len(df_hist)}")
    st.table(df_hist[[COL_LETZTER, COL_NAME, COL_ORT, COL_NAECHSTER]])

st.info("💡 Rot = Überfällig | Gelb = Fällig in < 30 Tagen | Grün = Alles OK")
