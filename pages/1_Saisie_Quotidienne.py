"""
pages/1_Saisie_Quotidienne.py
Formulaire de saisie quotidienne : RPE × Durée + bien-être.
"""

import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Saisie Quotidienne", page_icon="📝", layout="centered")

st.title("Saisie Quotidienne")
st.markdown("Enregistrez la séance d'entraînement et le ressenti de chaque joueur.")

# ── Connexion à Google Sheets ──────────────────────────────────────────────────
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Lecture de l'onglet Effectif
    players_df = conn.read(worksheet="Effectif", ttl=0)
    players_df = players_df.dropna(how="all")
    gsheets_ok = True
except Exception as e:
    gsheets_ok = False
    st.error(f"Erreur de connexion à Google Sheets : {e}")

if gsheets_ok:
    st.success(
        "Google Sheets connecté — Les données seront enregistrées dans "
        "**Test - Suivi Charge RCA Amiens**"
    )
else:
    st.stop() # On bloque la page si la connexion échoue

# ── Chargement joueurs ──────────────────────────────────────────────────────────
if players_df.empty:
    st.warning("Aucun joueur enregistré. Ajoutez des joueurs dans **Gestion des Joueurs**.")
    st.stop()

# Nettoyage et formatage pour éviter les erreurs si des cases sont vides
players_df["prenom"] = players_df["prenom"].fillna("")
players_df["nom"] = players_df["nom"].fillna("")
players_df["poste"] = players_df["poste"].fillna("Inconnu")

# Création de la liste des joueurs
player_options = {
    f"{row['prenom']} {row['nom']} — {row['poste']}": {
        "id": row.get("id", "1"),
        "nom": f"{row['nom']} {row['prenom']}",
        "poste": row["poste"],
        "groupe": row.get("groupe", "Groupe Élargi")
    }
    for _, row in players_df.iterrows() if str(row['nom']).strip() != ""
}

if not player_options:
     st.warning("La liste des joueurs semble vide ou mal formatée dans l'onglet Effectif.")
     st.stop()

def _get_week_number(d) -> int:
    """Calcule le numéro de semaine ISO."""
    try:
        return d.isocalendar()[1]
    except Exception:
        return 1

# ── Labels et variables de base ────────────────────────────────────────────────
JOURS_ENTRAINEMENT = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Jour de match", "Dimanche"]

RPE_LABELS = {
    0: "0 — Repos complet",
    1: "1 — Très très facile",
    2: "2 — Très facile",
    3: "3 — Facile",
    4: "4 — Effort modéré",
    5: "5 — Effort moyen",
    6: "6 — Effort un peu difficile",
    7: "7 — Difficile",
    8: "8 — Très difficile",
    9: "9 — Très très difficile",
    10: "10 — Maximal"
}

def foster_load(rpe, duration):
    return rpe * duration

