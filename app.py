import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Verbindung zum Google Sheet
conn = st.connection("gsheets", type=GSheetsConnection)

# Seite konfigurieren
st.set_page_config(page_title="Event-Planer Pro", layout="wide")

# Passwort-Abfrage in der Seitenleiste
st.sidebar.title("🔐 Login")
password = st.sidebar.text_input("Passwort eingeben", type="password")

# Dein geheimes Planer-Passwort
PLANER_PASSWORD = "1404" # Das kannst du hier ändern

# Daten laden
df = conn.read(worksheet="events")

# --- HAUPTBEREICH (Besucher-Oberfläche) ---
st.title("📅 Unsere Events")
st.write("Hier findest du alle aktuellen Planungen. Klicke auf ein Event für Details.")

if not df.empty:
    for i, row in df.iterrows():
        with st.expander(f"🗓️ {row['date']} - {row['summary']}"):
            st.write(f"📍 **Ort:** {row['location']}")
            st.info(f"💬 **Infos:** {row['description']}")
            # Hier könnten wir später den "Beitreten"-Button einbauen
else:
    st.info("Momentan sind keine Events geplant. Frag deinen Planer!")

# --- PLANER-BEREICH (Nur sichtbar mit Passwort) ---
if password == PLANER_PASSWORD:
    st.sidebar.success("Willkommen zurück, Planer!")
    st.sidebar.divider()
    
    with st.sidebar.form("planer_form"):
        st.header("🛠️ Admin-Bereich")
        summary = st.text_input("Neues Event")
        date = st.date_input("Datum")
        location = st.text_input("Ort")
        description = st.text_area("Details & Budget")
        
        submitted = st.form_submit_button("Event offiziell planen")
        
    if submitted:
        new_data = pd.DataFrame([{
            "summary": summary, 
            "date": str(date), 
            "location": location, 
            "description": description
        }])
        updated_df = pd.concat([df, new_data], ignore_index=True)
        conn.update(worksheet="events", data=updated_df)
        st.sidebar.balloons()
        st.rerun()
else:
    if password != "":
        st.sidebar.error("Falsches Passwort!")
    st.sidebar.info("Gib das Passwort ein, um neue Events zu erstellen.")