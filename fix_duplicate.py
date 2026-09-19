"""
Script de nettoyage : supprime la définition dupliquée de _get_week_number
dans pages/1_Saisie_Quotidienne.py
"""
path = "pages/1_Saisie_Quotidienne.py"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# Trouver les deux occurrences de la définition
indices = [i for i, l in enumerate(lines) if "def _get_week_number" in l]
print(f"Definitions trouvees aux lignes: {[i+1 for i in indices]}")

if len(indices) >= 2:
    # Supprimer la 2e occurrence (lignes 170-175 environ = index 169-174)
    # On supprime 6 lignes : la ligne vide avant + def + docstring + try + return + except + return
    second = indices[1]
    # Remonter pour inclure la ligne vide précédente
    start = second - 1 if lines[second - 1].strip() == "" else second
    # Avancer jusqu'à la fin du bloc (ligne vide suivante)
    end = second
    while end < len(lines) and lines[end].strip() != "":
        end += 1
    # Supprimer les lignes start..end (inclus la ligne vide de fin)
    removed = lines[start:end+1]
    lines = lines[:start] + lines[end+1:]
    print(f"Supprime {len(removed)} lignes ({start+1} a {end+1}):")
    for l in removed:
        print(f"  {repr(l)}")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("Fichier mis a jour.")
else:
    print("Pas de doublon detecte, rien a faire.")