# ── Formulaire ──────────────────────────────────────────────────────────────────
with st.form("saisie_form", clear_on_submit=True):

    col1, col2 = st.columns(2)
    with col1:
        selected_label = st.selectbox("Joueur", options=list(player_options.keys()))
    with col2:
        session_date = st.date_input("Date", value=date.today(), max_value=date.today())

    col_sem, col_jour = st.columns(2)
    with col_sem:
        semaine = st.number_input(
            "Numéro de semaine",
            min_value=1, max_value=52, value=_get_week_number(session_date),
            help="Numéro de semaine de la saison (1 = première semaine)",
        )
    with col_jour:
        jour = st.selectbox(
            "Jour d'entraînement",
            options=JOURS_ENTRAINEMENT,
            index=1,  # Mardi par défaut
            help="Correspond aux colonnes Mardi / Mercredi / Vendredi / Jour de match",
        )

    st.markdown("---")
    st.subheader("Charge de séance")

    col3, col4, col5 = st.columns(3)
    with col3:
        rpe = st.select_slider(
            "RPE — Perception de l'effort (Borg CR-10)",
            options=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            value=5,
            format_func=lambda x: RPE_LABELS.get(x, str(x)),
        )
    with col4:
        duration = st.number_input(
            "Durée (minutes)", min_value=0, max_value=300, value=75, step=5
        )
    with col5:
        load = foster_load(rpe, duration)
        st.metric("Charge Foster (UA)", f"{load:.0f}")
        st.caption("RPE x Durée")

    st.markdown("---")
    st.subheader("Etat de bien-être")
    st.caption("1 = très mauvais · 5 = excellent")

    col6, col7, col8 = st.columns(3)
    with col6:
        fatigue = st.select_slider(
            "Fatigue générale",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: {1: "1 — Épuisé", 2: "2 — Fatigué",
                                    3: "3 — Normal", 4: "4 — Bien", 5: "5 — Excellent"}[x],
        )
    with col7:
        courbatures = st.select_slider(
            "Courbatures / douleurs",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: {1: "1 — Très douloureux", 2: "2 — Douloureux",
                                    3: "3 — Légères", 4: "4 — Minimes", 5: "5 — Aucune"}[x],
        )
    with col8:
        sommeil = st.select_slider(
            "Qualité du sommeil",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: {1: "1 — Très mauvais", 2: "2 — Mauvais",
                                    3: "3 — Moyen", 4: "4 — Bon", 5: "5 — Excellent"}[x],
        )

    avg_well = (fatigue + courbatures + sommeil) / 3
    well_color = (
        "OK" if avg_well >= 4 else
        "Correct" if avg_well >= 3 else
        "Dégradé" if avg_well >= 2 else
        "ALERTE"
    )
    st.markdown(f"**Score bien-être moyen :** **{avg_well:.1f} / 5** ({well_color})")

    st.markdown("---")
    
    # On présélectionne le groupe du joueur par défaut
    player_groupe = player_options[selected_label]["groupe"] if selected_label else "Groupe Élargi"
    groupe_index = 0
    if player_groupe == "Équipe B": groupe_index = 1
    elif player_groupe == "Groupe Élargi": groupe_index = 2
        
    groupe_entrainement = st.radio("Groupe d'entraînement du jour *", ["Équipe A", "Équipe B", "Groupe Élargi"], horizontal=True, index=groupe_index)

    st.markdown("---")
    notes = st.text_area(
        "Notes / Observations (optionnel)",
        placeholder="Ex: séance terrain, match amical, blessure légère...",
        height=80,
    )

    is_rest_day = st.checkbox(
        "Jour de repos (charge = 0, mais enregistrer le bien-être)",
        value=False,
    )

    submitted = st.form_submit_button(
        "Enregistrer la séance", type="primary", use_container_width=True
    )


# ── Traitement à la validation ──────────────────────────────────────────────────
if submitted:
    player_info     = player_options[selected_label]
    nom_prenom      = player_info["nom"]
    poste           = player_info["poste"]

    actual_rpe      = 0 if is_rest_day else rpe
    actual_duration = 0 if is_rest_day else duration
    actual_load     = 0.0 if is_rest_day else load

    with st.spinner("Enregistrement dans Google Sheets..."):
        try:
            # 1. Lecture de l'onglet Saisies actuel
            saisies_df = conn.read(worksheet="Saisies", ttl=0)
            
            # Formatage des notes
            notes_gs = f"[{groupe_entrainement}] {notes}" if notes.strip() else f"[{groupe_entrainement}]"
            
            # Formattage de la date pour correspondre à ton Google Sheets (ex: 24/09/2026 15:30)
            from datetime import datetime
            horodateur = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            # 2. Création de la nouvelle ligne
            new_row = pd.DataFrame([{
                "Cle de recherche": f"{semaine}{nom_prenom.replace(' ', '')}",
                "Horodateur": horodateur,
                "Difficulte seance": RPE_LABELS.get(actual_rpe, str(actual_rpe)),
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
            
            # 3. Ajout et sauvegarde
            updated_df = pd.concat([saisies_df, new_row], ignore_index=True)
            conn.update(worksheet="Saisies", data=updated_df)
            
            if is_rest_day:
                msg = f"Jour de repos enregistré pour **{selected_label}**."
            else:
                msg = (
                    f"Séance enregistrée pour **{selected_label}** — "
                    f"Charge : **{actual_load:.0f} UA** (RPE {actual_rpe} x {actual_duration} min)"
                )
            st.success(msg)
            
        except Exception as e:
            st.error(f"Erreur lors de l'enregistrement : {e}")

# ── Aide RPE ────────────────────────────────────────────────────────────────────
with st.expander("Echelle RPE de Borg CR-10"):
    st.markdown("""
    | RPE | Description |
    |-----|-------------|
    | 0   | Repos complet |
    | 1   | Très très facile |
    | 2   | Très facile |
    | 3   | Facile |
    | 4   | Effort modéré |
    | 5   | Effort moyen |
    | 6   | Effort un peu difficile |
    | 7   | Difficile |
    | 8   | Très difficile |
    | 9   | Très très difficile |
    | 10  | Maximal |
    """)
