import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
from datetime import datetime
import time

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="The BOIIIS App", page_icon="📅", layout="centered")

# --- VERBINDUNG ZUM GOOGLE SHEET ---
conn = st.connection("gsheets", type=GSheetsConnection)
CACHE_TIME = 600 

# --- SICHERHEIT & DATEN ---
try:
    ICAL_URL = st.secrets["calendar"]["ical_link"]
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
    USERS = st.secrets["users"] 
    USER_OPTIONS = list(USERS.keys())
except Exception:
    st.error("❌ Secrets fehlen!")
    st.stop()

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""

# ==========================================
# GATEKEEPER: LOGIN
# ==========================================
if not st.session_state["logged_in"]:
    st.title("🔒 The BOIIIS - Login")
    with st.form("login_form"):
        username = st.text_input("Wer bist du?")
        password = st.text_input("Passwort", type="password")
        if st.form_submit_button("Let's go", use_container_width=True):
            if username in USERS and USERS[username] == password:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Falscher Name oder Passwort.")

# ==========================================
# HAUPT-APP
# ==========================================
else:
    with st.sidebar:
        st.markdown(f"### 👨‍💻 {st.session_state['username']}")
        
        is_admin = False
        if st.session_state['username'] == "Luca":
            admin_pass = st.text_input("Admin-Passwort", type="password", placeholder="Planer-Login...")
            is_admin = admin_pass == ADMIN_PASSWORD
            st.caption("👑 Planer-Modus aktiv" if is_admin else "👑 Planer-Login")
        else:
            st.caption("👤 BOIIIS Member")
        
        if st.button("🚪 Ausloggen", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state.clear()
            st.rerun()
        
        st.divider()
        page = st.radio("Menü", ["🗓️ Events", "📊 Votings", "💰 Finanzen"], label_visibility="collapsed")
        st.caption("Version 1.11 (Finance Upgrade)")

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
                st.link_button("🍎", webcal_link, use_container_width=True)
            with c2: 
                google_url = f"https://www.google.com/calendar/render?cid={urllib.parse.quote(ICAL_URL)}"
                st.link_button("🌐", google_url, use_container_width=True)

        st.write("---")

        # Admin: Event Erstellung
        if is_admin:
            with st.expander("➕ Neues Event planen"):
                with st.form("event_form"):
                    summary = st.text_input("Was steht an?")
                    date_range = st.date_input("Zeitraum", value=[datetime.now(), datetime.now()])
                    location = st.text_input("Wo?")
                    description = st.text_area("Zusatzinfos")
                    
                    if st.form_submit_button("Event offiziell planen"):
                        d_start = date_range[0]
                        d_end = date_range[1] if len(date_range) > 1 else d_start
                        display_date = d_start.strftime('%d.%m.%Y')
                        if d_start != d_end: 
                            display_date += f" - {d_end.strftime('%d.%m.%Y')}"
                        
                        df_current = conn.read(worksheet="events", ttl=0)
                        new_row = pd.DataFrame([{"summary": summary, "date": display_date, "location": location, "description": description, "start_time": "", "end_time": ""}])
                        conn.update(worksheet="events", data=pd.concat([df_current, new_row], ignore_index=True))
                        st.cache_data.clear()
                        st.toast("Event wurde erstellt!", icon="✅")
                        time.sleep(1)
                        st.rerun()

        # Daten laden
        try:
            df = conn.read(worksheet="events", ttl=CACHE_TIME).fillna("")
            p_df = conn.read(worksheet="participants", ttl=CACHE_TIME).fillna("")
            
            try:
                c_df = conn.read(worksheet="checklists", ttl=CACHE_TIME).fillna("")
            except:
                c_df = pd.DataFrame(columns=["event_summary", "item", "assigned_to", "done", "amount"])
            
            # Datentypen fixen (SICHERHEITSNETZ)
            if 'amount' not in c_df.columns: 
                c_df['amount'] = "1"
            if 'done' in c_df.columns:
                c_df['done'] = c_df['done'].astype(str)

            if not df.empty:
                for i in reversed(df.index):
                    row = df.loc[i]
                    with st.expander(f"🗓️ {row['date']} - {row['summary']}"):
                        st.write(f"📍 **Ort:** {row['location']}")
                        st.info(f"💬 {row['description']}")
                        
                        # --- CHECKLISTEN SEKTION ---
                        st.write("### 🎒 Mitbringliste")
                        event_mask = c_df['event_summary'] == row['summary']
                        event_items_indices = c_df.index[event_mask].tolist()
                        
                        if event_items_indices:
                            for c_idx in event_items_indices:
                                c_row = c_df.loc[c_idx]
                                col_amt, col_main, col_admin = st.columns([0.6, 4, 1.2])
                                unique_key = f"chk_{i}_{c_idx}_{row['summary'][:5]}"
                                
                                with col_amt:
                                    display_amt = int(float(c_row['amount'])) if str(c_row['amount']).strip() != "" else 1
                                    st.write(f"**{display_amt}x**")

                                with col_main:
                                    st.write(f"**{c_row['item']}**")
                                    current_assigned = [u.strip() for u in str(c_row['assigned_to']).split(",") if u.strip()]
                                    
                                    if current_assigned:
                                        st.caption(f"👤 {', '.join(current_assigned)}")
                                    else:
                                        st.caption("⚪ Noch niemand eingeteilt")

                                    if is_admin:
                                        selected_users = st.multiselect("Zuweisen:", USER_OPTIONS, default=current_assigned, key=f"ms_{unique_key}", label_visibility="collapsed")
                                        new_assigned_str = ", ".join(selected_users)
                                        # SICHERHEITSNETZ: Konsequenter String-Vergleich
                                        if new_assigned_str != str(c_row['assigned_to']):
                                            c_df.at[c_idx, 'assigned_to'] = new_assigned_str
                                            conn.update(worksheet="checklists", data=c_df)
                                            st.cache_data.clear()
                                            st.rerun()
                                    else:
                                        if st.session_state["username"] in current_assigned:
                                            if st.button("Bin doch raus", key=f"out_{unique_key}"):
                                                current_assigned.remove(st.session_state["username"])
                                                c_df.at[c_idx, 'assigned_to'] = ", ".join(current_assigned)
                                                conn.update(worksheet="checklists", data=c_df)
                                                st.cache_data.clear()
                                                st.rerun()
                                        else:
                                            if st.button("Übernehme ich", key=f"in_{unique_key}"):
                                                current_assigned.append(st.session_state["username"])
                                                c_df.at[c_idx, 'assigned_to'] = ", ".join(current_assigned)
                                                conn.update(worksheet="checklists", data=c_df)
                                                st.cache_data.clear()
                                                st.rerun()

                                with col_admin:
                                    if is_admin:
                                        col_edit, col_del = st.columns(2)
                                        with col_edit:
                                            with st.popover("📝"):
                                                edit_name = st.text_input("Name", value=c_row['item'], key=f"ed_n_{unique_key}")
                                                edit_amt_raw = st.number_input("Anzahl", value=display_amt, step=1, key=f"ed_a_{unique_key}")
                                                if st.button("Speichern", key=f"save_{unique_key}"):
                                                    c_df.at[c_idx, 'item'] = edit_name
                                                    c_df.at[c_idx, 'amount'] = str(int(edit_amt_raw))
                                                    conn.update(worksheet="checklists", data=c_df)
                                                    st.cache_data.clear()
                                                    st.rerun()
                                        with col_del:
                                            if st.button("🗑️", key=f"del_chk_{unique_key}"):
                                                c_df = c_df.drop(c_idx)
                                                conn.update(worksheet="checklists", data=c_df)
                                                st.cache_data.clear()
                                                st.rerun()
                        else: 
                            st.info("Die Liste ist noch leer.")

                        if is_admin:
                            with st.form(f"add_item_{i}", clear_on_submit=True):
                                col_add_amt, col_add_item = st.columns([1, 3])
                                with col_add_amt: 
                                    add_amt = st.number_input("Menge", min_value=1, value=1, step=1)
                                with col_add_item: 
                                    add_item = st.text_input("Was wird gebraucht?")
                                
                                if st.form_submit_button("Hinzufügen") and add_item:
                                    new_entry = pd.DataFrame([{"event_summary": row['summary'], "item": add_item, "amount": str(int(add_amt)), "assigned_to": "", "done": "FALSE"}])
                                    conn.update(worksheet="checklists", data=pd.concat([c_df, new_entry], ignore_index=True))
                                    st.cache_data.clear()
                                    st.rerun()

                        st.write("---")
                        
                        curr_p = p_df[p_df['event'] == row['summary']]
                        if st.session_state["username"] not in curr_p['name'].values:
                            if st.button("Ich bin dabei! 🚀", key=f"j_ev_{i}"):
                                new_participant = pd.DataFrame([{"event": row['summary'], "name": st.session_state["username"]}])
                                conn.update(worksheet="participants", data=pd.concat([p_df, new_participant], ignore_index=True))
                                st.cache_data.clear()
                                st.rerun()
                                
                        st.write(f"🔥 **Dabei:** {', '.join(curr_p['name'].tolist())}" if not curr_p.empty else "🏃 Niemand.")
                        
                        if is_admin:
                            st.write("---")
                            if st.button("🗑️ Event komplett löschen", key=f"del_ev_{i}"):
                                conn.update(worksheet="events", data=df.drop(i))
                                st.cache_data.clear()
                                st.rerun()
            else: 
                st.write("Aktuell keine Events geplant.")
                
        except Exception as e: 
            st.error(f"Event-Fehler: {e}")

    # --- SEITE 2: VOTINGS ---
    elif page == "📊 Votings":
        st.title("📊 The BOIIIS Votings")
        
        if is_admin:
            with st.expander("➕ Neue Umfrage starten"):
                with st.form("new_v"):
                    v_title = st.text_input("Thema")
                    v_options = st.text_area("Optionen (pro Zeile)")
                    allow_multi = st.checkbox("Mehrfachauswahl erlauben?")
                    
                    if st.form_submit_button("Start") and v_title and v_options:
                        v_df = conn.read(worksheet="votings", ttl=0)
                        v_id_new = datetime.now().strftime("%Y%m%d%H%M%S")
                        multi_val = "TRUE" if allow_multi else "FALSE"
                        
                        new_v = pd.DataFrame([{"id": v_id_new, "title": v_title, "options": v_options, "active": "TRUE", "multi_choice": multi_val}])
                        updated_df = pd.concat([v_df, new_v], ignore_index=True)
                        
                        # Die "Zwangsjacke" für Spalten
                        expected_columns = ["id", "title", "options", "active", "multi_choice"]
                        for col in expected_columns:
                            if col not in updated_df.columns: 
                                updated_df[col] = "" 
                        
                        conn.update(worksheet="votings", data=updated_df[expected_columns])
                        st.cache_data.clear() 
                        st.toast("Umfrage gestartet!", icon="🗳️")
                        time.sleep(1)
                        st.rerun()

        try:
            v_df = conn.read(worksheet="votings", ttl=CACHE_TIME).fillna("")
            votes_df = conn.read(worksheet="votes", ttl=CACHE_TIME).fillna("")
            
            if not v_df.empty:
                # SCHUTZ 1: Spaltennamen zwingend klein machen
                v_df.columns = [c.lower() for c in v_df.columns]
                
                if not votes_df.empty: 
                    votes_df.columns = [c.lower() for c in votes_df.columns]
                    # SCHUTZ 2: IDs im Vote-Sheet in reinen Text umwandeln
                    if 'voting_id' in votes_df.columns:
                        votes_df['voting_id'] = votes_df['voting_id'].astype(str).str.strip()

                for i, v_row in v_df.iterrows():
                    v_id_val = str(v_row['id']).strip()
                    
                    # SCHUTZ 3: Robuste Abfrage für Mehrfachauswahl
                    is_multi = False
                    if 'multi_choice' in v_df.columns:
                        is_multi = str(v_row['multi_choice']).strip().upper() in ['TRUE', 'WAHR', '1', '1.0', 'YES', 'JA']
                    
                    with st.container(border=True):
                        st.subheader(f"🗳️ {v_row['title']}" + (" (Mehrfachwahl)" if is_multi else ""))
                        opts = [o.strip() for o in v_row['options'].split("\n") if o.strip()]
                        
                        # Sicherstellen, dass c_votes existiert
                        if not votes_df.empty and 'voting_id' in votes_df.columns:
                            c_votes = votes_df[votes_df['voting_id'] == v_id_val]
                        else:
                            c_votes = pd.DataFrame(columns=['voting_id', 'name', 'option'])
                        
                        if is_admin:
                            voted_users = set(c_votes['name'].unique()) if 'name' in c_votes.columns else set()
                            missing_users = set(USERS.keys()) - voted_users
                            if missing_users: 
                                st.warning(f"⏳ **Noch offen von:** {', '.join(missing_users)}")
                            else: 
                                st.success("🎯 Alle haben abgestimmt!")

                        for o in opts:
                            count = len(c_votes[c_votes['option'] == o]) if 'option' in c_votes.columns else 0
                            st.write(f"**{o}** ({count} Stimmen)")
                            st.progress(min(count / max(1, len(USERS)), 1.0))

                        declined_count = len(c_votes[c_votes['option'] == "Kein Interesse / Enthaltung"]) if 'option' in c_votes.columns else 0
                        if declined_count > 0: 
                            st.caption(f"ℹ️ {declined_count} Person(en) haben kein Interesse oder enthalten sich.")

                        if is_admin and not c_votes.empty:
                            with st.expander("🕵️‍♂️ Detail-Auswertung"):
                                for o in opts:
                                    voters = c_votes[c_votes['option'] == o]['name'].tolist() if 'option' in c_votes.columns else []
                                    if voters: 
                                        st.write(f"- **{o}:** {', '.join(voters)}")
                                declined_voters = c_votes[c_votes['option'] == "Kein Interesse / Enthaltung"]['name'].tolist() if 'option' in c_votes.columns else []
                                if declined_voters: 
                                    st.write(f"- **Kein Interesse:** {', '.join(declined_voters)}")

                        has_voted = st.session_state["username"] in c_votes['name'].values if not c_votes.empty and 'name' in c_votes.columns else False

                        col_v1, col_v2 = st.columns([1, 1])
                        with col_v1:
                            if has_voted: 
                                st.success("Erledigt! ✅")
                            else:
                                with st.popover("Abstimmen"):
                                    if is_multi: 
                                        u_choices = st.multiselect("Deine Favoriten:", opts, key=f"uc_{v_id_val}")
                                    else:
                                        u_choice_single = st.radio("Deine Wahl:", opts, key=f"uc_{v_id_val}")
                                        u_choices = [u_choice_single] if u_choice_single else []

                                    if st.button("Voten!", key=f"vb_{v_id_val}"):
                                        if not u_choices: 
                                            st.warning("Bitte wähle etwas aus.")
                                        else:
                                            new_votes = pd.DataFrame([{"voting_id": v_id_val, "name": st.session_state["username"], "option": c} for c in u_choices])
                                            conn.update(worksheet="votes", data=pd.concat([votes_df, new_votes], ignore_index=True))
                                            st.cache_data.clear()
                                            st.toast("Abgestimmt!", icon="🗳️")
                                            time.sleep(1)
                                            st.rerun()
                                            
                                    st.write("---")
                                    if st.button("Kein Interesse ✋", key=f"decl_{v_id_val}", use_container_width=True):
                                        new_vote = pd.DataFrame([{"voting_id": v_id_val, "name": st.session_state["username"], "option": "Kein Interesse / Enthaltung"}])
                                        conn.update(worksheet="votes", data=pd.concat([votes_df, new_vote], ignore_index=True))
                                        st.cache_data.clear()
                                        st.rerun()
                        
                        if is_admin:
                            if col_v2.button("🗑️ Beenden", key=f"dv_{v_id_val}"):
                                conn.update(worksheet="votings", data=v_df.drop(i))
                                st.cache_data.clear()
                                st.rerun()
            else: 
                st.info("Keine aktiven Umfragen.")
                
        except Exception as e: 
            st.error(f"Votings-Fehler: {e}")

# --- SEITE 3: FINANZEN (UPDATE V1.12) ---
    elif page == "💰 Finanzen":
        st.title("💰 Kasse & Abrechnung")
        
        try:
            f_df = conn.read(worksheet="finances", ttl=CACHE_TIME).fillna("")
            p_df = conn.read(worksheet="participants", ttl=CACHE_TIME).fillna("")
            pay_df = conn.read(worksheet="payments", ttl=CACHE_TIME).fillna("")
            ev_df = conn.read(worksheet="events", ttl=CACHE_TIME).fillna("")

            # SICHERHEITSNETZ: Spalte für Schuldner hinzufügen, falls nicht existent
            if 'debtors' not in f_df.columns:
                f_df['debtors'] = ""

            if is_admin:
                with st.expander("💸 Neue Rechnung erstellen"):
                    with st.form("finance_form"):
                        target_ev = st.selectbox("Event wählen", ev_df['summary'].tolist() if not ev_df.empty else ["Keine Events"])
                        t_cost = st.number_input("Gesamtkosten (€) (Z.B. Hotel + Sprit)", min_value=0.0, step=10.0)
                        prov = st.number_input("Deine Provision pro Kopf (€)", min_value=0.0, max_value=25.0, value=2.0, step=0.5)
                        
                        # NEU: Explizite Auswahl der Schuldner
                        selected_debtors = st.multiselect(
                            "Kostensplit: Wer teilt sich die Rechnung?", 
                            USER_OPTIONS, 
                            help="Die Gesamtkosten werden durch die Anzahl der hier gewählten Personen geteilt."
                        )
                        
                        if st.form_submit_button("Rechnung abschicken"):
                            if not selected_debtors:
                                st.warning("Bitte wähle mindestens eine Person für den Kostensplit aus!")
                            else:
                                new_f = pd.DataFrame([{
                                    "event_summary": target_ev, 
                                    "total_cost": t_cost, 
                                    "provision_per_person": prov,
                                    "debtors": ", ".join(selected_debtors) # Speichere die Namen
                                }])
                                old_f = conn.read(worksheet="finances", ttl=0)
                                conn.update(worksheet="finances", data=pd.concat([old_f, new_f], ignore_index=True))
                                st.cache_data.clear()
                                st.toast("Rechnung erstellt!", icon="💸")
                                time.sleep(1)
                                st.rerun()

                st.write("### 🕵️‍♂️ Offene Zahlungen (Admin-Übersicht)")
                if not f_df.empty:
                    for f_idx, f_row in f_df.iterrows():
                        ev_name = f_row['event_summary']
                        
                        # Lese die expliziten Schuldner aus. Falls alt/leer, nutze Event-Teilnehmer
                        if str(f_row.get('debtors', '')).strip():
                            debtors_list = [u.strip() for u in str(f_row['debtors']).split(",") if u.strip()]
                        else:
                            debtors_list = p_df[p_df['event'] == ev_name]['name'].tolist()
                        
                        if debtors_list:
                            # Kosten pro Kopf = (Gesamt / Ausgewählte Personen) + Provision
                            per_head = (float(f_row['total_cost']) / len(debtors_list)) + float(f_row['provision_per_person'])
                            
                            # NEU: Mülleimer für Rechnungen
                            col_title, col_del = st.columns([4, 1])
                            with col_title:
                                st.write(f"**{ev_name}** ({per_head:.2f} € p.P.)")
                            with col_del:
                                if st.button("🗑️", key=f"del_fin_{f_idx}", help="Rechnung löschen"):
                                    conn.update(worksheet="finances", data=f_df.drop(f_idx))
                                    st.cache_data.clear()
                                    st.rerun()

                            # Die "Wurde bezahlt" Buttons
                            for person in debtors_list:
                                if person == st.session_state["username"]: 
                                    continue # Du schuldest dir selbst nichts!
                                
                                # Prüfe in 'payments', ob ein Eintrag für diese Person & Event existiert
                                paid_status = not pay_df[(pay_df['event_summary'] == ev_name) & (pay_df['user_name'] == person)].empty
                                
                                c1, c2 = st.columns([3, 1])
                                with c1:
                                    st.write(f"{'✅' if paid_status else '⏳'} {person}")
                                with c2:
                                    if not paid_status:
                                        if st.button("Bezahlt", key=f"pay_{ev_name}_{person}_{f_idx}"):
                                            new_pay = pd.DataFrame([{"event_summary": ev_name, "user_name": person, "is_paid": "TRUE"}])
                                            old_pay = conn.read(worksheet="payments", ttl=0)
                                            conn.update(worksheet="payments", data=pd.concat([old_pay, new_pay], ignore_index=True))
                                            st.cache_data.clear()
                                            st.toast(f"Geld von {person} erhalten!", icon="💰")
                                            time.sleep(1)
                                            st.rerun()
                            st.divider()
                else:
                    st.info("Noch keine Rechnungen gestellt.")

            # --- USER ANSICHT (RECHNUNGS-DASHBOARD) ---
            if not is_admin: # Die Jungs sehen ihre eigenen Schulden
                st.write("### 🧾 Meine offenen Rechnungen")
                my_name = st.session_state["username"]
                found_any = False
                
                for _, f_row in f_df.iterrows():
                    ev_name = f_row['event_summary']
                    
                    if str(f_row.get('debtors', '')).strip():
                        debtors_list = [u.strip() for u in str(f_row['debtors']).split(",") if u.strip()]
                    else:
                        debtors_list = p_df[p_df['event'] == ev_name]['name'].tolist()
                    
                    if my_name in debtors_list:
                        # Prüfen ob bereits bezahlt
                        is_paid = not pay_df[(pay_df['event_summary'] == ev_name) & (pay_df['user_name'] == my_name)].empty
                        
                        if not is_paid:
                            found_any = True
                            per_head = (float(f_row['total_cost']) / len(debtors_list)) + float(f_row['provision_per_person'])
                            with st.container(border=True):
                                st.subheader(f"📅 {ev_name}")
                                st.write(f"Zu zahlen: **{per_head:.2f} €**")
                                st.caption(f"(Inklusive {f_row['provision_per_person']}€ Planungs-Provision)")
                                # Hier könntest du sogar einen Link einfügen:
                                # st.markdown("[Jetzt per PayPal zahlen](https://paypal.me/DeinName)")
                
                if not found_any:
                    st.success("Alle Rechnungen beglichen. Du bist sauber! 💸")

        except Exception as e:
            st.error(f"Finanz-Fehler: {e}")
