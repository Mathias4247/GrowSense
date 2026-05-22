import os
from datetime import datetime

try:
    import libcamera
    from picamera2 import Picamera2
    _cam_ok = True
except Exception:
    _cam_ok = False
    print("PiCamera2 ikke tilgængelig - kamera deaktiveret")

try:
    from ultralytics import YOLO
    _model = YOLO("/home/gruppe5/best_ncnn_model", task="classify")   # præ-trænet model på Pi
    _yolo_ok = True
except Exception:
    _yolo_ok = False
    print("YOLOv8 ikke tilgængelig")

IMG_MAPPE = "static/img"
os.makedirs(IMG_MAPPE, exist_ok=True)

# Gemmer seneste kamera-resultat i hukommelsen
seneste_resultat = {
    "billede":    None,
    "sundhed":    None,
    "labels":     [],
    "timestamp":  None,
}


def tag_billede_og_analyser() -> dict:
    """Tager et billede med PiCamera, kører YOLOv8, returnerer resultat-dict."""
    nu = datetime.now()
    filnavn = f"{nu.strftime('%d-%m-%Y_%H-%M-%S')}.jpg"
    sti = f"{IMG_MAPPE}/{filnavn}"

    # Kamera
    if _cam_ok:
        picam = Picamera2()
        config = picam.create_still_configuration(main={"size": (640, 480)})
        config["transform"] = libcamera.Transform(hflip=1, vflip=1)
        picam.configure(config)
        picam.start()
        picam.capture_file(sti)
        picam.close()
    else:
        # Ingen Pi-kamera - brug placeholder
        filnavn = None

    # YOLOv8 analyse
    labels = []
    sundhed = "Ukendt"
    if _yolo_ok and filnavn:
        results = _model(sti, verbose=False)
        probs = results[0].probs
        names = results[0].names
        healthy_idx = list(names.values()).index("healthy")
        sick_idx    = list(names.values()).index("sick")
        healthy_pct = round(probs.data[healthy_idx].item() * 100, 1)
        sick_pct    = round(probs.data[sick_idx].item() * 100, 1)
        sundhed = "Sund" if healthy_pct > sick_pct else "Syg"

    seneste_resultat["billede"]   = filnavn
    seneste_resultat["sundhed"]   = sundhed
    seneste_resultat["labels"]    = labels
    seneste_resultat["timestamp"] = nu.strftime("%d-%m-%Y %H:%M:%S")

    return seneste_resultat.copy()


def get_galleri(antal: int = 12) -> list:
    """Returnerer liste af billedfilnavne sorteret nyest først."""
    if not os.path.exists(IMG_MAPPE):
        return []
    filer = sorted(
        [f for f in os.listdir(IMG_MAPPE) if f.endswith(".jpg")],
        reverse=True,
    )
    return filer[:antal]
