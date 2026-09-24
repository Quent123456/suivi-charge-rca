"""
pages/4_Gestion_Joueurs.py
Gestion de l'effectif : ajout, modification et suppression de joueurs sur Google Sheets.
"""

import streamlit as st
import pandas as pd
import uuid
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestion Joueurs", page_icon="⚙️", layout="wide")

st.title("⚙️ Gestion de l'effectif")

# ── INITIALISATION CONNEXION GOOGLE SHEETS ───────────────────────────────────────
# Établir la connexion sécurisée via les secrets Streamlit
conn = st.connection("gsheets", type=GSheetsConnection)

# Fonction pour télécharger la liste à jour
def load_players():
    try:
        df = conn.read(worksheet="Effectif")
        # Retirer les lignes totalement vides de Google Sheets
        df = df.dropna(how="all")
        # S'assurer que les identifiants sont bien en texte
        df['id'] = df['id'].astype(str)
        return df
    except Exception:
        # Si l'onglet est vide ou mal lu, on crée un tableau vide avec les bonnes colonnes
        return pd.DataFrame(columns=["id", "nom", "prenom", "poste", "numero", "groupe"])

players_df = load_players()

POSTES_RUGBY = [
    "Pilier", "Talonneur", "2ème ligne", "3ème ligne",
    "Demi de mêlée", "Demi d'ouverture", "Centre", "Ailier", "Arrière",
]

GROUPES = ["Groupe Élargi", "Équipe A", "Équipe B"]

# ── LISTE DES JOUEURS ────────────────────────────────────────────────────────────
st.subheader("📋 Effectif actuel")

if players_df.empty:
    st.info("Aucun joueur enregistré dans la base de données Google Sheets.")
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
            # Mettre à jour la ligne correspondante dans le dataframe
            idx = players_df.index[players_df['id'] == selected_player['id']].tolist()[0]
            players_df.at[idx, 'nom'] = edit_nom.strip().upper()
            players_df.at[idx, 'prenom'] = edit_prenom.strip().capitalize()
            players_df.at[idx, 'poste'] = edit_poste
            players_df.at[idx, 'groupe'] = edit_groupe
            
            # Envoyer le tableau mis à jour vers Google Sheets
            conn.update(worksheet="Effectif", data=players_df)
            st.cache_data.clear() # Vider la mémoire cache
            
            st.success(f"✅ Profil de {edit_prenom.capitalize()} {edit_nom.upper()} mis à jour.")
            st.rerun()

        if btn_del:
            # Filtrer le tableau pour retirer le joueur sélectionné
            updated_df = players_df[players_df['id'] != selected_player['id']]
            
            # Envoyer le nouveau tableau vers Google Sheets
            conn.update(worksheet="Effectif", data=updated_df)
            st.cache_data.clear() # Vider la mémoire cache
            
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
            # Créer une nouvelle ligne de données avec un ID unique généré automatiquement
            new_player = pd.DataFrame([{
                "id": str(uuid.uuid4()),
                "nom": nom.strip().upper(),
                "prenom": prenom.strip().capitalize(),
                "poste": poste,
                "numero": 0,
                "groupe": groupe
            }])
            
            # Ajouter la nouvelle ligne au tableau existant
            updated_df = pd.concat([players_df, new_player], ignore_index=True)
            
            # Envoyer la fusion vers Google Sheets
            conn.update(worksheet="Effectif", data=updated_df)
            st.cache_data.clear() # Vider la mémoire cache pour forcer la relecture
            
            st.success(f"✅ {prenom.capitalize()} {nom.upper()} ajouté(e) au poste de {poste}.")
            st.rerun()
