"""
pages/3_Tableau_Collectif.py
Dashboard collectif connecté à Google Sheets : heatmap ACWR équipe, tableau de risque, export CSV.
"""

import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

from modules.calculations import compute_team_acwr_snapshot
from modules.alerts import acwr_alert, acwr_color
from modules.visualizations import plot_team_heatmap

st.set_page_config(page_title="Tableau Collectif", page_icon="👥", layout="wide")

st.title("👥 Tableau de bord collectif")
st.markdown("Vue d'ensemble de la charge et du risque pour tout l'effectif.")

# ── Connexion à Google Sheets ──────────────────────────────────────────────────
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    sessions_df = conn.read(worksheet="Saisies", ttl=0)
    sessions_df = sessions_df.dropna(how="all")
except Exception as e:
    st.error(f"Erreur de connexion à Google Sheets : {e}")
    st.stop()

# ── FILTRE DE GROUPE ────────────────────────────────────────────────────────────
filtre_groupe = st.radio(
    "Filtrer l'affichage (basé sur le groupe d'entraînement sélectionné lors des saisies) :",
    ["Générale", "Équipe A", "Équipe B", "Groupe Élargi"],
    horizontal=True
)

# ── Chargement et Nettoyage des données ────────────────────────────────────────
if sessions_df.empty:
    st.info("Aucune donnée disponible. Saisissez des séances dans **Saisie Quotidienne**.")
    st.stop()

df_raw = sessions_df.copy()

try:
    # Dates et Valeurs
    df_raw["session_date"] = pd.to_datetime(df_raw["Horodateur"], format='mixed', dayfirst=True).dt.normalize()
    df_raw["foster_load"] = pd.to_numeric(df_raw["Charge (UA)"], errors='coerce').fillna(0)
    df_raw["player_name"] = df_raw["Nom / Prenom"]
    df_raw["poste"] = df_raw["Poste"]
    
    # Extraction du groupe d'entraînement depuis les notes (ex: "[Équipe A] match amical")
    df_raw["groupe_entrainement"] = df_raw["Ressenti / Notes"].str.extract(r'\[(.*?)\]')[0]
    df_raw["groupe_entrainement"] = df_raw["groupe_entrainement"].fillna("Groupe Élargi")

    # Extraction des scores de bien-être
    def extract_wellness(row_text, key):
        if pd.isna(row_text): return None
        try:
            for p in str(row_text).split("|"):
                if key in p: return float(p.split(":")[1].strip())
        except: pass
        return None

    df_raw["fatigue"] = df_raw["Fatigue | Courbatures | Sommeil"].apply(lambda x: extract_wellness(x, "Fatigue"))
    df_raw["courbatures"] = df_raw["Fatigue | Courbatures | Sommeil"].apply(lambda x: extract_wellness(x, "Courbatures"))
    df_raw["sommeil"] = df_raw["Fatigue | Courbatures | Sommeil"].apply(lambda x: extract_wellness(x, "Sommeil"))
    
    # Tri par date
    df_raw = df_raw.sort_values(by="session_date")

except Exception as e:
    st.error(f"Erreur lors du formatage des données : {e}")
    st.stop()

# Filtrer sur les 35 derniers jours (comme l'ancienne fonction SQLite)
min_date = pd.Timestamp.now().normalize() - pd.Timedelta(days=35)
sessions_all = df_raw[df_raw["session_date"] >= min_date].copy()

# Appliquer le filtre de groupe si nécessaire
if filtre_groupe != "Générale" and not sessions_all.empty:
    sessions_all = sessions_all[sessions_all["groupe_entrainement"] == filtre_groupe]

if sessions_all.empty or sessions_all["foster_load"].sum() == 0:
    st.info(f"Aucune donnée d'entraînement pour la période ou le groupe sélectionné.")
    st.stop()

# ── SNAPSHOT ÉQUIPE ─────────────────────────────────────────────────────────────
snapshot = compute_team_acwr_snapshot(sessions_all)

# ── KPI COLLECTIFS ──────────────────────────────────────────────────────────────
st.subheader("📊 Résumé de l'effectif")

