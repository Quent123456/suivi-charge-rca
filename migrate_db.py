import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "training.db")

def migrate_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. Ajouter les colonnes manquantes
    cur.execute("PRAGMA table_info(players)")
    cols = [row[1] for row in cur.fetchall()]
    if 'groupe' not in cols:
        cur.execute("ALTER TABLE players ADD COLUMN groupe TEXT DEFAULT 'Groupe Élargi'")
        print("Colonne 'groupe' ajoutée à players.")

    cur.execute("PRAGMA table_info(sessions)")
    cols = [row[1] for row in cur.fetchall()]
    if 'groupe_entrainement' not in cols:
        cur.execute("ALTER TABLE sessions ADD COLUMN groupe_entrainement TEXT DEFAULT 'Équipe A'")
        print("Colonne 'groupe_entrainement' ajoutée à sessions.")
        
    # 2. Supprimer l'ancien effectif factice
    cur.execute("DELETE FROM players WHERE nom IN ('Dupont', 'Ntamack', 'Jelonch', 'Mauvaka', 'Taofifenua', 'Fickou', 'Rattez', 'Penaud', 'Carbonel', 'Cros')")
    
    # 3. Insérer le nouvel effectif
    pdf_players = [
        ("SALUA", "Landry", "Pilier"),
        ("FRION", "Quentin", "Pilier"),
        ("COZIC", "Adrien", "Pilier"),
        ("PECQUERY", "Thomas", "Pilier"),
        ("TRAMON", "Noam", "Pilier"),
        ("FOURNET", "Giovanni", "Pilier"),
        ("MAZE", "Nolan", "Pilier"),
        ("BICHARI", "Jérémy", "Pilier"),
        ("LEFEVER", "Thibault", "Pilier"),
        ("ROGIER", "Arnaud", "Pilier"),
        ("VASELLI", "Sebastien", "Pilier"),
        ("TANTER", "Edouard", "Pilier"),
        ("DAULT", "Bastien", "Pilier"),

        ("LESUEUR", "Jean-Étienne", "Talonneur"),
        ("SAINTOMER", "Lucas", "Talonneur"),
        ("GENERMONT", "Romêo", "Talonneur"),
        ("GUIBERT", "Samuel", "Talonneur"),

        ("WAEYAERT", "Thomas", "2ème ligne"),
        ("GRENET", "Paul", "2ème ligne"),
        ("SOTILLO", "Alejo", "2ème ligne"),
        ("BOIDIN", "Donovan", "2ème ligne"),
        ("VDH", "Simon", "2ème ligne"),
        ("DENIER", "Gabin", "2ème ligne"),
        ("ROY", "Etienne", "2ème ligne"),
        ("FOUQUET", "Victorien", "2ème ligne"),

        ("VASELLI", "Enzo", "3ème ligne"),
        ("LAFEUILLE", "Emilien", "3ème ligne"),
        ("MARTIN", "Benjamin", "3ème ligne"),
        ("MONTI", "Ciro", "3ème ligne"),
        ("WIOTTE", "Louis", "3ème ligne"),
        ("GENTIEN", "Tim", "3ème ligne"),
        ("ORION", "Lucas", "3ème ligne"),
        ("CARPENTIER", "Simon", "3ème ligne"),
        ("CARLIER", "Louis", "3ème ligne"),
        ("COSSARD", "Léandre", "3ème ligne"),
        ("SAINTOMER", "Louis", "3ème ligne"),
        ("AUDIERE", "Adrien", "3ème ligne"),
        ("BINNINGER", "Alban", "3ème ligne"),
        ("BLANC", "Jules", "3ème ligne"),
        ("KAZUMBA", "Camille", "3ème ligne"),

        ("TESSON", "Gabriel", "Demi de mêlée"),
        ("BAMIERE", "Clément", "Demi de mêlée"),
        ("SANTONI", "Stephan", "Demi de mêlée"),
        ("BOEUF", "Elliot", "Demi de mêlée"),

        ("HARRY", "Max", "Demi d'ouverture"),
        ("CARPENTIER", "Maël", "Demi d'ouverture"),
        ("ULMUCK", "Victor", "Demi d'ouverture"),
        ("GOMES", "Louis", "Demi d'ouverture"),
        ("SUEUR", "Xavier", "Demi d'ouverture"),

        ("PRÉVOTÉ", "Oliver", "Centre"),
        ("PELESEUMA", "Ope", "Centre"),
        ("TREMBLAY", "Brieuc", "Centre"),
        ("DE BRYUN", "Octave", "Centre"),
        ("VENIN", "Benoît", "Centre"),
        ("HURTEL", "Oscar", "Centre"),

        ("CARPENTIER", "Joseph", "Ailier"),
        ("SALUA", "Maka", "Ailier"),
        ("SELTZER", "Antoine", "Ailier"),
        ("BATON", "Léonard", "Ailier"),
        ("MARZIANO", "Nathan", "Ailier"),
        ("SRIDI", "Youness", "Ailier"),
        ("LEROUX", "Mathis", "Ailier"),

        ("LESPINASSE", "Lucien", "Arrière"),
        ("PRÉVOST", "Thomas", "Arrière"),
        ("MOINE", "Arthur", "Arrière"),
        ("VILAIN", "Beryl", "Arrière"),
    ]
    
    # Check if we already inserted them to avoid duplicates
    cur.execute("SELECT COUNT(*) FROM players WHERE nom = 'SALUA' AND prenom = 'Landry'")
    if cur.fetchone()[0] == 0:
        for nom, prenom, poste in pdf_players:
            cur.execute("INSERT INTO players (nom, prenom, poste, numero, groupe) VALUES (?, ?, ?, ?, ?)", 
                        (nom, prenom, poste, None, 'Groupe Élargi'))
        print("Nouvel effectif inséré.")
        
    conn.commit()
    conn.close()
    print("Migration terminée.")

if __name__ == '__main__':
    migrate_db()
