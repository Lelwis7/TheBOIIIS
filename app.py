import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
from datetime import datetime

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="The BOIIIS App", page_icon="📅")

# --- VERBINDUNG ZUM GOOGLE SHEET ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- NAVIGATION & LOGIN (SIDEBAR) ---
with st.sidebar:
    st.title("📌 Menü")
    # Hier kannst du später weitere Seiten hinzufügen
    page = st.radio("Gehe zu:", ["🗓️ Events"]) 
    st.write("---")
    st.header("🔐 Admin-Login")
    password = st.text_input("Passwort eingeben", type="password")
    st.info("Logge dich ein, um Events zu planen, zu bearbeiten oder zu löschen.")

# --- HEADER & ABO-BUTTONS ---
col_title, col_abo = st.columns([2, 1])

with col_title:
    st.title("📅 Unsere Events")

with col_abo:
    ical_link = "https://calendar.google.com/calendar/ical/8d035138c79ebce46d9e4c5899614c429cc1044c3c223349dcb885b24c8d12b2%40group.calendar.google.com/private-1600c31d25ba8c5a8127559dd4501184/basic.ics"
    webcal_link = ical_link.replace("https://", "webcal://")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<p style="font-size: 1.1rem; margin-bottom: 5px; white-space: nowrap; font-weight: bold;">Abo <span title="iPhone: Apple klicken. Android: Link kopieren & im Chrome Desktop-Modus öffnen.">ℹ️</span></p>', unsafe_allow_html=True)
        st.link_button("🍎", webcal_link, use_container_width=True)
    with c2:
        st.markdown('<p style="font-size: 1.1rem; margin-bottom: 5px;">&nbsp;</p>', unsafe_allow_html=True)
        google_url = f"https://www.google.com/calendar/render?cid={urllib.parse.quote(ical_link)}"
        st.link_button("🌐", google_url, use_container_width=True)

st.write("---")

# --- NEUES EVENT ERSTELLEN (NUR ADMIN) ---
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
        for i in reversed(df.index):
            row = df.loc[i]
            event_name = str(row['summary'])
            event_date = str(row['date'])
            event_loc = str(row['location'])
            event_desc = str(row['description'])
            s_time = str(row.get('start_time', ""))
            e_time = str(row.get('end_time', ""))
            
            # Uhrzeit-Anzeige Logik für den Titel
            time_title = ""
            if s_time and s_time != "" and "(" not in event_date:
                if e_time and e_time != "":
                    time_title = f" ({s_time} - {e_time} Uhr)"
                else:
                    time_title = f" (ab {s_time} Uhr)"
            
            with st.expander(f"🗓️ {event_date}{time_title} - {event_name}"):
                col_info, col_btns = st.columns([3, 1.2])
                with col_info:
                    st.write(f"📍 **Ort:** {event_loc}")
                    st.info(f"💬 **Infos:** {event_desc}")
                
                # ADMIN BEREICH
                if password == "1404":
                    with col_btns:
                        st.write("🛠️ **Admin**")
                        try:
                            # Datum für Links vorbereiten
                            raw_date = event_date.split(" - ")[0].strip()
                            clean_date = datetime.strptime(raw_date, "%d.%m.%Y").strftime("%Y%m%d")
                            
                            t_str = ""
                            if s_time and s_time != "":
                                s_t = s_time.replace(":", "").strip()
                                e_t = e_time.replace(":", "").strip() if e_time != "" else s_t
                                t_str = f"T{s_t}00/T{e_t}00"
                            else:
                                t_str = f"/{clean_date}"
                            
                            g_url = f"https://www.google.com/calendar/render?action=TEMPLATE&text={urllib.parse.quote(event_name)}&dates={clean_date}{t_str}&details={urllib.parse.quote(event_desc)}&location={urllib.parse.quote(event_loc)}"
                            st.link_button("🌐 Google", g_url, use_container_width=True)
                            
                            ics_content = f"BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nSUMMARY:{event_name}\nDTSTART;VALUE=DATE:{clean_date}\nDTEND;VALUE=DATE:{clean_date}\nLOCATION:{event_loc}\nDESCRIPTION:{event_desc}\nEND:VEVENT\nEND:VCALENDAR"
                            st.download_button("🍎 Apple", ics_content, file_name=f"{event_name}.ics", mime="text/calendar", use_container_width=True, key=f"ics_{i}")
                        except:
                            st.error("Kalender-Link Fehler")

                        if st.button("✏️ Bearbeiten", key=f"edit_btn_{i}", use_container_width=True):
                            st.session_state[f"edit_mode_{i}"] = True

                        if st.button("🗑️ Löschen", key=f"del_btn_{i}", use_container_width=True):
                            st.session_state[f"del_mode_{i}"] = True

                        # Lösch-Bestätigung
                        if st.session_state.get(f"del_mode_{i}", False):
                            st.warning("Wirklich löschen?")
                            c_y, c_n = st.columns(2)
                            with c_y:
                                if st.button("Ja", key=f"y_{i}"):
                                    df_new = df.drop(i)
                                    conn.update(worksheet="events", data=df_new)
                                    st.session_state[f"del_mode_{i}"] = False
                                    st.rerun()
                            with c_n:
                                if st.button("Nein", key=f"n_{i}"):
                                    st.session_state[f"del_mode_{i}"] = False
                                    st.rerun()

                        # Bearbeiten Formular
                        if st.session_state.get(f"edit_mode_{i}", False):
                            with st.form(f"edit_f_{i}"):
                                e_sum = st.text_input("Titel", value=event_name)
                                e_dat = st.text_input("Datum", value=event_date)
                                e_loc = st.text_input("Ort", value=event_loc)
                                e_des = st.text_area("Infos", value=event_desc)
                                e_sta = st.text_input("Start", value=s_time)
                                e_end = st.text_input("Ende", value=e_time)
                                if st.form_submit_button("Speichern"):
                                    df.at[i, 'summary'] = e_sum
                                    df.at[i, 'date'] = e_dat
                                    df.at[i, 'location'] = e_loc
                                    df.at[i, 'description'] = e_des
                                    df.at[i, 'start_time'] = e_sta
                                    df.at[i, 'end_time'] = e_end
                                    conn.update(worksheet="events", data=df)
                                    st.session_state[f"edit_mode_{i}"] = False
                                    st.rerun()

                st.write("---")
                st.subheader("👥 Wer ist am Start?")
                n_in = st.text_input("Dein Name", key=f"n_{i}")
                if st.button("Ich bin dabei! ✅", key=f"j_{i}"):
                    if n_in:
                        new_p = pd.DataFrame([{"event": event_name, "name": n_in}])
                        upd_p = pd.concat([participants_df, new_p], ignore_index=True)
                        conn.update(worksheet="participants", data=upd_p)
                        st.success(f"Check, {n_in}!")
                        st.rerun()

                curr_p = participants_df[participants_df['event'] == event_name]
                if not curr_p.empty:
                    st.write(f"🔥 **Dabei:** {', '.join(curr_p['name'].tolist())}")
                else:
                    st.write("🏃 Noch niemand dabei.")

    else:
        st.write("Keine Events geplant.")
except Exception as ex:
    st.error(f"Fehler beim Laden: {ex}")
