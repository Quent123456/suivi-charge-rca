"""
pages/1_Saisie_Quotidienne.py
Formulaire de saisie quotidienne (100% Google Sheets) avec recherche, mémorisation et masquage dynamique.
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Saisie Quotidienne", page_icon="📝", layout="centered")

st.title("Saisie Quotidienne")
st.markdown("Enregistrez la séance d'entraînement et le ressenti de chaque joueur.")

# ── 1. Initialisation des mémoires (Session State) ──────────────────────────────
if "submitted_players" not in st.session_state:
    st.session_state.submitted_players = []
if "saved_duration" not in st.session_state:
    st.session_state.saved_duration = 75
if "saved_group" not in st.session_state:
    st.session_state.saved_group = "Groupe Élargi"

# ── 2. Connexion à Google Sheets ───────────────────────────────────────────────
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    players_df = conn.read(worksheet="Effectif", ttl=0)
    players_df = players_df.dropna(how="all")
except Exception as e:
    st.error(f"Erreur de connexion à Google Sheets : {e}")
    st.stop()

if players_df.empty:
    st.warning("Aucun joueur enregistré. Ajoutez des joueurs dans **Gestion des Joueurs**.")
    st.stop()

# ── 3. Formatage, Tri et Filtrage de l'effectif ────────────────────────────────
# Formatage strict : NOM (majuscules) Prénom (majuscule initiale)
players_df["prenom"] = players_df["prenom"].fillna("").astype(str).str.strip().str.title()
players_df["nom"] = players_df["nom"].fillna("").astype(str).str.strip().str.upper()
players_df["poste"] = players_df["poste"].fillna("Inconnu")

# Tri alphabétique 
players_df = players_df.sort_values(by=["nom", "prenom"])

# Création des options
all_player_options = {}
for _, row in players_df.iterrows():
    if row['nom'] != "":
        label = f"{row['nom']} {row['prenom']} — {row['poste']}"
        all_player_options[label] = {
            "nom_complet": f"{row['nom']} {row['prenom']}",
            "poste": row["poste"]
        }

# Exclusion des joueurs déjà validés
available_options = {k: v for k, v in all_player_options.items() if k not in st.session_state.submitted_players}

# En-tête avec bouton de rafraîchissement
col_title, col_btn = st.columns([2, 1])
with col_btn:
    if st.button("🔄 Réafficher l'effectif", use_container_width=True):
        st.session_state.submitted_players = []
        st.rerun()

if not available_options:
    st.success("Toutes les saisies ont été effectuées ! Cliquez sur le bouton 'Réafficher l'effectif' pour recommencer.")
    st.stop()

# ── 4. Interface Dynamique ─────────────────────────────────────────────────────
# Recherche
search_term = st.text_input("🔍 Rechercher un joueur (Nom ou Prénom) :", "").lower()

filtered_options = {
    k: v for k, v in available_options.items() 
    if search_term in k.lower()
}

if not filtered_options:
    st.warning("Aucun joueur trouvé. Vérifiez l'orthographe ou réaffichez l'effectif.")
    st.stop()

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    selected_label = st.selectbox("Joueur sélectionné", options=list(filtered_options.keys()))
with col2:
    session_date = st.date_input("Date", value=date.today(), max_value=date.today())

# Synchronisation Date -> Jour
JOURS_SEMAINE = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
jour_auto = JOURS_SEMAINE[session_date.weekday()]
OPTIONS_JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Jour de match", "Dimanche"]
index_jour = OPTIONS_JOURS.index(jour_auto) if jour_auto in OPTIONS_JOURS else 1

col_sem, col_jour = st.columns(2)
with col_sem:
    semaine = st.number_input(
        "Numéro de semaine",
        min_value=1, max_value=52, value=session_date.isocalendar()[1],
    )
with col_jour:
    jour = st.selectbox("Jour d'entraînement", options=OPTIONS_JOURS, index=index_jour)

st.markdown("---")
st.subheader("Charge de séance")

RPE_LABELS = {0: "0 — Repos complet", 1: "1 — Très très facile", 2: "2 — Très facile", 3: "3 — Facile", 4: "4 — Effort modéré", 5: "5 — Effort moyen", 6: "6 — Effort un peu difficile", 7: "7 — Difficile", 8: "8 — Très difficile", 9: "9 — Très très difficile", 10: "10 — Maximal"}

col3, col4, col5 = st.columns(3)
with col3:
    rpe = st.select_slider("RPE — Perception de l'effort", options=list(RPE_LABELS.keys()), value=5, format_func=lambda x: RPE_LABELS[x])
with col4:
    duration = st.number_input("Durée (minutes)", min_value=0, max_value=300, value=st.session_state.saved_duration, step=5)
with col5:
    load = rpe * duration
    st.metric("Charge Foster (UA)", f"{load:.0f}")

st.markdown("---")
st.subheader("Etat de bien-être")

col6, col7, col8 = st.columns(3)
with col6:
    fatigue = st.select_slider("Fatigue", options=[1, 2, 3, 4, 5], value=3)
with col7:
    courbatures = st.select_slider("Courbatures", options=[1, 2, 3, 4, 5], value=3)
with col8:
    sommeil = st.select_slider("Sommeil", options=[1, 2, 3, 4, 5], value=3)

st.markdown("---")
group_options = ["Équipe A", "Équipe B", "Groupe Élargi"]
default_group_index = group_options.index(st.session_state.saved_group) if st.session_state.saved_group in group_options else 2

groupe_entrainement = st.radio("Groupe d'entraînement *", group_options, horizontal=True, index=default_group_index)

st.markdown("---")
notes = st.text_area("Notes / Observations (optionnel)", height=80)
is_rest_day = st.checkbox("Jour de repos (charge = 0)")

# ── 5. Traitement Google Sheets ────────────────────────────────────────────────
if st.button("✅ Enregistrer la séance", type="primary", use_container_width=True):
    player_info = filtered_options[selected_label]
    nom_prenom = player_info["nom_complet"]
    poste = player_info["poste"]

    actual_rpe = 0 if is_rest_day else rpe
    actual_duration = 0 if is_rest_day else duration
    actual_load = 0.0 if is_rest_day else load
    
    # Mise à jour des valeurs mémorisées pour le prochain joueur
    st.session_state.saved_duration = duration
    st.session_state.saved_group = groupe_entrainement

    with st.spinner("Enregistrement dans Google Sheets..."):
        try:
            saisies_df = conn.read(worksheet="Saisies", ttl=0)
            notes_gs = f"[{groupe_entrainement}] {notes}" if notes.strip() else f"[{groupe_entrainement}]"
            horodateur = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            
            new_row = pd.DataFrame([{
                "Cle de recherche": f"{semaine}{nom_prenom.replace(' ', '')}",
                "Horodateur": horodateur,
                "Difficulte seance": RPE_LABELS[actual_rpe],
                "Ressenti / Notes": notes_gs,
                "Nom / Prenom": nom_prenom,
                "Poste": poste,
                "Numero Semaine": semaine,
                "Jour seance": jour,
                "RPE (Chiffre)": actual_rpe,
                "Duree (min)": actual_duration,
                "Charge (UA)": actual_load,
                "Fatigue | Courbatures | Sommeil": f"Fatigue:{fatigue} | Courbatures:{courbatures} | Sommeil:{sommeil}"
            }])
            
            updated_df = pd.concat([saisies_df, new_row], ignore_index=True)
            conn.update(worksheet="Saisies", data=updated_df)
            
            # Ajout du joueur à la liste des "déjà saisis"
            st.session_state.submitted_players.append(selected_label)
            
            # Rechargement immédiat de la page pour le masquer
            st.rerun()
            
        except Exception as e:
            st.error(f"Erreur lors de l'enregistrement : {e}")
