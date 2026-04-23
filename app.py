import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
from datetime import datetime

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="The BOIIIS App", page_icon="📅", layout="centered")

# --- VERBINDUNG ZUM GOOGLE SHEET ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SICHERHEIT (AUS SECRETS LADEN) ---
try:
    ICAL_URL = st.secrets["calendar"]["ical_link"]
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
    USERS = st.secrets["users"] # Lädt alle angelegten Kumpels
except Exception:
    st.error("❌ Secrets nicht gefunden! Bitte ical_link, admin_password und [users] konfigurieren.")
    st.stop()

# --- SESSION LOGIK (LOGIN STATUS SPEICHERN) ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""

# ==========================================
# GATERKEEPER: LOGIN SEITE
# ==========================================
if not st.session_state["logged_in"]:
    st.title("🔒 The BOIIIS - Login")
    st.write("Bitte melde dich an, um auf die Event-Planung zuzugreifen.")
    
    with st.form("login_form"):
        username = st.text_input("Wer bist du? (Name)")
        password = st.text_input("Passwort", type="password")
        submit = st.form_submit_button("Let's go")
        
        if submit:
            # Prüfen, ob der Name existiert und das Passwort stimmt
            if username in USERS and USERS[username] == password:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Falscher Name oder Passwort. Versuch's nochmal!")

