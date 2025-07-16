# core/paliers.py

def charger_paliers(fichier):
    paliers = []
    nombre_boucles = 1
    try:
        with open(fichier, 'r') as f:
            for ligne in f:
                ligne_propre = ligne.strip()
                if not ligne_propre or ligne_propre.startswith('#'):
                    continue
                if "boucle" in ligne_propre.lower() and "-" in ligne_propre:
                    try:
                        _, valeur = ligne_propre.split('-')
                        nombre_boucles = int(valeur.strip())
                    except ValueError:
                        print(f"Erreur conversion boucle : '{ligne_propre}'")
                elif "-" in ligne_propre:
                    try:
                        t_str, d_str = ligne_propre.split("-")
                        t = float(t_str.strip())
                        d = int(d_str.strip())
                        paliers.append((t, d))
                    except ValueError:
                        print(f"Ligne de palier invalide : '{ligne_propre}'")
    except FileNotFoundError:
        print(f"Fichier de paliers introuvable : {fichier}")
    except Exception as e:
        print(f"Erreur lecture paliers : {e}")
    return nombre_boucles, paliers
