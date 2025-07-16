import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import threading
import time

# Import des fonctions depuis core/
from core.regulation import lire_donnees_andeeraa
from core.chauffage import activer_relais, desactiver_relais
from core.thingspeak import send_to_thingspeak

# --- Variables globales ---
running = False
use_thingspeak = tk.BooleanVar(value=False)
thingspeak_api = tk.StringVar(value="")

# --- Fonctions ---

def boucle_mesures():
    while running:
        donnees = lire_donnees_andeeraa()
        if donnees:
            cond, temp, sal = donnees
            temp_label_var.set(f"{temp:.2f} °C")
            cond_label_var.set(f"{cond:.2f} mS/cm")
            sal_label_var.set(f"{sal:.2f} PSU")

            if use_thingspeak.get() and thingspeak_api.get():
                send_to_thingspeak(thingspeak_api.get(), temp, cond, sal)
            
            log(f"Mesure : Temp={temp:.2f} | Cond={cond:.2f} | Sal={sal:.2f}")
        else:
            log("Erreur lecture sonde.")
        time.sleep(3)

def demarrer_mesures():
    global running
    if not running:
        running = True
        threading.Thread(target=boucle_mesures, daemon=True).start()
        log("Mesures démarrées.")

def arreter_mesures():
    global running
    running = False
    log("Mesures arrêtées.")

def log(message):
    journal_text.insert(tk.END, f"{message}\n")
    journal_text.see(tk.END)

# --- Interface graphique ---
root = tk.Tk()
root.title("Contrôle bassin de métrologie")

notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True)

# Onglet 1 : Mesures
onglet_mesures = ttk.Frame(notebook)
notebook.add(onglet_mesures, text="Mesures")

temp_label_var = tk.StringVar(value="--")
cond_label_var = tk.StringVar(value="--")
sal_label_var = tk.StringVar(value="--")

ttk.Label(onglet_mesures, text="Température :").grid(row=0, column=0, sticky="w")
ttk.Label(onglet_mesures, textvariable=temp_label_var).grid(row=0, column=1, sticky="w")

ttk.Label(onglet_mesures, text="Conductivité :").grid(row=1, column=0, sticky="w")
ttk.Label(onglet_mesures, textvariable=cond_label_var).grid(row=1, column=1, sticky="w")

ttk.Label(onglet_mesures, text="Salinité :").grid(row=2, column=0, sticky="w")
ttk.Label(onglet_mesures, textvariable=sal_label_var).grid(row=2, column=1, sticky="w")

ttk.Button(onglet_mesures, text="Démarrer", command=demarrer_mesures).grid(row=3, column=0)
ttk.Button(onglet_mesures, text="Arrêter", command=arreter_mesures).grid(row=3, column=1)

# Onglet 2 : Paliers (placeholder)
onglet_paliers = ttk.Frame(notebook)
notebook.add(onglet_paliers, text="Paliers")
ttk.Label(onglet_paliers, text="(À venir : édition et lancement des paliers)").pack(padx=10, pady=10)

# Onglet 3 : Options
onglet_options = ttk.Frame(notebook)
notebook.add(onglet_options, text="Options")

ttk.Checkbutton(onglet_options, text="Activer ThingSpeak", variable=use_thingspeak).grid(row=0, column=0, sticky="w")
ttk.Label(onglet_options, text="Clé API :").grid(row=1, column=0, sticky="w")
ttk.Entry(onglet_options, textvariable=thingspeak_api, width=40).grid(row=1, column=1, sticky="w")

# Onglet 4 : Journal
onglet_journal = ttk.Frame(notebook)
notebook.add(onglet_journal, text="Journal")

journal_text = ScrolledText(onglet_journal, height=15)
journal_text.pack(fill='both', expand=True)

# Fermeture propre
def on_close():
    arreter_mesures()
    desactiver_relais()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