# ==========================================
# HAUPT-APP (NUR SICHTBAR WENN EINGELOGGT)
# ==========================================
else:
    # --- NAVIGATION & LOGIN (SIDEBAR) ---
    with st.sidebar:
        st.success(f"Eingeloggt als: **{st.session_state['username']}**")
        if st.button("🚪 Ausloggen"):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.rerun()
        
        st.write("---")
        st.title("📌 Menü")
        page = st.radio("Gehe zu:", ["🗓️ Events", "📊 Votings"])
        
        st.write("---")
        st.header("🔐 Planer-Rechte (Admin)")
        password = st.text_input("Admin-Passwort", type="password", help="Nur für Event-Erstellung")

    # --- SEITE 1: EVENTS ---
    if page == "🗓️ Events":
        col_title, col_abo = st.columns([2, 1])
        with col_title:
            st.title("📅 Unsere Events")
        
        with col_abo:
            webcal_link = ICAL_URL.replace("https://", "webcal://")
            st.write("Abo:")
            c1, c2 = st.columns(2)
            with c1:
                st.link_button("🍎", webcal_link, use_container_width=True, help="iPhone Kalender Abo")
            with c2:
                google_url = f"https://www.google.com/calendar/render?cid={urllib.parse.quote(ICAL_URL)}"
                st.link_button("🌐", google_url, use_container_width=True, help="Google/Android Kalender")

        st.write("---")

        # --- ADMIN BEREICH: EVENT ERSTELLEN ---
        if password == ADMIN_PASSWORD:
            with st.expander("➕ Neues Event planen"):
                with st.form("event_form"):
                    summary = st.text_input("Was steht an?")
                    date_range = st.date_input("Zeitraum", value=[datetime.now(), datetime.now()])
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        use_start = st.checkbox("Startzeit?")
                        start_val = st.time_input("Von", value=datetime.strptime("12:00", "%H:%M"))
                    with col_t2:
                        use_end = st.checkbox("Endzeit?")
                        end_val = st.time_input("Bis", value=datetime.strptime("14:00", "%H:%M"))
                    
                    location = st.text_input("Wo?")
                    description = st.text_area("Infos")
                    
                    if st.form_submit_button("Event offiziell planen"):
                        d_start = date_range[0]
                        d_end = date_range[1] if len(date_range) > 1 else d_start
                        display_date = d_start.strftime('%d.%m.%Y')
                        if d_start != d_end: 
                            display_date += f" - {d_end.strftime('%d.%m.%Y')}"
                        
                        df_current = conn.read(worksheet="events", ttl=0)
                        new_row = pd.DataFrame([{
                            "summary": summary, 
                            "date": display_date, 
                            "location": location, 
                            "description": description, 
                            "start_time": start_val.strftime("%H:%M") if use_start else "", 
                            "end_time": end_val.strftime("%H:%M") if use_end else ""
                        }])
                        conn.update(worksheet="events", data=pd.concat([df_current, new_row], ignore_index=True))
                        st.success("Event gespeichert!")
                        st.rerun()

        # --- EVENT ANZEIGE ---
        try:
            df = conn.read(worksheet="events", ttl=0).fillna("")
            p_df = conn.read(worksheet="participants", ttl=0).fillna("")
            
            if not df.empty:
                for i in reversed(df.index):
                    row = df.loc[i]
                    s_t, e_t = str(row['start_time']), str(row['end_time'])
                    t_title = f" ({s_t}{' - ' + e_t if e_t else ''} Uhr)" if s_t else ""
                    
                    with st.expander(f"🗓️ {row['date']}{t_title} - {row['summary']}"):
                        c_info, c_admin = st.columns([3, 1.2])
                        with c_info:
                            st.write(f"📍 **Ort:** {row['location']}")
                            st.info(f"💬 {row['description']}")
                        
                        if password == ADMIN_PASSWORD:
                            with c_admin:
                                if st.button("🗑️ Löschen", key=f"del_ev_{i}"):
                                    conn.update(worksheet="events", data=df.drop(i))
                                    st.rerun()
                        
                        st.write("---")
                        # UX-UPGRADE: Der eingeloggte Name wird automatisch verwendet!
                        curr_p = p_df[p_df['event'] == row['summary']]
                        is_joined = st.session_state["username"] in curr_p['name'].values
                        
                        if is_joined:
                            st.success("Du bist bei diesem Event dabei! ✅")
                        else:
                            if st.button("Ich bin dabei! 🚀", key=f"j_ev_{i}"):
                                new_p = pd.DataFrame([{"event": row['summary'], "name": st.session_state["username"]}])
                                conn.update(worksheet="participants", data=pd.concat([p_df, new_p], ignore_index=True))
                                st.rerun()
                        
                        st.write(f"🔥 **Dabei:** {', '.join(curr_p['name'].tolist())}" if not curr_p.empty else "🏃 Noch niemand da.")
            else:
                st.write("Aktuell keine Events geplant.")
        except Exception as e: 
            st.error(f"Event-Fehler: {e}")

    # --- SEITE 2: VOTINGS ---
    elif page == "📊 Votings":
        st.title("📊 The BOIIIS Votings")
        
        if password == ADMIN_PASSWORD:
            with st.expander("➕ Neue Umfrage starten"):
                with st.form("new_v"):
                    v_title = st.text_input("Thema")
                    v_options = st.text_area("Optionen (pro Zeile)")
                    v_id_new = st.text_input("Eindeutige ID (z.B. 1, 2, 3)")
                    if st.form_submit_button("Start") and v_title and v_options and v_id_new:
                        v_df = conn.read(worksheet="votings", ttl=0)
                        new_v = pd.DataFrame([{"id": v_id_new, "title": v_title, "options": v_options, "active": "TRUE"}])
                        conn.update(worksheet="votings", data=pd.concat([v_df, new_v], ignore_index=True))
                        st.rerun()

        try:
            v_df = conn.read(worksheet="votings", ttl=0).fillna("")
            votes_df = conn.read(worksheet="votes", ttl=0).fillna("")
            
            if not v_df.empty and "id" in v_df.columns:
                v_df.columns = [c.lower() for c in v_df.columns]
                if not votes_df.empty:
                    votes_df.columns = [c.lower() for c in votes_df.columns]

                for i, v_row in v_df.iterrows():
                    v_id_val = str(v_row['id']).strip()
                    with st.container(border=True):
                        st.subheader(f"🗳️ {v_row['title']}")
                        opts = [o.strip() for o in v_row['options'].split("\n") if o.strip()]
                        
                        if not votes_df.empty and 'voting_id' in votes_df.columns:
                            votes_df['voting_id'] = votes_df['voting_id'].astype(str).str.strip()
                            c_votes = votes_df[votes_df['voting_id'] == v_id_val]
                        else:
                            c_votes = pd.DataFrame(columns=['voting_id', 'name', 'option'])
                        
                        for o in opts:
                            count = len(c_votes[c_votes['option'] == o]) if 'option' in c_votes.columns else 0
                            st.write(f"**{o}** ({count} Stimmen)")
                            st.progress(min(count / 10, 1.0))
                        
                        # Prüfen, ob der User hier schon abgestimmt hat
                        has_voted = False
                        if not c_votes.empty and 'name' in c_votes.columns:
                            has_voted = st.session_state["username"] in c_votes['name'].values

                        col_v1, col_v2 = st.columns([1, 1])
                        with col_v1:
                            if has_voted:
                                st.success("Du hast bereits abgestimmt! 🗳️")
                            else:
                                with st.popover("Abstimmen"):
                                    # UX-UPGRADE: Auch hier kein Namens-Feld mehr nötig!
                                    u_choice = st.radio("Wahl:", opts, key=f"uc_{v_id_val}")
                                    if st.button("Voten!", key=f"vb_{v_id_val}"):
                                        new_vote = pd.DataFrame([{"voting_id": v_id_val, "name": st.session_state["username"], "option": u_choice}])
                                        conn.update(worksheet="votes", data=pd.concat([votes_df, new_vote], ignore_index=True))
                                        st.rerun()
                        
                        if password == ADMIN_PASSWORD:
                            if col_v2.button("🗑️ Beenden", key=f"dv_{v_id_val}"):
                                conn.update(worksheet="votings", data=v_df.drop(i))
                                st.rerun()
            else: 
                st.info("Keine aktiven Umfragen.")
        except Exception as e: 
            st.error(f"Votings-Fehler: {e}")


