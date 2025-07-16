# regul-bassin3.py
import time
import serial
import argparse
from itertools import cycle

from core.paliers import charger_paliers
from core.chauffage import nettoyage_gpio
from core.enregistrement import enregistrer_csv
from core.thingspeak import send_to_thingspeak
from core.regulation import regulation_step, is_consigne_atteinte

# --- PARAMÈTRES GÉNÉRAUX ---
TEMPS_ATTENTE = 3
CSV_PATH = 'data_bassin.csv'
PALIER_PATH = 'paliers.txt'
SERIAL_PORT = '/dev/ttyAMA0'
BAUD_RATE = 9600
THINGSPEAK_API_KEY = "0CSG6VYJKJGFVIXT"

# --- ARGPARSE : options ligne de commande ---
parser = argparse.ArgumentParser(description="Contrôle de bassin (console)")
parser.add_argument("--thingspeak", choices=["yes", "no"], default="no", help="Activer l'envoi vers ThingSpeak")
args = parser.parse_args()
ENVOI_THINGSPEAK = args.thingspeak == "yes"

# --- Connexion série ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
except Exception as e:
    print(f"[ERREUR] Ouverture port série : {e}")
    ser = None

def lire_donnees_andeeraa():
    if ser is None:
        return None
    try:
        ser.reset_input_buffer()
        ligne = ser.readline().decode(errors='ignore').strip()
        parts = ligne.split()
        if len(parts) >= 5:
            conductivite = float(parts[2])
            temperature = float(parts[3])
            salinite = float(parts[4])
            return conductivite, temperature, salinite
    except Exception as e:
        print(f"[ERREUR] Lecture série : {e}")
    return None

# --- BOUCLE PRINCIPALE ---
try:
    chauffage_on = False
    nombre_boucles, paliers = charger_paliers(PALIER_PATH)

    if not paliers:
        print("[ERREUR] Aucun palier trouvé.")
        raise SystemExit

    sequence = cycle(range(1)) if nombre_boucles == 0 else range(nombre_boucles)

    for i in sequence:
        print(f"\n>>> CYCLE {i + 1 if nombre_boucles > 0 else '?'}")

        for consigne, duree in paliers:
            print(f"\n-- PALIER {consigne}°C pendant {duree} sec")
            palier_atteint = False
            debut_maintien = None

            while True:
                donnees = lire_donnees_andeeraa()
                if not donnees:
                    print("[ERREUR] Données non valides.")
                    time.sleep(TEMPS_ATTENTE)
                    continue

                cond, temp, sal = donnees
                chauffage_on, _ = regulation_step(temp, consigne, chauffage_on)

                if not palier_atteint and is_consigne_atteinte(temp, consigne):
                    print(f"Consigne atteinte à {consigne}°C → début maintien.")
                    debut_maintien = time.time()
                    palier_atteint = True

                if palier_atteint and (time.time() - debut_maintien) >= duree:
                    print(f"Maintien terminé ({duree}s). Prochain palier.")
                    break

                etat = 1 if chauffage_on else 0
                reste = duree - (time.time() - debut_maintien) if palier_atteint else -1
                reste_txt = f"{int(reste)}s" if reste > 0 else "---"

                print(f"Temp: {temp:.3f}°C | Cond: {cond:.3f} | Sal: {sal:.3f} | Relais: {'ON' if etat else 'OFF'} | Temps restant: {reste_txt}")

                enregistrer_csv(temp, cond, sal, etat, consigne, CSV_PATH)
                if ENVOI_THINGSPEAK:
                    send_to_thingspeak(THINGSPEAK_API_KEY, temp, cond, sal)

                time.sleep(TEMPS_ATTENTE)

except KeyboardInterrupt:
    print("\nArrêt manuel.")

finally:
    print("Nettoyage GPIO et fermeture port série...")
    nettoyage_gpio()
    if ser and ser.is_open:
        ser.close()
    print("Terminé.")
