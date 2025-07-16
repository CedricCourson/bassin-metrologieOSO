# core/chauffage.py

import gpiod

RELAI_GPIO = 17
chip = gpiod.Chip('gpiochip0')
line = chip.get_line(RELAI_GPIO)
line.request(consumer="Relais", type=gpiod.LINE_REQ_DIR_OUT)

def activer_relais():
    line.set_value(1)
    print("Resistance chauffante ACTIVEE")

def desactiver_relais():
    line.set_value(0)
    print("Resistance chauffante DESACTIVEE")

def nettoyage_gpio():
    line.set_value(0)
    line.release()

