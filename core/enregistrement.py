# core/enregistrement.py

import csv
import os
from datetime import datetime

def enregistrer_csv(temp, cond, sal, relais, consigne, chemin):
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

