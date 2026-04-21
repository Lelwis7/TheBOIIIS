import streamlit as st
from icalendar import Calendar, Event
from datetime import datetime, time
import json
import os

# Datei für die Speicherung
DB_FILE = "events_db.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

st.title("📅 Event-Planer PRO")

# Daten laden
events = load_data()

# Eingabe-Maske in der Seitenleiste
with st.sidebar.form("event_form"):
    st.header("Neues Event")
    summary = st.text_input("Event Titel")
    date = st.date_input("Datum")
    location = st.text_input("Ort")
    description = st.text_area("Details")
    submitted = st.form_submit_button("Speichern & Kalender Sync")

if submitted:
    new_event = {
        "summary": summary,
        "date": str(date),
        "location": location,
        "description": description
    }
    events.append(new_event)
    save_data(events)
    st.success("Event gespeichert!")

# Anzeige der Events
st.header("Deine geplanten Events")
for i, ev in enumerate(events):
    with st.expander(f"{ev['date']} - {ev['summary']}"):
        st.write(f"📍 **Ort:** {ev['location']}")
        st.write(f"📝 **Infos:** {ev['description']}")