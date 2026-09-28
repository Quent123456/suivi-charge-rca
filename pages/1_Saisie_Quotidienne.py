"""
pages/1_Saisie_Quotidienne.py
Formulaire de saisie quotidienne : RPE × Durée + bien-être.
Écrit simultanément dans SQLite (local) ET Google Sheets.
"""

import streamlit as st
from datetime import date
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules.database import get_players, add_session
from modules.calculations import foster_load
from modules.gsheets import (
    append_saisie_row,
    update_rpe_indv,
    update_rpe_par_ligne_semaine,
    is_configured,
    init_sheets,
    JOURS_ENTRAINEMENT,
    RPE_LABELS,
)

st.set_page_config(page_title="Saisie Quotidienne", page_icon="📝", layout="centered")

st.title("Saisie Quotidienne")
st.markdown("Enregistrez la séance d'entraînement et le ressenti de chaque joueur.")

# ── Statut Google Sheets ────────────────────────────────────────────────────────
gsheets_ok = is_configured()

if gsheets_ok:
    st.success(
        "Google Sheets connecté — Les données seront enregistrées dans "
        "**Test - Suivi Charge RCA Amiens**"
    )
else:
    st.warning(
        "Google Sheets non configuré. Les données seront enregistrées "
        "**uniquement en local** (SQLite). "
        "Consultez l'onglet **Configuration Google Sheets** pour activer la synchronisation."
    )

# ── Chargement des joueurs ──────────────────────────────────────────────────────
players_df = get_players()

if players_df.empty:
    st.warning("Aucun joueur enregistré. Ajoutez des joueurs dans **Gestion des Joueurs**.")
    st.stop()

# ── Initialisation du Session State ─────────────────────────────────────────────
JOURS_SEMAINE_MAP = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


def _get_week_number(d) -> int:
    """Calcule le numéro de semaine ISO."""
    try:
        return d.isocalendar()[1]
    except Exception:
        return 1


today = date.today()

if "saved_duration" not in st.session_state:
    st.session_state["saved_duration"] = 75
if "saved_groupe" not in st.session_state:
    st.session_state["saved_groupe"] = "Équipe A"
if "submitted_players" not in st.session_state:
    st.session_state["submitted_players"] = []
if "form_id" not in st.session_state:
    st.session_state["form_id"] = 0
if "last_submission" not in st.session_state:
    st.session_state["last_submission"] = None

# Synchronisation initiale de la date et du jour
if "session_date_widget" not in st.session_state:
    st.session_state["session_date_widget"] = today
if "session_jour_widget" not in st.session_state:
    st.session_state["session_jour_widget"] = JOURS_SEMAINE_MAP[today.weekday()]
if "session_semaine_widget" not in st.session_state:
    st.session_state["session_semaine_widget"] = _get_week_number(today)


def _on_date_change():
    """Met à jour automatiquement le jour et la semaine quand la date change."""
    d = st.session_state["session_date_widget"]
    st.session_state["session_jour_widget"] = JOURS_SEMAINE_MAP[d.weekday()]
    st.session_state["session_semaine_widget"] = _get_week_number(d)


# ── Formatage et Tri alphabétique des joueurs ───────────────────────────────────
# Format : NOM Prénom — Poste (avec le NOM de famille en majuscules)
# Tri : Strictement alphabétique (par Nom, puis Prénom)
all_players = []
for _, row in players_df.iterrows():
    nom_upper = str(row["nom"]).strip().upper()
    prenom = str(row["prenom"]).strip()
    poste = str(row["poste"]).strip()
    label = f"{nom_upper} {prenom} — {poste}"
    nom_prenom = f"{nom_upper} {prenom}"
    all_players.append({
        "id": row["id"],
        "nom_upper": nom_upper,
        "prenom": prenom,
        "nom_prenom": nom_prenom,
        "poste": poste,
        "label": label,
    })

# Tri strict par Nom majuscule, puis Prénom insensible à la casse
all_players.sort(key=lambda x: (x["nom_upper"], x["prenom"].lower()))

# ── Message de confirmation après enregistrement précédent ──────────────────────
if st.session_state.get("last_submission"):
    last = st.session_state["last_submission"]
    if last["is_rest_day"]:
        st.success(f"Jour de repos enregistré pour **{last['player_label']}** le {last['session_date']}.")
    else:
        st.success(
            f"Séance enregistrée pour **{last['player_label']}** — "
            f"Semaine {last['semaine']}, {last['jour']} — "
            f"Charge : **{last['actual_load']:.0f} UA** (RPE {last['actual_rpe']} x {last['actual_duration']} min)"
        )
    if last["gsheets_ok"]:
        if last["gs_success"]:
            st.info("Google Sheets mis à jour : onglets **Saisies** + **RPE INDV** + **RPE PAR LIGNE SEMAINE**")
        else:
            st.warning("Enregistrement local OK, mais erreur lors de la synchronisation Google Sheets.")
    if last["avg_well"] <= 2.5:
        st.warning(f"Score bien-être faible ({last['avg_well']:.1f}/5). Pensez à adapter la charge.")

