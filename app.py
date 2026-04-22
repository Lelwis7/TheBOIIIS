import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
from datetime import datetime

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="The BOIIIS App", page_icon="📅")

# --- VERBINDUNG ZUM GOOGLE SHEET ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- LOGIN BEREICH (SIDEBAR) ---
with st.sidebar:
    st.header("🔐 Login")
    password = st.text_input("Passwort eingeben", type="password")
    st.info("Admin-Bereich für Event-Planung und Bearbeitung.")

# --- HEADER & DEZENTES ABO (OBEN RECHTS) ---
col_title, col_abo = st.columns([2, 1])

with col_title:
    st.title("📅 Unsere Events")

with col_abo:
    ical_link = "https://calendar.google.com/calendar/ical/8d035138c79ebce46d9e4c5899614c429cc1044c3c223349dcb885b24c8d12b2%40group.calendar.google.com/private-1600c31d25ba8c5a8127559dd4501184/basic.ics"
    webcal_link = ical_link.replace("https://", "webcal://")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<p style="font-size: 1.1rem; margin-bottom: 5px; white-space: nowrap; font-weight: bold;">Kalenderabo <span title="iPhone: Apple Abo klicken. Android: Link kopieren & im Chrome Desktop-Modus öffnen.">ℹ️</span></p>', unsafe_allow_html=True)
        st.link_button("🍎", webcal_link, use_container_width=True)
    with c2:
        st.markdown('<p style="font-size: 1.1rem; margin-bottom: 5px;">&nbsp;</p>', unsafe_allow_html=True)
        google_url = f"https://www.google.com/calendar/render?cid={urllib.parse.quote(ical_link)}"
        st.link_button("🌐", google_url, use_container_width=True)

st.write("---")

# --- NEUES EVENT ERSTELLEN (NUR MIT PASSWORT) ---
if password == "1404":
    with st.expander("➕ Neues Event planen"):
        with st.form("event_form"):
            summary = st.text_input("Was steht an?")
            date_range = st.date_input("Zeitraum (Start und Ende wählen)", value=[datetime.now(), datetime.now()])
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                use_start = st.checkbox("Startzeit berücksichtigen?")
                start_val = st.time_input("Von", value=datetime.strptime("12:00", "%H:%M"))
            with col_t2:
                use_end = st.checkbox("Endzeit berücksichtigen?")
                end_val = st.time_input("Bis", value=datetime.strptime("14:00", "%H:%M"))
            
            location = st.text_input("Wo?")
            description = st.text_area("Infos")
            submit = st.form_submit_button("Event offiziell planen")
            
            if submit:
                d_start = date_range[0]
                d_end = date_range[1] if len(date_range) > 1 else d_start
                display_date = d_start.strftime('%d.%m.%Y')
                if d_start != d_end:
                    display_date += f" - {d_end.strftime('%d.%m.%Y')}"
                
                t_start_sheet = start_val.strftime("%H:%M") if use_start else ""
                t_end_sheet = end_val.strftime("%H:%M") if use_end else ""
                
                df_current = conn.read(worksheet="events", ttl=0)
                new_row = pd.DataFrame([{
                    "summary": summary,
                    "date": display_date,
                    "location": location,
                    "description": description,
                    "start_time": t_start_sheet,
                    "end_time": t_end_sheet
                }])
                updated_df = pd.concat([df_current, new_row], ignore_index=True)
                conn.update(worksheet="events", data=updated_df)
                st.success("Event gespeichert!")
                st.rerun()

