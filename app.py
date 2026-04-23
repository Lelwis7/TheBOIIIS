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
    page = st.radio("Gehe zu:", ["🗓️ Events", "📊 Votings"])
    st.write("---")
    st.header("🔐 Admin-Login")
    password = st.text_input("Passwort eingeben", type="password")

# --- SEITE 1: EVENTS ---
if page == "🗓️ Events":
    col_title, col_abo = st.columns([2, 1])
    with col_title:
        st.title("📅 Unsere Events")
    with col_abo:
        ical_link = "https://calendar.google.com/calendar/ical/8d035138c79ebce46d9e4c5899614c429cc1044c3c223349dcb885b24c8d12b2%40group.calendar.google.com/private-1600c31d25ba8c5a8127559dd4501184/basic.ics"
        webcal_link = ical_link.replace("https://", "webcal://")
        c1, c2 = st.columns(2)
        with c1:
            st.link_button("🍎", webcal_link, use_container_width=True)
        with c2:
            google_url = f"https://www.google.com/calendar/render?cid={urllib.parse.quote(ical_link)}"
            st.link_button("🌐", google_url, use_container_width=True)

    st.write("---")

    if password == "1404":
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
                    if d_start != d_end: display_date += f" - {d_end.strftime('%d.%m.%Y')}"
                    
                    df_current = conn.read(worksheet="events", ttl=0)
                    new_row = pd.DataFrame([{
                        "summary": summary, "date": display_date, "location": location, 
                        "description": description, "start_time": start_val.strftime("%H:%M") if use_start else "", 
                        "end_time": end_val.strftime("%H:%M") if use_end else ""
                    }])
                    conn.update(worksheet="events", data=pd.concat([df_current, new_row], ignore_index=True))
                    st.rerun()

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
                    if password == "1404":
                        with c_admin:
                            if st.button("🗑️ Löschen", key=f"del_ev_{i}"):
                                conn.update(worksheet="events", data=df.drop(i))
                                st.rerun()
                    st.write("---")
                    n_in = st.text_input("Dein Name", key=f"n_in_{i}")
                    if st.button("Ich bin dabei! ✅", key=f"j_ev_{i}") and n_in:
                        conn.update(worksheet="participants", data=pd.concat([p_df, pd.DataFrame([{"event": row['summary'], "name": n_in}])], ignore_index=True))
                        st.rerun()
                    curr_p = p_df[p_df['event'] == row['summary']]
                    st.write(f"🔥 **Dabei:** {', '.join(curr_p['name'].tolist())}" if not curr_p.empty else "🏃 Niemand da.")
    except Exception as e: 
        st.error(f"Event-Fehler: {e}")

# --- SEITE 2: VOTINGS ---
elif page == "📊 Votings":
    st.title("📊 The BOIIIS Votings")
    
    if password == "1404":
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
                        # HIER IST DER FIX: Die Tabelle braucht zwingend diese Spalten, auch wenn sie leer ist!
                        c_votes = pd.DataFrame(columns=['voting_id', 'name', 'option'])
                    
                    for o in opts:
                        # Jetzt stürzt er hier nicht mehr ab, weil 'option' garantiert existiert
                        count = len(c_votes[c_votes['option'] == o])
                        st.write(f"**{o}** ({count} Stimmen)")
                        st.progress(min(count / 10, 1.0))
                    
                    col_v1, col_v2 = st.columns([1, 1])
                    with col_v1:
                        with st.popover("Abstimmen"):
                            u_name = st.text_input("Name", key=f"un_{v_id_val}")
                            u_choice = st.radio("Wahl:", opts, key=f"uc_{v_id_val}")
                            if st.button("Voten!", key=f"vb_{v_id_val}") and u_name:
                                new_vote = pd.DataFrame([{"voting_id": v_id_val, "name": u_name, "option": u_choice}])
                                conn.update(worksheet="votes", data=pd.concat([votes_df, new_vote], ignore_index=True))
                                st.rerun()
                    if password == "1404":
                        if col_v2.button("🗑️ Beenden", key=f"dv_{v_id_val}"):
                            conn.update(worksheet="votings", data=v_df.drop(i))
                            st.rerun()
        else: 
            st.warning("⚠️ Im Google Sheet 'votings' fehlt die Spalte 'id' oder es gibt keine Umfragen.")
    except Exception as e: 
        st.error(f"Kritischer Fehler bei den Votings: {e}")