# ── Paramètres généraux de la séance (Date, Semaine, Jour) ──────────────────────
st.markdown("### 1. Paramètres de la séance")
col_date, col_sem, col_jour = st.columns([1.5, 1, 1.5])
with col_date:
    session_date = st.date_input(
        "Date",
        value=today,
        key="session_date_widget",
        on_change=_on_date_change,
        help="Modifier la date met à jour automatiquement le jour et la semaine.",
    )
with col_sem:
    semaine = st.number_input(
        "Numéro de semaine",
        min_value=1,
        max_value=52,
        key="session_semaine_widget",
        help="Numéro de semaine de la saison (1 = première semaine)",
    )
with col_jour:
    jour = st.selectbox(
        "Jour d'entraînement",
        options=JOURS_ENTRAINEMENT,
        key="session_jour_widget",
        help="Correspond aux colonnes Mardi / Mercredi / Vendredi / Jour de match",
    )

st.markdown("---")

# ── Sélection du joueur (Recherche dynamique + Retrait temporaire) ───────────────
st.markdown("### 2. Sélection du joueur")

col_search, col_reset = st.columns([3, 1.5], vertical_alignment="bottom")
with col_search:
    search_query = st.text_input(
        "Rechercher un joueur",
        placeholder="Tapez un nom ou un prénom...",
        key="search_query_input",
        help="Filtrage dynamique en temps réel insensible à la casse",
    )
with col_reset:
    if st.button("🔄 Réinitialiser la liste", use_container_width=True, help="Réinitialise la liste pour réafficher l'ensemble de l'effectif"):
        st.session_state["submitted_players"] = []
        st.session_state["last_submission"] = None
        st.rerun()

# Filtrage : exclusion des joueurs déjà saisis + recherche textuelle
query_clean = search_query.strip().lower()
available_players = [
    p for p in all_players
    if p["nom_prenom"] not in st.session_state["submitted_players"]
    and (not query_clean or query_clean in p["nom_upper"].lower() or query_clean in p["prenom"].lower() or query_clean in p["poste"].lower())
]

nb_total = len(all_players)
nb_submitted = len(st.session_state["submitted_players"])
nb_restants = len(available_players)

if nb_submitted > 0:
    st.caption(f"👥 **{nb_restants}** joueur(s) disponible(s) · **{nb_submitted}** déjà enregistré(s) sur **{nb_total}** au total")

if not available_players:
    if nb_submitted >= nb_total:
        st.info("🎉 **Tous les joueurs ont été saisis pour cette séance !**")
        st.markdown("Cliquez sur **🔄 Réinitialiser la liste** ci-dessus pour réafficher tout l'effectif si vous souhaitez modifier ou ajouter des données.")
    else:
        st.warning(f"🔍 Aucun joueur ne correspond à la recherche : *« {search_query} »*.")
    st.stop()

player_options = {p["label"]: p for p in available_players}
selected_label = st.selectbox(
    "Joueur à saisir",
    options=list(player_options.keys()),
    help="Sélectionnez le joueur dans la liste filtrée",
)
selected_player = player_options[selected_label]

st.markdown("---")

# ── Formulaire de saisie ────────────────────────────────────────────────────────
st.markdown("### 3. Évaluation de la séance")