n_total   = len(snapshot)
n_danger  = (snapshot["ACWR"] > 1.5).sum()
n_warning = ((snapshot["ACWR"] >= 1.3) & (snapshot["ACWR"] <= 1.5)).sum()
n_optimal = ((snapshot["ACWR"] >= 0.8) & (snapshot["ACWR"] < 1.3)).sum()
n_under   = (snapshot["ACWR"] < 0.8).sum()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("👥 Effectif", n_total)
k2.metric("🟢 Zone optimale", n_optimal)
k3.metric("🟠 Vigilance",     n_warning)
k4.metric("🔴 Risque élevé",  n_danger)
k5.metric("🔵 Sous-charge",   n_under)

if n_danger > 0:
    joueurs_danger = snapshot[snapshot["ACWR"] > 1.5]["Joueur"].tolist()
    st.error(f"⚠️ **{n_danger} joueur(s) en zone rouge** : {', '.join(joueurs_danger)}")

if n_warning > 0:
    joueurs_warn = snapshot[(snapshot["ACWR"] >= 1.3) & (snapshot["ACWR"] <= 1.5)]["Joueur"].tolist()
    st.warning(f"🟠 **{n_warning} joueur(s) en vigilance** : {', '.join(joueurs_warn)}")

st.markdown("---")

# ── HEATMAP ─────────────────────────────────────────────────────────────────────
st.subheader("🗓️ Heatmap ACWR — 14 derniers jours")
fig_heatmap = plot_team_heatmap(snapshot, sessions_all)
st.plotly_chart(fig_heatmap, use_container_width=True)

st.markdown("---")

# ── TABLEAU DE RISQUE ────────────────────────────────────────────────────────────
st.subheader("📋 Tableau de risque — Effectif complet")

# Ajout colonne Niveau de risque
def format_risk(row):
    alert = acwr_alert(row["ACWR"])
    return f"{alert.emoji} {alert.label}"

snapshot_display = snapshot.copy()
snapshot_display["Risque"] = snapshot_display.apply(format_risk, axis=1)

# Tri par ACWR décroissant
snapshot_display = snapshot_display.sort_values("ACWR", ascending=False, na_position="last")

# Formatage
for col in ["ACWR", "Monotonie"]:
    snapshot_display[col] = snapshot_display[col].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
    )
for col in ["Charge aiguë (7j)", "Charge chronique (28j)", "Contrainte"]:
    snapshot_display[col] = snapshot_display[col].apply(
        lambda x: f"{x:.0f} UA" if pd.notna(x) else "N/A"
    )
snapshot_display["Bien-être /5"] = snapshot_display["Bien-être /5"].apply(
    lambda x: f"{x:.1f}/5" if pd.notna(x) else "N/A"
)

display_cols = ["Joueur", "Poste", "Risque", "ACWR",
                "Charge aiguë (7j)", "Charge chronique (28j)",
                "Monotonie", "Contrainte", "Bien-être /5"]

st.dataframe(
    snapshot_display[display_cols].reset_index(drop=True),
    use_container_width=True,
    hide_index=True,
)

# ── EXPORT CSV ──────────────────────────────────────────────────────────────────
col_exp1, col_exp2 = st.columns(2)
with col_exp1:
    csv_snap = snapshot_display[display_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Exporter snapshot équipe (CSV)",
        data=csv_snap,
        file_name="snapshot_equipe.csv",
        mime="text/csv",
    )
with col_exp2:
    # Pour l'export complet, on nettoie un peu le df
    export_cols = ["Horodateur", "Nom / Prenom", "Poste", "groupe_entrainement", 
                   "Charge (UA)", "RPE (Chiffre)", "Duree (min)", "Ressenti / Notes", "Fatigue | Courbatures | Sommeil"]
    csv_all = sessions_all[export_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Exporter toutes les sessions (CSV)",
        data=csv_all,
        file_name="sessions_equipe_completes.csv",
        mime="text/csv",
    )

# ── VUE PAR POSTE ───────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("📌 Vue par poste"):
    postes = snapshot["Poste"].unique()
    for poste in sorted(postes):
        st.markdown(f"**{poste}**")
        poste_df = snapshot_display[snapshot_display["Poste"] == poste][display_cols]
        st.dataframe(poste_df.reset_index(drop=True), use_container_width=True, hide_index=True)
