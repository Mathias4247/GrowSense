import sensor_reader

# Alle aktuatorer (pumpe + LED) sidder på ESP'en og styres via UART.
# Dette modul holder kun den senest sendte tilstand til visning i Flask.
_tilstand = {
    "pumpe":     False,
    "lysprofil": "standard",
}


def set_pumpe(state: bool):
    """Manuel pumpe-styring -> ESP."""
    _tilstand["pumpe"] = state
    sensor_reader.send("indstil:pumpe={}".format("TIL" if state else "FRA"))


def set_profil(soil_min: int, soil_max: int):
    """Planteprofilens fugt-grænser -> ESP (automatisk justering)."""
    sensor_reader.send("indstil:soil_min={},soil_max={}".format(soil_min, soil_max))


def set_lysprofil(navn: str):
    """Lysprofil-knap (seedling/standard) -> ESP."""
    if navn in ("seedling", "standard"):
        _tilstand["lysprofil"] = navn
        sensor_reader.send("indstil:lysprofil={}".format(navn))


def get_tilstand() -> dict:
    return _tilstand.copy()