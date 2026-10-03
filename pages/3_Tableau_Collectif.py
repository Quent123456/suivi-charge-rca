"""
pages/3_Tableau_Collectif.py
Dashboard collectif connecté à Google Sheets : heatmap ACWR équipe, tableau de risque, RPE dynamique, export CSV.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

from modules.calculations import compute_team_acwr_snapshot
from modules.alerts import acwr_alert, acwr_color
from modules.visualizations import plot_team_heatmap

st.set_page_config(page_title="Tableau Collectif", page_icon="👥", layout="wide")

st.title("👥 Tableau de bord collectif")
st.markdown("Vue d'ensemble de la charge, du risque et de la perception de l'effort (RPE) pour tout l'effectif.")

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
    "Filtrer l'affichage (basé sur le groupe d'entraînement) :",
    ["Générale", "Équipe A", "Équipe B", "Groupe Élargi"],
    horizontal=True
)

# ── Chargement et Nettoyage des données ────────────────────────────────────────
if sessions_df.empty:
    st.info("Aucune donnée disponible. Saisissez des séances dans **Saisie Quotidienne**.")
    st.stop()

df_raw = sessions_df.copy()

try:
    df_raw["session_date"] = pd.to_datetime(df_raw["Horodateur"], format='mixed', dayfirst=True).dt.normalize()
    df_raw["foster_load"] = pd.to_numeric(df_raw["Charge (UA)"], errors='coerce').fillna(0)
    df_raw["rpe"] = pd.to_numeric(df_raw["RPE (Chiffre)"], errors='coerce').fillna(0)
    df_raw["player_name"] = df_raw["Nom / Prenom"]
    df_raw["player_id"] = df_raw["Nom / Prenom"] 
    df_raw["poste"] = df_raw["Poste"]
    
    df_raw["groupe_entrainement"] = df_raw["Ressenti / Notes"].str.extract(r'\[(.*?)\]')[0]
    df_raw["groupe_entrainement"] = df_raw["groupe_entrainement"].fillna("Groupe Élargi")

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
    
    df_raw = df_raw.sort_values(by="session_date")

except Exception as e:
    st.error(f"Erreur lors du formatage des données : {e}")
    st.stop()

# Filtrer sur les 35 derniers jours pour l'ACWR
min_date = pd.Timestamp.now().normalize() - pd.Timedelta(days=35)
sessions_all = df_raw[df_raw["session_date"] >= min_date].copy()

if filtre_groupe != "Générale" and not sessions_all.empty:
    sessions_all = sessions_all[sessions_all["groupe_entrainement"] == filtre_groupe]

if sessions_all.empty or sessions_all["foster_load"].sum() == 0:
    st.info(f"Aucune donnée d'entraînement pour la période ou le groupe sélectionné.")
    st.stop()

# ── SNAPSHOT ÉQUIPE ─────────────────────────────────────────────────────────────
snapshot = compute_team_acwr_snapshot(sessions_all)

# ── CALCUL DES MOYENNES RPE (AVEC FILTRE DYNAMIQUE) ─────────────────────────────
st.markdown("---")
st.subheader("⏱️ Analyse de la Perception de l'Effort (RPE)")

periode_rpe = st.radio(
    "Sélectionnez la période pour le calcul du RPE moyen :", 
    [7, 14, 28], 
    format_func=lambda x: f"{x} derniers jours", 
    horizontal=True
)

# Isoler les X derniers jours et exclure les RPE à 0
last_period = sessions_all[sessions_all["session_date"] >= (pd.Timestamp.now().normalize() - pd.Timedelta(days=periode_rpe))]
rpe_data = last_period[last_period["rpe"] > 0]

# Moyenne RPE par joueur
rpe_joueur = rpe_data.groupby("player_name")["rpe"].mean().reset_index()
nom_col_rpe = f"RPE Moyen ({periode_rpe}j)"
rpe_joueur.columns = ["Joueur", nom_col_rpe]

# Intégrer au snapshot
snapshot_display = snapshot.copy()
snapshot_display = pd.merge(snapshot_display, rpe_joueur, on="Joueur", how="left")

# ── KPI COLLECTIFS ──────────────────────────────────────────────────────────────
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

# ── GRAPHIQUE : ÉVOLUTION DU RPE ────────────────────────────────────────────────
st.subheader("📈 Évolution chronologique du RPE")

filtre_graph = st.radio("Niveau d'analyse du graphique :", ["Toute l'équipe", "Par Poste", "Par Joueur"], horizontal=True)

df_graph_rpe = sessions_all[sessions_all["rpe"] > 0].copy()

if not df_graph_rpe.empty:
    if filtre_graph == "Toute l'équipe":
        df_grp = df_graph_rpe.groupby("session_date")["rpe"].mean().reset_index()
        fig_rpe = px.line(df_grp, x="session_date", y="rpe", markers=True, title="Moyenne RPE - Équipe entière")
    elif filtre_graph == "Par Poste":
        selected_poste = st.selectbox("Sélectionner un poste :", sorted(df_graph_rpe["poste"].unique()))
        df_grp = df_graph_rpe[df_graph_rpe["poste"] == selected_poste].groupby("session_date")["rpe"].mean().reset_index()
        fig_rpe = px.line(df_grp, x="session_date", y="rpe", markers=True, title=f"Moyenne RPE - {selected_poste}")
    else:
        selected_player = st.selectbox("Sélectionner un joueur :", sorted(df_graph_rpe["player_name"].unique()))
        df_grp = df_graph_rpe[df_graph_rpe["player_name"] == selected_player].groupby("session_date")["rpe"].mean().reset_index()
        fig_rpe = px.line(df_grp, x="session_date", y="rpe", markers=True, title=f"RPE - {selected_player}")
    
    fig_rpe.update_layout(yaxis_title="RPE (0-10)", xaxis_title="Date", yaxis=dict(range=[0, 10]))
    fig_rpe.update_traces(line_color="#e67e22", line_width=3, marker=dict(size=8))
    st.plotly_chart(fig_rpe, use_container_width=True)
else:
    st.info("Pas assez de données de RPE pour générer le graphique.")

st.markdown("---")

# ── HEATMAP ─────────────────────────────────────────────────────────────────────
st.subheader("🗓️ Heatmap ACWR — 14 derniers jours")
fig_heatmap = plot_team_heatmap(snapshot, sessions_all)
st.plotly_chart(fig_heatmap, use_container_width=True)

st.markdown("---")

# ── TABLEAU DE RISQUE ────────────────────────────────────────────────────────────
st.subheader("📋 Tableau de risque — Effectif complet")

def format_risk(row):
    alert = acwr_alert(row["ACWR"])
    return f"{alert.emoji} {alert.label}"

snapshot_display["Risque"] = snapshot_display.apply(format_risk, axis=1)
snapshot_display = snapshot_display.sort_values("ACWR", ascending=False, na_position="last")

for col in ["ACWR", "Monotonie"]:
    snapshot_display[col] = snapshot_display[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
for col in ["Charge aiguë (7j)", "Charge chronique (28j)", "Contrainte"]:
    snapshot_display[col] = snapshot_display[col].apply(lambda x: f"{x:.0f} UA" if pd.notna(x) else "N/A")
snapshot_display["Bien-être /5"] = snapshot_display["Bien-être /5"].apply(lambda x: f"{x:.1f}/5" if pd.notna(x) else "N/A")
snapshot_display[nom_col_rpe] = snapshot_display[nom_col_rpe].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")

display_cols = ["Joueur", "Poste", nom_col_rpe, "Risque", "ACWR", "Charge aiguë (7j)", "Charge chronique (28j)", "Monotonie", "Contrainte", "Bien-être /5"]

st.dataframe(snapshot_display[display_cols].reset_index(drop=True), use_container_width=True, hide_index=True)

# ── EXPORT CSV ──────────────────────────────────────────────────────────────────
col_exp1, col_exp2 = st.columns(2)
with col_exp1:
    csv_snap = snapshot_display[display_cols].to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exporter snapshot équipe (CSV)", data=csv_snap, file_name="snapshot_equipe.csv", mime="text/csv")
with col_exp2:
    export_cols = ["Horodateur", "Nom / Prenom", "Poste", "groupe_entrainement", "Charge (UA)", "RPE (Chiffre)", "Duree (min)", "Ressenti / Notes", "Fatigue | Courbatures | Sommeil"]
    csv_all = sessions_all[export_cols].to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exporter toutes les sessions (CSV)", data=csv_all, file_name="sessions_equipe_completes.csv", mime="text/csv")

# ── VUE PAR POSTE ───────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("📌 Vue par poste"):
    postes = snapshot["Poste"].unique()
    for poste in sorted(postes):
        poste_df_rpe = rpe_data[rpe_data["poste"] == poste]
        avg_rpe_poste = poste_df_rpe["rpe"].mean() if not poste_df_rpe.empty else 0
        
        st.markdown(f"#### **{poste}** — RPE Moyen ({periode_rpe} derniers jours) : **{avg_rpe_poste:.1f}**")
        poste_df = snapshot_display[snapshot_display["Poste"] == poste][display_cols]
        st.dataframe(poste_df.reset_index(drop=True), use_container_width=True, hide_index=True)
        st.markdown("<br>", unsafe_allow_html=True)
