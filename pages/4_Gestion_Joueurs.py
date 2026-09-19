"""
pages/4_Gestion_Joueurs.py
Gestion de l'effectif : ajout, modification et suppression de joueurs.
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules.database import get_players, add_player, delete_player, update_player

st.set_page_config(page_title="Gestion Joueurs", page_icon="⚙️", layout="wide")

st.title("⚙️ Gestion de l'effectif")

POSTES_RUGBY = [
    "Pilier",
    "Talonneur",
    "2ème ligne",
    "3ème ligne",
    "Demi de mêlée",
    "Demi d'ouverture",
    "Centre",
    "Ailier",
    "Arrière",
]

GROUPES = ["Groupe Élargi", "Équipe A", "Équipe B"]

# ── LISTE DES JOUEURS ────────────────────────────────────────────────────────────
st.subheader("📋 Effectif actuel")
players_df = get_players()

if players_df.empty:
    st.info("Aucun joueur enregistré.")
else:
    # Tableau affichage simplifié
    st.dataframe(
        players_df[["prenom", "nom", "poste", "groupe"]],
        use_container_width=True,
        hide_index=True
    )
st.markdown(f"**Total : {len(players_df)} joueur(s)**")
st.markdown("---")

# ── MODIFICATION D'UN JOUEUR ─────────────────────────────────────────────────────
st.subheader("✏️ Modifier / Supprimer un joueur")
if not players_df.empty:
    player_options = {
        f"{row['prenom']} {row['nom']} ({row['poste']})": row
        for _, row in players_df.iterrows()
    }
    selected_label = st.selectbox("Sélectionner un joueur", options=list(player_options.keys()))
    selected_player = player_options[selected_label]

    with st.form("edit_player_form"):
        col1, col2 = st.columns(2)
        with col1:
            edit_prenom = st.text_input("Prénom", value=selected_player["prenom"])
            
            # Gestion du poste qui pourrait ne pas être dans la liste stricte (ex: anciens)
            default_poste_idx = 0
            if selected_player["poste"] in POSTES_RUGBY:
                default_poste_idx = POSTES_RUGBY.index(selected_player["poste"])
            edit_poste = st.selectbox("Poste", POSTES_RUGBY, index=default_poste_idx)

        with col2:
            edit_nom = st.text_input("Nom", value=selected_player["nom"])
            
            default_groupe_idx = 0
            if selected_player.get("groupe") in GROUPES:
                default_groupe_idx = GROUPES.index(selected_player["groupe"])
            edit_groupe = st.selectbox("Groupe d'appartenance", GROUPES, index=default_groupe_idx)

        col_save, col_del = st.columns([1, 1])
        with col_save:
            btn_save = st.form_submit_button("💾 Enregistrer les modifications", type="primary")
        with col_del:
            btn_del = st.form_submit_button("🗑️ Supprimer ce joueur")

        if btn_save:
            update_player(
                selected_player["id"], 
                edit_nom.strip().upper(), 
                edit_prenom.strip().capitalize(), 
                edit_poste, 
                edit_groupe
            )
            st.success(f"✅ Profil de {edit_prenom.capitalize()} {edit_nom.upper()} mis à jour.")
            st.rerun()

        if btn_del:
            delete_player(selected_player["id"])
            st.warning(f"⚠️ {edit_prenom.capitalize()} {edit_nom.upper()} supprimé(e).")
            st.rerun()

st.markdown("---")

# ── AJOUT D'UN JOUEUR ────────────────────────────────────────────────────────────
st.subheader("➕ Ajouter un joueur")

with st.form("add_player_form"):
    col_a, col_b = st.columns(2)
    with col_a:
        prenom = st.text_input("Prénom *", placeholder="Antoine")
        poste  = st.selectbox("Poste *", POSTES_RUGBY)
    with col_b:
        nom    = st.text_input("Nom *", placeholder="Dupont")
        groupe = st.selectbox("Groupe", GROUPES, index=0)

    submitted = st.form_submit_button("➕ Ajouter le joueur", type="secondary")

    if submitted:
        if not nom.strip() or not prenom.strip():
            st.error("Le nom et le prénom sont obligatoires.")
        else:
            # We pass 0 or None for number as it was removed from UI context essentially, but signature expects it. 
            # Or we can just use 0.
            add_player(nom.strip().upper(), prenom.strip().capitalize(), poste, 0, groupe)
            st.success(f"✅ {prenom.capitalize()} {nom.upper()} ajouté(e) au poste de {poste}.")
            st.rerun()
