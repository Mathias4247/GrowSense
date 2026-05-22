import sensor_reader

_tilstand = {
    "pumpe":    False,
    "lysprofil": "standard",
    "soil_min":  50,
    "soil_max":  70,
}


def set_pumpe(state: bool):
    _tilstand["pumpe"] = state
    sensor_reader.send("indstil:pumpe={}".format("TIL" if state else "FRA"))


def set_profil(soil_min: int, soil_max: int, lysprofil: str = "standard"):
    """Sender profilgrænser + lysprofil til ESP32."""
    _tilstand["soil_min"]  = soil_min
    _tilstand["soil_max"]  = soil_max
    _tilstand["lysprofil"] = lysprofil
    sensor_reader.send("indstil:soil_min={},soil_max={},lysprofil={}".format(
        soil_min, soil_max, lysprofil
    ))


def set_lysprofil(navn: str):
    if navn in ("seedling", "standard"):
        _tilstand["lysprofil"] = navn
        sensor_reader.send("indstil:lysprofil={}".format(navn))


def get_tilstand() -> dict:
    return _tilstand.copy()