# core/thingspeak.py

import requests

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

