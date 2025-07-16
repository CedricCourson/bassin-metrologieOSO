#!/usr/bin/env python3
import gpiod
import time
import csv
import os
import serial
import argparse
import requests
from datetime import datetime
from itertools import cycle

# --- PARAMETRES GÉNÉRAUX ---
RELAI_GPIO = 17
TEMPS_ATTENTE = 3  # secondes entre chaque boucle
CSV_PATH = 'data_bassin.csv'
PALIER_PATH = 'paliers.txt'
SERIAL_PORT = '/dev/ttyAMA0'
BAUD_RATE = 9600
HYSTERESIS = 0.001

# --- ARGPARSE (options ligne de commande) ---
parser = argparse.ArgumentParser(description="Asservissement température avec paliers et envoi optionnel vers ThingSpeak")
parser.add_argument("--thingspeak", choices=["yes", "no"], default="no", help="Activer ThingSpeak (yes/no)")
args = parser.parse_args()
ENVOI_THINGSPEAK = args.thingspeak == "yes"

# --- CLÉ API THINGSPEAK ---
THINGSPEAK_API_KEY = "0CSG6VYJKJGFVIXT"  # Remplace-la si besoin

# --- RELAIS GPIO ---
chip = gpiod.Chip('gpiochip0')
line = chip.get_line(RELAI_GPIO)
line.request(consumer="Relais", type=gpiod.LINE_REQ_DIR_OUT)

def activer_relais():
    line.set_value(1)
    print("Resistance chauffante ACTIVEE")

def desactiver_relais():
    line.set_value(0)
    print("Resistance chauffante DESACTIVEE")

# --- PORT SÉRIE ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
except Exception as e:
    print(f"Erreur ouverture port série : {e}")
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
        print(f"Erreur lecture série : {e}")
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
            print("Erreur conversion données.")
    return None

def lire_donnees_andeeraa():
    dataserial = read_serial_data()
    if dataserial:
        return parse_serial_data(dataserial)
    return None

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
                        print(f"Erreur de conversion sur la ligne boucle : '{ligne_propre}'")
                elif "-" in ligne_propre:
                    try:
                        t_str, d_str = ligne_propre.split("-")
                        t = float(t_str.strip())
                        d = int(d_str.strip())
                        paliers.append((t, d))
                    except ValueError:
                        print(f"Ligne de palier invalide ignorée : '{ligne_propre}'")
    except FileNotFoundError:
        print(f"Fichier de paliers introuvable : {fichier}")
    except Exception as e:
        print(f"Erreur lecture paliers : {e}")
    return nombre_boucles, paliers

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
        print("Aucun palier trouvé. Arrêt.")
        raise SystemExit

    sequence_boucles = cycle(range(1)) if nombre_boucles == 0 else range(nombre_boucles)

    for i in sequence_boucles:
        print(f"\n*** CYCLE N°{i + 1 if nombre_boucles > 0 else '?'} ***")

        for consigne, duree in paliers:
            print(f"\n--- PALIER : {consigne}°C pendant {duree} sec ---")
            palier_atteint = False
            debut_maintien_palier = None

            while True:
                donnees = lire_donnees_andeeraa()
                if donnees is None:
                    print("[ERREUR] Données incomplètes, nouvelle tentative...")
                    time.sleep(TEMPS_ATTENTE)
                    continue

                cond, temp, sal = donnees

                # Régulation permanente
                if not chauffage_on and temp < (consigne - HYSTERESIS):
                    activer_relais()
                    chauffage_on = True
                elif chauffage_on and temp > (consigne + HYSTERESIS):
                    desactiver_relais()
                    chauffage_on = False

                # Début du maintien quand la consigne est atteinte
                if not palier_atteint and (consigne - HYSTERESIS) <= temp <= (consigne + HYSTERESIS):
                    print(f"Consigne atteinte ({consigne}°C), début du maintien.")
                    debut_maintien_palier = time.time()
                    palier_atteint = True

                # Fin du maintien si durée atteinte
                if palier_atteint:
                    if (time.time() - debut_maintien_palier) >= duree:
                        print(f"Maintien terminé : {duree}s à {consigne}°C.")
                        break

                etat = 1 if chauffage_on else 0
                temps_restant_str = "N/A"
                if palier_atteint:
                    temps_restant = duree - (time.time() - debut_maintien_palier)
                    temps_restant_str = f"{int(temps_restant)}s"

                print(f"Consigne: {consigne:.2f}°C | Temp: {temp:.3f}°C | "
                      f"Maintien: {'OUI' if palier_atteint else 'NON'} | "
                      f"Temps restant: {temps_restant_str} | Relais: {'ON' if etat else 'OFF'}")

                enregistrer_csv(temp, cond, sal, etat, consigne)

                if ENVOI_THINGSPEAK:
                    send_to_thingspeak(THINGSPEAK_API_KEY, temp, cond, sal)

                time.sleep(TEMPS_ATTENTE)

except KeyboardInterrupt:
    print("\nArrêt manuel du programme.")
finally:
    print("Arrêt du chauffage et libération des ressources.")
    desactiver_relais()
    line.release()
    if ser and ser.is_open:
        ser.close()
    print("Programme terminé.")
