import os, re

files = [
    "pages/2_Tableau_Individuel.py",
    "pages/3_Tableau_Collectif.py",
    "pages/4_Gestion_Joueurs.py",
    "app.py",
    "pages/1_Saisie_Quotidienne.py",
]

for fpath in files:
    with open(fpath, encoding="utf-8") as f:
        content = f.read()
    new = content.replace("use_container_width=True", "width='stretch'")
    new = new.replace("use_container_width=False", "width='content'")
    if new != content:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(new)
        count = content.count("use_container_width")
        print(f"Fixed {count} occurrence(s) in {fpath}")
    else:
        print(f"No changes needed in {fpath}")
