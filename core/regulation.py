# core/regulation.py

import time
from core.chauffage import activer_relais, desactiver_relais

HYSTERESIS = 0.001

def regulation_step(temp, consigne, chauffage_on):
    """
    Applique la logique d'asservissement avec hystérésis.
    Retourne l'état du chauffage (True/False) et une action ("on", "off" ou None).
    """
    action = None
    if not chauffage_on and temp < (consigne - HYSTERESIS):
        activer_relais()
        chauffage_on = True
        action = "on"
    elif chauffage_on and temp > (consigne + HYSTERESIS):
        desactiver_relais()
        chauffage_on = False
        action = "off"
    return chauffage_on, action


def is_consigne_atteinte(temp, consigne):
    return (consigne - HYSTERESIS) <= temp <= (consigne + HYSTERESIS)