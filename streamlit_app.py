import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Seite konfigurieren
st.set_page_config(page_title="Sender-Wartung", page_icon="🔋")

st.title("🔋 Sender-Batterie-Check")

# 1. Verbindung aufbauen
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Daten lesen
df = conn.read()

# 3. Eingabeformular
with st.form("entry_form"):
    st.write("Neuen Batteriewechsel registrieren:")
    sender = st.text_input("Name des Senders")
    ort = st.text_input("Standort")
    datum = st.date_input("Wechseldatum")
    notiz = st.text_input("Bemerkung (z.B. Batterietyp)")
    
    submit = st.form_submit_button("In Tabelle speichern")

    if submit:
        if sender and ort:
            # Neue Zeile vorbereiten
            new_row = pd.DataFrame([{
                "Sender Name": sender,
                "Standort": ort,
                "Letzter Batteriewechsel": str(datum),
                "Nächster Wechsel (geplant)": notiz
            }])
            
            # Daten zusammenführen
            updated_df = pd.concat([df, new_row], ignore_index=True)
            
            # Speichern versuchen
            try:
                conn.update(data=updated_df)
                st.success(f"✅ Gespeichert: {sender} am {datum}")
                st.balloons()
            except Exception as e:
                st.error("⚠️ Fehler beim Schreiben in Google Sheets.")
                st.info("Bitte prüfe, ob die Tabelle für 'Jeden mit Link' als 'Mitbearbeiter' freigegeben ist.")
        else:
            st.warning("Bitte fülle mindestens 'Name' und 'Standort' aus.")

# 4. Tabelle anzeigen
st.subheader("Aktuelle Wartungsliste")
st.dataframe(df)
