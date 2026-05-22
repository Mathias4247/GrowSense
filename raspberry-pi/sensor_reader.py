import csv
import os
import threading
from datetime import datetime
from time import sleep

try:
    import serial
    _serial_ok = True
except ImportError:
    _serial_ok = False

SERIAL_PORT  = "/dev/serial0"
BAUD_RATE    = 115200
LOG_FIL      = "data/sensor_log.csv"
CSV_KOLONNER = ["timestamp", "soil1", "soil2", "light", "vandstand", "pumpe"]

sensor_data = {
    "soil1":     0.0,
    "soil2":     0.0,
    "light":     0,
    "vandstand": "Ukendt",
    "pumpe":     "FRA",
    "lysprofil": "standard",
    "led":       0,
    "timestamp": "Ingen data endnu",
}

_ser = None

def _gem_til_csv(data: dict):
    os.makedirs("data", exist_ok=True)
    fil_fandtes = os.path.exists(LOG_FIL)
    with open(LOG_FIL, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_KOLONNER, extrasaction="ignore")
        if not fil_fandtes:
            writer.writeheader()
        writer.writerow(data)

def _laes_serial():
    global _ser
    try:
        _ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        print(f"Forbundet til ESP32 på {SERIAL_PORT}")
        while True:
            linje = _ser.readline().decode("utf-8", errors="ignore").strip()
            if not linje:
                continue
            try:
                for del_ in linje.split(","):
                    if ":" not in del_:
                        continue
                    key, val = del_.split(":", 1)
                    key = key.strip()
                    val = val.strip().rstrip("%")
                    if key == "soil1":       sensor_data["soil1"] = float(val)
                    elif key == "soil2":     sensor_data["soil2"] = float(val)
                    elif key == "light":     sensor_data["light"] = int(float(val))
                    elif key == "vandstand": sensor_data["vandstand"] = val
                    elif key == "pumpe":     sensor_data["pumpe"] = val
                    elif key == "lysprofil": sensor_data["lysprofil"] = val
                    elif key == "led":       sensor_data["led"] = int(float(val))
                sensor_data["timestamp"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                _gem_til_csv(sensor_data.copy())
            except Exception:
                pass
    except Exception as e:
        print(f"Serial fejl: {e}")

def send(besked: str):
    if _ser is not None:
        try:
            _ser.write((besked.strip() + "\n").encode("utf-8"))
        except Exception:
            pass

def start():
    t = threading.Thread(target=_laes_serial, daemon=True)
    t.start()

def get_data() -> dict:
    return sensor_data.copy()

def get_historik(antal: int = 20) -> list:
    if not os.path.exists(LOG_FIL):
        return []
    with open(LOG_FIL, "r") as f:
        raekker = list(csv.DictReader(f))
    return raekker[-antal:]