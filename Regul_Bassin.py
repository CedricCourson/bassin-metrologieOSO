import gpiod
import time
import csv
import os
import serial
import argparse
import requests
from datetime import datetime
from itertools import cycle



# --- PARAMETRES ---
RELAI_GPIO = 17
TEMPS_ATTENTE = 3
CSV_PATH = 'data_bassin.csv'
PALIER_PATH = 'paliers.txt'
SERIAL_PORT = '/dev/ttyAMA0'
BAUD_RATE = 9600
HYSTERESIS = 0.001




# --- ARGPARSE : options en ligne de commande ---
parser = argparse.ArgumentParser(description="Asservissement température avec paliers et option ThingSpeak")
parser.add_argument("--thingspeak", choices=["yes", "no"], default="no", help="Activer ThingSpeak (yes/no)")
args = parser.parse_args()

ENVOI_THINGSPEAK = args.thingspeak == "yes"





# --- RELAIS ---
chip = gpiod.Chip('gpiochip0')
line = chip.get_line(RELAI_GPIO)
line.request(consumer="Relais", type=gpiod.LINE_REQ_DIR_OUT)

def activer_relais():
    line.set_value(1)
    print("Resistance chauffante ACTIVEE")

def desactiver_relais():
    line.set_value(0)
    print("Resistance chauffante DESACTIVEE")

# --- SERIAL ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
except Exception as e:
    print(f"Erreur ouverture port serie : {e}")
    ser = None

def flush_serial():
    if ser:
        ser.reset_input_buffer()

def read_serial_data():
    if ser is None:
        return None
    flush_serial()
    try:
        ligne = ser.readline().decode(errors='ignore').strip()
        return ligne if ligne else None
    except Exception as e:
        print(f"Erreur lecture serie : {e}")
        return None

def parse_serial_data(dataserial):
    parts = dataserial.strip().split()
    if len(parts) >= 5:
        try:
            conductivite = float(parts[2])
            temperature = float(parts[3])
            salinite = float(parts[4])
            return conductivite, temperature, salinite
        except ValueError:
            print("Erreur conversion donnees.")
    return None


# ---- Aanderaa
def lire_donnees_andeeraa():
    dataserial = read_serial_data()
    if dataserial:
        return parse_serial_data(dataserial)
    return None
    
# --- Enregistrement de donnée

def enregistrer_csv(temp, cond, sal, relais, consigne, chemin=CSV_PATH):
    existe = os.path.isfile(chemin)
    now = datetime.now()
    with open(chemin, 'a', newline='') as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(['Date', 'Heure', 'Consigne (C)', 'Temp (C)', 'Cond (mS/cm)', 'Sal (PSU)', 'Relais'])
        writer.writerow([
            now.strftime('%Y-%m-%d'),
            now.strftime('%H:%M:%S'),
            f"{consigne:.2f}",
            f"{temp:.3f}",
            f"{cond:.3f}",
            f"{sal:.3f}",
            relais
        ])


# --- Cahrgement fichier palier

def charger_paliers(fichier):
    """
    Charge les paliers et le nombre de boucles depuis le fichier de configuration.
    Retourne :
        - nombre_boucles (int) : Le nombre de cycles à exécuter. Vaut 0 pour l'infini.
        - paliers (list) : La liste des tuples (consigne, duree).
    """
    paliers = []
    nombre_boucles = 1  # Valeur par défaut si non spécifié : 1 seul cycle.
    try:
        with open(fichier, 'r') as f:
            for ligne in f:
                ligne_propre = ligne.strip()
                if not ligne_propre or ligne_propre.startswith('#'):
                    continue  # Ignore les lignes vides ou les commentaires

                # Détection de la directive pour le nombre de boucles
                if "boucle" in ligne_propre.lower() and "-" in ligne_propre:
                    try:
                        cle, valeur = ligne_propre.split('-')
                        nombre_boucles = int(valeur.strip())
                    except ValueError:
                        print(f"Erreur de conversion sur la ligne de boucle : '{ligne_propre}'. Utilisation de la valeur par défaut (1).")
                        nombre_boucles = 1
                
                # Détection d'un palier de température
                elif "-" in ligne_propre:
                    try:
                        t_str, d_str = ligne_propre.split("-")
                        t = float(t_str.strip())
                        d = int(d_str.strip())
                        paliers.append((t, d))
                    except ValueError:
                        print(f"Ligne de palier invalide ignorée : '{ligne_propre}'")

    except FileNotFoundError:
        print(f"Erreur : le fichier de paliers '{fichier}' est introuvable.")
    except Exception as e:
        print(f"Erreur inattendue lors de la lecture du fichier paliers : {e}")
        
    return nombre_boucles, paliers


