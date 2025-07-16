# gui_bassin_extended.py
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import time
import csv
import os
from datetime import datetime
from itertools import cycle
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

from core.chauffage import activer_relais, desactiver_relais, nettoyage_gpio
from core.enregistrement import enregistrer_csv
from core.thingspeak import send_to_thingspeak
from core.paliers import charger_paliers
from core.regulation import regulation_step, is_consigne_atteinte

import serial

# CONFIGURATION
CSV_PATH = "data_bassin.csv"
PALIER_PATH = "paliers.txt"
SERIAL_PORT = "/dev/ttyAMA0"
BAUD_RATE = 9600
THINGSPEAK_API_KEY = "0CSG6VYJKJGFVIXT"
TEMPS_LECTURE = 3

class BassinGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Interface Bassin de Métrologie")
        self.running = True
        self.enregistrement = False
        self.chauffage_on = False

        self.freq_enregistrement = tk.IntVar(value=5)
        self.use_thingspeak = tk.BooleanVar()
        self.log_text = None

        self.heure_x = tk.IntVar(value=3)
        self.y_min = tk.DoubleVar(value=0.0)
        self.y_max = tk.DoubleVar(value=40.0)

        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        except Exception as e:
            print(f"Erreur port série : {e}")
            self.ser = None

        self.setup_ui()
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()

    def setup_ui(self):
        self.tabs = ttk.Notebook(self.root)
        self.tab1 = ttk.Frame(self.tabs)
        self.tab2 = ttk.Frame(self.tabs)
        self.tab3 = ttk.Frame(self.tabs)
        self.tab4 = ttk.Frame(self.tabs)
        self.tabs.add(self.tab1, text="Temps réel")
        self.tabs.add(self.tab2, text="Paliers")
        self.tabs.add(self.tab3, text="Visualisation")
        self.tabs.add(self.tab4, text="Journal")
        self.tabs.pack(fill='both', expand=True)

        self.setup_tab1()
        self.setup_tab2()
        self.setup_tab3()
        self.setup_tab4()

    def setup_tab1(self):
        self.temp_var = tk.StringVar(value="--")
        self.cond_var = tk.StringVar(value="--")
        self.sal_var = tk.StringVar(value="--")
        self.etat_var = tk.StringVar(value="OFF")

        ttk.Label(self.tab1, text="Température :").pack()
        ttk.Label(self.tab1, textvariable=self.temp_var, font=("Arial", 14)).pack()
        ttk.Label(self.tab1, text="Conductivité :").pack()
        ttk.Label(self.tab1, textvariable=self.cond_var, font=("Arial", 14)).pack()
        ttk.Label(self.tab1, text="Salinité :").pack()
        ttk.Label(self.tab1, textvariable=self.sal_var, font=("Arial", 14)).pack()
        ttk.Label(self.tab1, text="Relais :").pack()
        ttk.Label(self.tab1, textvariable=self.etat_var, font=("Arial", 12)).pack()

        # Enregistrement
        f = ttk.Frame(self.tab1)
        f.pack(pady=10)
        ttk.Button(f, text="Démarrer enregistrement", command=self.start_enregistrement).grid(row=0, column=0, padx=5)
        ttk.Button(f, text="Arrêter", command=self.stop_enregistrement).grid(row=0, column=1, padx=5)
        ttk.Label(f, text="Fréquence (s):").grid(row=0, column=2)
        ttk.Entry(f, textvariable=self.freq_enregistrement, width=5).grid(row=0, column=3)
        ttk.Checkbutton(self.tab1, text="Activer ThingSpeak", variable=self.use_thingspeak).pack()

    def setup_tab2(self):
        self.palier_text = ScrolledText(self.tab2, height=10)
        self.palier_text.pack(fill='both', expand=True)
        self.load_paliers()
        ttk.Button(self.tab2, text="Sauvegarder", command=self.save_paliers).pack(pady=5)

    def setup_tab3(self):
        controls = ttk.Frame(self.tab3)
        controls.pack()
        ttk.Label(controls, text="X (heures) :").grid(row=0, column=0)
        ttk.Entry(controls, textvariable=self.heure_x, width=5).grid(row=0, column=1)
        ttk.Label(controls, text="Y min :").grid(row=0, column=2)
        ttk.Entry(controls, textvariable=self.y_min, width=5).grid(row=0, column=3)
        ttk.Label(controls, text="Y max :").grid(row=0, column=4)
        ttk.Entry(controls, textvariable=self.y_max, width=5).grid(row=0, column=5)
        ttk.Button(controls, text="Rafraîchir", command=self.update_plot).grid(row=0, column=6, padx=5)

        self.fig, self.ax = plt.subplots(figsize=(6,4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab3)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

    def setup_tab4(self):
        self.log_text = ScrolledText(self.tab4, height=20)
        self.log_text.pack(fill='both', expand=True)

    def log(self, msg):
        now = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{now}] {msg}\n")
        self.log_text.see(tk.END)

    def update_loop(self):
        t_last_enregistrement = time.time()
        while self.running:
            donnees = self.lire_donnees()
            if donnees:
                cond, temp, sal = donnees
                self.temp_var.set(f"{temp:.2f} °C")
                self.cond_var.set(f"{cond:.2f} mS/cm")
                self.sal_var.set(f"{sal:.2f} PSU")

                if self.enregistrement and (time.time() - t_last_enregistrement) >= self.freq_enregistrement.get():
                    enregistrer_csv(temp, cond, sal, int(self.chauffage_on), 0.0, CSV_PATH)
                    if self.use_thingspeak.get():
                        send_to_thingspeak(THINGSPEAK_API_KEY, temp, cond, sal)
                    self.log("Enregistrement effectué")
                    t_last_enregistrement = time.time()

            time.sleep(TEMPS_LECTURE)

    def lire_donnees(self):
        if not self.ser:
            return None
        try:
            self.ser.reset_input_buffer()
            ligne = self.ser.readline().decode(errors='ignore').strip()
            parts = ligne.split()
            if len(parts) >= 5:
                return float(parts[2]), float(parts[3]), float(parts[4])
        except:
            return None
        return None

    def start_enregistrement(self):
        self.enregistrement = True
        self.log("Enregistrement démarré")

    def stop_enregistrement(self):
        self.enregistrement = False
        self.log("Enregistrement arrêté")

    def load_paliers(self):
        try:
            with open(PALIER_PATH, 'r') as f:
                contenu = f.read()
                self.palier_text.delete('1.0', tk.END)
                self.palier_text.insert(tk.END, contenu)
        except:
            self.palier_text.insert(tk.END, "Erreur lecture fichier paliers.txt")

    def save_paliers(self):
        contenu = self.palier_text.get('1.0', tk.END)
        try:
            with open(PALIER_PATH, 'w') as f:
                f.write(contenu.strip())
                self.log("Paliers sauvegardés")
        except:
            self.log("Erreur lors de l'enregistrement des paliers")

    def update_plot(self):
        if not os.path.exists(CSV_PATH):
            self.log("Aucun fichier CSV à afficher")
            return
        try:
            df = pd.read_csv(CSV_PATH, parse_dates=[["Date", "Heure"]])
            df = df.set_index("Date_Heure")
            now = datetime.now()
            df = df[df.index > now - pd.Timedelta(hours=self.heure_x.get())]
            self.ax.clear()
            self.ax.plot(df.index, df['Temp (C)'], label='Température (°C)')
            self.ax.plot(df.index, df['Cond (mS/cm)'], label='Conductivité')
            self.ax.plot(df.index, df['Sal (PSU)'], label='Salinité')
            self.ax.set_ylim(self.y_min.get(), self.y_max.get())
            self.ax.legend()
            self.ax.set_title("Évolution des paramètres")
            self.canvas.draw()
            self.log("Graphique mis à jour")
        except Exception as e:
            self.log(f"Erreur graphique : {e}")

    def on_close(self):
        self.running = False
        nettoyage_gpio()
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = BassinGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