fid = st.session_state["form_id"]
with st.form("saisie_form", clear_on_submit=False):

    st.subheader("Charge de séance")
    col3, col4, col5 = st.columns(3)
    with col3:
        rpe = st.select_slider(
            "RPE — Perception de l'effort (Borg CR-10)",
            options=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            value=5,
            format_func=lambda x: RPE_LABELS.get(x, str(x)),
            key=f"rpe_input_{fid}",
        )
    with col4:
        duration = st.number_input(
            "Durée (minutes)",
            min_value=0,
            max_value=300,
            value=int(st.session_state["saved_duration"]),
            step=5,
            key=f"duration_input_{fid}",
            help="Cette valeur est conservée d'un joueur à l'autre.",
        )
    with col5:
        preview_load = foster_load(rpe, duration)
        st.metric("Charge Foster estimée (UA)", f"{preview_load:.0f}")
        st.caption("Calculée : RPE × Durée")

    st.markdown("---")
    st.subheader("État de bien-être")
    st.caption("1 = très mauvais · 5 = excellent")

    col6, col7, col8 = st.columns(3)
    with col6:
        fatigue = st.select_slider(
            "Fatigue générale",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: {1: "1 — Épuisé", 2: "2 — Fatigué",
                                    3: "3 — Normal", 4: "4 — Bien", 5: "5 — Excellent"}[x],
            key=f"fatigue_input_{fid}",
        )
    with col7:
        courbatures = st.select_slider(
            "Courbatures / douleurs",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: {1: "1 — Très douloureux", 2: "2 — Douloureux",
                                    3: "3 — Légères", 4: "4 — Minimes", 5: "5 — Aucune"}[x],
            key=f"courbatures_input_{fid}",
        )
    with col8:
        sommeil = st.select_slider(
            "Qualité du sommeil",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: {1: "1 — Très mauvais", 2: "2 — Mauvais",
                                    3: "3 — Moyen", 4: "4 — Bon", 5: "5 — Excellent"}[x],
            key=f"sommeil_input_{fid}",
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
    group_options = ["Équipe A", "Équipe B", "Groupe Élargi"]
    current_saved_group = st.session_state["saved_groupe"]
    group_idx = group_options.index(current_saved_group) if current_saved_group in group_options else 0

    groupe_entrainement = st.radio(
        "Groupe d'entraînement du jour *",
        group_options,
        index=group_idx,
        horizontal=True,
        key=f"groupe_input_{fid}",
        help="Cette sélection est conservée d'un joueur à l'autre.",
    )

    st.markdown("---")
    notes = st.text_area(
        "Notes / Observations (optionnel)",
        placeholder="Ex: séance terrain, match amical, blessure légère...",
        height=80,
        key=f"notes_input_{fid}",
    )

    is_rest_day = st.checkbox(
        "Jour de repos (charge = 0, mais enregistrer le bien-être)",
        value=False,
        key=f"rest_input_{fid}",
    )

    submitted = st.form_submit_button(
        "Enregistrer la séance", type="primary", use_container_width=True
    )


# ── Traitement à la validation ──────────────────────────────────────────────────
if submitted:
    player_id       = selected_player["id"]
    nom_prenom      = selected_player["nom_prenom"]
    poste           = selected_player["poste"]

    actual_rpe      = 0 if is_rest_day else rpe
    actual_duration = 0 if is_rest_day else duration
    actual_load     = 0.0 if is_rest_day else foster_load(actual_rpe, actual_duration)

    # 1. Enregistrement SQLite local (toujours)
    add_session(
        player_id=player_id,
        session_date=str(session_date),
        rpe=actual_rpe,
        duration=actual_duration,
        foster_load=actual_load,
        fatigue=fatigue,
        courbatures=courbatures,
        sommeil=sommeil,
        notes=notes,
        groupe_entrainement=groupe_entrainement,
    )

    # 2. Enregistrement Google Sheets (si configuré)
    gs_success = False
    if gsheets_ok:
        with st.spinner("Synchronisation Google Sheets..."):
            # Initialisation des onglets si première utilisation
            init_sheets()

            # Ajout du groupe dans les notes pour Google Sheets
            notes_gs = f"[{groupe_entrainement}] {notes}" if notes.strip() else f"[{groupe_entrainement}]"

            # Onglet Saisies → nouvelle ligne
            try:
                ok1 = append_saisie_row(
                    nom_prenom=nom_prenom,
                    poste=poste,
                    semaine=int(semaine),
                    jour=jour,
                    rpe=actual_rpe,
                    duree=actual_duration,
                    charge=actual_load,
                    fatigue=fatigue,
                    courbatures=courbatures,
                    sommeil=sommeil,
                    notes=notes_gs,
                    is_rest=is_rest_day,
                )
            except Exception:
                ok1 = False

            # Onglet RPE INDV → mise à jour cellule
            try:
                ok2 = True
                if not is_rest_day and jour in ["Mardi", "Mercredi", "Vendredi", "Jour de match"]:
                    ok2 = update_rpe_indv(
                        nom_prenom=nom_prenom,
                        poste=poste,
                        semaine=int(semaine),
                        jour=jour,
                        rpe=actual_rpe,
                        duree=actual_duration,
                        charge=actual_load,
                    )
            except Exception:
                ok2 = False

            # Onglet RPE PAR LIGNE SEMAINE → agrégats par poste
            try:
                ok3 = True
                if not is_rest_day:
                    ok3 = update_rpe_par_ligne_semaine(
                        poste=poste,
                        semaine=int(semaine),
                        nom_prenom=nom_prenom,
                        rpe=actual_rpe,
                        duree=actual_duration,
                        charge=actual_load,
                    )
            except Exception:
                ok3 = False

            gs_success = ok1 and ok2 and ok3

    # 3. Mise à jour de l'état pour la persistance et l'exclusion
    st.session_state["saved_duration"] = int(duration)
    st.session_state["saved_groupe"] = groupe_entrainement
    st.session_state["submitted_players"].append(nom_prenom)
    st.session_state["last_submission"] = {
        "is_rest_day": is_rest_day,
        "player_label": selected_label,
        "session_date": str(session_date),
        "semaine": int(semaine),
        "jour": jour,
        "actual_load": actual_load,
        "actual_rpe": actual_rpe,
        "actual_duration": actual_duration,
        "gsheets_ok": gsheets_ok,
        "gs_success": gs_success,
        "avg_well": avg_well,
    }
    # Réinitialisation manuelle du RPE et du bien-être en incrémentant l'ID de formulaire
    st.session_state["form_id"] += 1

    st.rerun()

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