# --- configuration thingspeak

THINGSPEAK_API_KEY = "0CSG6VYJKJGFVIXT"  # Remplace par ta vraie clé

def send_to_thingspeak(api_key, temperature, conductivity, salinity):
    base_url = "https://api.thingspeak.com/update"
    params = {
        "api_key": api_key,
        "field1": temperature,
        "field2": conductivity,
        "field3": salinity
    }
    try:
        response = requests.get(base_url, params=params, timeout=4)
        if response.status_code != 200:
            print(f"[ThingSpeak] Erreur HTTP : {response.status_code}")
    except Exception as e:
        print(f"[ThingSpeak] Exception : {e}")





# --- BOUCLE PRINCIPALE ---

try:
    chauffage_on = False
    nombre_boucles, paliers = charger_paliers(PALIER_PATH)

    if not paliers:
        print("Aucun palier de consigne trouvé dans paliers.txt. Arrêt du programme.")
        raise SystemExit

    # Création d'un itérateur qui sera soit fini, soit infini
    if nombre_boucles == 0:
        print("Mode de boucle infinie activé.")
        # Pour une boucle infinie, on crée une liste qui ne se terminera jamais conceptuellement
        sequence_boucles = cycle(range(1)) # itertools.cycle est parfait pour ça
        # N'oubliez pas d'ajouter "from itertools import cycle" en haut de votre script !
    else:
        print(f"Le cycle sera exécuté {nombre_boucles} fois.")
        sequence_boucles = range(nombre_boucles)

    for i in sequence_boucles:
        if nombre_boucles > 0:
            print(f"\n*** DÉMARRAGE DU CYCLE N°{i + 1}/{nombre_boucles} ***")
        else:
            print("\n*** DÉMARRAGE D'UN NOUVEAU CYCLE DE PALIERS ***")

        for consigne, duree in paliers:
            print(f"\n--- NOUVEAU PALIER ---")
            print(f"Objectif: Atteindre {consigne}°C et maintenir pendant {duree} secondes.")

            palier_atteint = False
            debut_maintien_palier = None

            while True:
                donnees = lire_donnees_andeeraa()
                if donnees is None:
                    print("[ERREUR] Données incomplètes, nouvelle tentative...")
                    time.sleep(TEMPS_ATTENTE)
                    continue

                cond, temp, sal = donnees

                if not chauffage_on and temp < (consigne - HYSTERESIS):
                    activer_relais()
                    chauffage_on = True
                elif chauffage_on and temp > (consigne + HYSTERESIS):
                    desactiver_relais()
                    chauffage_on = False

                if not palier_atteint:
                    if (consigne - HYSTERESIS) <= temp <= (consigne + HYSTERESIS):
                        print(f"Temperature de consigne ({consigne}°C) atteinte.")
                        print(f"Début du maintien pour une durée de {duree} secondes.")
                        palier_atteint = True
                        debut_maintien_palier = time.time()
                
                if palier_atteint:
                    temps_ecoule = time.time() - debut_maintien_palier
                    if temps_ecoule >= duree:
                        print(f"Maintien de {duree}s terminé pour le palier à {consigne}°C.")
                        break

                etat = 1 if chauffage_on else 0
                temps_restant_str = "N/A"
                if palier_atteint:
                    temps_restant = duree - (time.time() - debut_maintien_palier)
                    temps_restant_str = f"{int(temps_restant)}s"

                print(f"Consigne: {consigne:.2f} C | Temp: {temp:.3f} C | Maintien: {'OUI' if palier_atteint else 'NON'} | Temps restant: {temps_restant_str} | Relais: {'ON' if etat else 'OFF'}")
                
                enregistrer_csv(temp, cond, sal, etat, consigne)
                
                if ENVOI_THINGSPEAK:
                  send_to_thingspeak(THINGSPEAK_API_KEY, temp, cond, sal)

                
                time.sleep(TEMPS_ATTENTE)

except KeyboardInterrupt:
    print("\nArrêt manuel du programme par l'utilisateur.")

finally:
    print("Arrêt du chauffage et libération des ressources.")
    desactiver_relais()
    line.release()
    if ser and ser.is_open:
        ser.close()
    print("Programme terminé.")
