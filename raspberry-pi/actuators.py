try:
    import pigpio
    _pigpio_ok = True
except ImportError:
    _pigpio_ok = False

PUMPE_GPIO = 26
LED_ROD_GPIO = 12
LED_BLA_GPIO = 13

# Samlede aktuelle tilstande - bruges af Flask til at vise status
_tilstand = {
    "pumpe": False,
    "led_rod": 0,
    "led_bla": 0,
}

try:
    if not _pigpio_ok:
        raise ImportError("pigpio ikke installeret")
    _pi = pigpio.pi()
    if not _pi.connected:
        raise RuntimeError("pigpio daemon ikke tilgængelig")
    _pi.set_PWM_range(LED_ROD_GPIO, 100)
    _pi.set_PWM_range(LED_BLA_GPIO, 100)
    _pi.write(PUMPE_GPIO, 0)
    _pi_ok = True
except Exception as e:
    print(f"Aktuator advarsel: {e} (hardware deaktiveret)")
    _pi_ok = False


def set_pumpe(state: bool):
    _tilstand["pumpe"] = state
    if _pi_ok:
        _pi.write(PUMPE_GPIO, 1 if state else 0)


def set_led(rod: int, bla: int):
    rod = max(0, min(100, rod))
    bla = max(0, min(100, bla))
    _tilstand["led_rod"] = rod
    _tilstand["led_bla"] = bla
    if _pi_ok:
        _pi.set_PWM_dutycycle(LED_ROD_GPIO, rod)
        _pi.set_PWM_dutycycle(LED_BLA_GPIO, bla)


def get_tilstand() -> dict:
    return _tilstand.copy()