# --- EVENT LISTE ANZEIGEN ---
try:
    df = conn.read(worksheet="events", ttl=0)
    df = df.fillna("") 
    participants_df = conn.read(worksheet="participants", ttl=0)
    participants_df = participants_df.fillna("")

    if not df.empty:
        # Wir loopen über den Index, um gezielt löschen zu können
        for i in reversed(df.index):
            row = df.loc[i]
            event_name = str(row['summary'])
            event_date = str(row['date'])
            event_loc = str(row['location'])
            event_desc = str(row['description'])
            s_time = str(row.get('start_time', ""))
            e_time = str(row.get('end_time', ""))
            
            time_title = ""
            if s_time and s_time != "" and "(" not in event_date:
                if e_time and e_time != "":
                    time_title = f" ({s_time} - {e_time} Uhr)"
                else:
                    time_title = f" (ab {s_time} Uhr)"
            
            with st.expander(f"🗓️ {event_date}{time_title} - {event_name}"):
                col_info, col_btns = st.columns([3, 1])
                with col_info:
                    st.write(f"📍 **Ort:** {event_loc}")
                    st.info(f"💬 **Infos:** {event_desc}")
                
                if password == "1404":
                    with col_btns:
                        st.write("🛠️ **Admin**")
                        
                        # --- BEARBEITEN BUTTON ---
                        if st.button("✏️ Bearbeiten", key=f"edit_btn_{i}", use_container_width=True):
                            st.session_state[f"edit_mode_{i}"] = True

                        # --- LÖSCHEN BUTTON ---
                        if st.button("🗑️ Löschen", key=f"del_btn_{i}", use_container_width=True):
                            st.session_state[f"del_mode_{i}"] = True

                        # --- LÖSCHEN BESTÄTIGUNG ---
                        if st.session_state.get(f"del_mode_{i}", False):
                            st.warning("Wirklich löschen?")
                            c_del_yes, c_del_no = st.columns(2)
                            with c_del_yes:
                                if st.button("Ja", key=f"conf_del_{i}", use_container_width=True):
                                    # Zeile aus dem DataFrame entfernen
                                    df_dropped = df.drop(i)
                                    conn.update(worksheet="events", data=df_dropped)
                                    # Optional: Auch Teilnehmer für dieses Event löschen
                                    p_dropped = participants_df[participants_df['event'] != event_name]
                                    conn.update(worksheet="participants", data=p_dropped)
                                    
                                    st.success("Gelöscht!")
                                    st.session_state[f"del_mode_{i}"] = False
                                    st.rerun()
                            with c_del_no:
                                if st.button("Nein", key=f"canc_del_{i}", use_container_width=True):
                                    st.session_state[f"del_mode_{i}"] = False
                                    st.rerun()

                        # --- BEARBEITEN FORMULAR ---
                        if st.session_state.get(f"edit_mode_{i}", False):
                            with st.form(f"edit_form_{i}"):
                                edit_summary = st.text_input("Titel", value=event_name)
                                edit_date = st.text_input("Datum", value=event_date)
                                edit_loc = st.text_input("Ort", value=event_loc)
                                edit_desc = st.text_area("Infos", value=event_desc)
                                edit_start_t = st.text_input("Startzeit", value=s_time)
                                edit_end_t = st.text_input("Endzeit", value=e_time)
                                
                                c_save, c_cancel = st.columns(2)
                                with c_save:
                                    if st.form_submit_button("Speichern"):
                                        df.at[i, 'summary'] = edit_summary
                                        df.at[i, 'date'] = edit_date
                                        df.at[i, 'location'] = edit_loc
                                        df.at[i, 'description'] = edit_desc
                                        df.at[i, 'start_time'] = edit_start_t
                                        df.at[i, 'end_time'] = edit_end_t
                                        conn.update(worksheet="events", data=df)
                                        st.session_state[f"edit_mode_{i}"] = False
                                        st.rerun()
                                with c_cancel:
                                    if st.form_submit_button("Abbrechen"):
                                        st.session_state[f"edit_mode_{i}"] = False
                                        st.rerun()

                st.write("---")
                st.subheader("👥 Wer ist am Start?")
                n_input = st.text_input("Dein Name", key=f"name_{i}")
                if st.button("Ich bin dabei! ✅", key=f"join_{i}"):
                    if n_input:
                        new_p = pd.DataFrame([{"event": event_name, "name": n_input}])
                        updated_p = pd.concat([participants_df, new_p], ignore_index=True)
                        conn.update(worksheet="participants", data=updated_p)
                        st.success(f"Sauber {n_input}!")
                        st.rerun()

                curr_p = participants_df[participants_df['event'] == event_name]
                if not curr_p.empty:
                    names_list = [str(n) for n in curr_p['name'].tolist() if n != ""]
                    st.write(f"🔥 **Dabei sind:** {', '.join(names_list)}")
                else:
                    st.write("🏃 Noch niemand dabei.")

    else:
        st.write("Keine Events geplant.")
except Exception as e:
    st.error(f"Fehler: {e}")
