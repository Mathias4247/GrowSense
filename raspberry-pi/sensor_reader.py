import json
import threading
import csv
import os
from datetime import datetime
from time import sleep
import random

try:
    import serial
    _serial_ok = True
except ImportError:
    _serial_ok = False

SERIAL_PORT = "/dev/serial0"   # Tjek hvilken port ESP32 er på: ls /dev/ttyUSB*
BAUD_RATE = 115200
LOG_FIL = "data/sensor_log.csv"

# CSV-kolonner - ESP32 sender disse værdier som JSON
CSV_KOLONNER = ["timestamp", "soil", "light", "vandstand"]

# Delt sensor-tilstand - opdateres af baggrundstråd
sensor_data = {
    "soil":      0.0,
    "light":     0,
    "vandstand": "Ukendt",
    "timestamp": "Ingen data endnu",
}


def _gem_til_csv(data: dict):
    os.makedirs("data", exist_ok=True)
    fil_fandtes = os.path.exists(LOG_FIL)
    with open(LOG_FIL, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_KOLONNER, extrasaction="ignore")
        if not fil_fandtes:
            writer.writeheader()
        writer.writerow(data)


def _demo_loop():
    """Kører når ingen ESP32 er tilsluttet - simulerer realistiske sensorværdier."""
    print("Demo-tilstand: simulerer ESP32 sensordata (ingen Pi nødvendig)")
    soil   = 55.0
    height = 5.0
    taeller = 0
    while True:
        soil   = max(10.0, min(90.0, soil + random.uniform(-1.5, 0.8)))
        height = min(30.0, height + random.uniform(0.0, 0.04))
        sensor_data.update({
            "soil":     round(soil, 1),
            "light":    random.randint(400, 900),
        })
        sensor_data["timestamp"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        taeller += 1
        if taeller % 10 == 0:
            _gem_til_csv(sensor_data.copy())
        sleep(2)


def _laes_serial():
    taeller = 0
    if not _serial_ok:
        _demo_loop()
        return
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        print(f"Forbundet til ESP32 på {SERIAL_PORT}")
        while True:
            linje = ser.readline().decode("utf-8", errors="ignore").strip()
            if not linje:
                continue
            try:
                dele = linje.split(",")
                for del_ in dele:
                    if ":" in del_:
                        key, val = del_.split(":", 1)
                        key = key.strip()
                        val = val.strip().rstrip("%")
                        if key == "jordfugt":
                            sensor_data["soil"] = float(val)
                        elif key == "vandstand":
                            sensor_data["vandstand"] = val
                        elif key == "lys":
                            sensor_data["light"] = int(val)
                sensor_data["timestamp"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                taeller += 1
                if taeller % 10 == 0:
                    _gem_til_csv(sensor_data.copy())
            except Exception:
                pass
    except Exception as e:
        print(f"Serial fejl: {e} - starter demo-tilstand")
        _demo_loop()


def start():
    t = threading.Thread(target=_laes_serial, daemon=True)
    t.start()


def get_data() -> dict:
    return sensor_data.copy()


def get_historik(antal: int = 20) -> list:
    """Returnerer de seneste 'antal' rækker fra CSV som liste af dicts."""
    if not os.path.exists(LOG_FIL):
        return []
    with open(LOG_FIL, "r") as f:
        reader = csv.DictReader(f)
        raekker = list(reader)
    return raekker[-antal:]