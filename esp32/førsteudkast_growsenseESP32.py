from machine import Pin, ADC, UART
from neopixel import NeoPixel
from time import sleep
import time

# ====== PIN-KONFIGURATION ======
FUGT1_PIN     = 35
FUGT2_PIN     = 33
LDR_PIN       = 39
VANDSTAND_PIN = 12
PUMP_PIN      = 27
LED_PIN       = 32
LED_ANTAL     = 22
UART_TX       = 4
UART_RX       = 5

# ====== KALIBRERING ======
SOIL_DRY   = 2500
SOIL_WET   = 1000
ADC_DARK   = 0
ADC_BRIGHT = 1615

# ====== GRÆNSEVÆRDIER ======
SOIL_MIN = 50
SOIL_MAX = 70

# ====== LYSPROFILER (R, G, B i %) ======
SEEDLING_PROFILE = (25, 100, 25)
STANDARD_PROFILE = (70, 100, 58)

# ====== PUMPE-TIMER ======
PUMPE_VARIGHED = 5    # sekunder pumpen kører ad gangen
PUMPE_PAUSE    = 60   # sekunder pause efter stop inden ny måling


class WaterSystem:
    def __init__(self, fugt1_pin, fugt2_pin, pump_pin, dry, wet):
        self.fugt1 = self._adc(fugt1_pin)
        self.fugt2 = self._adc(fugt2_pin)
        self.pump = Pin(pump_pin, Pin.OUT)
        self.pump.value(0)
        self.dry = dry
        self.wet = wet
        self.pumping = False
        self.pumpe_start_tid = None
        self.pumpe_slut_tid  = None

    def _adc(self, pin):
        adc = ADC(Pin(pin))
        adc.atten(ADC.ATTN_11DB)
        return adc

    def _les(self, adc, antal=20):
        return sum(adc.read() for _ in range(antal)) // antal

    def _til_pct(self, raw):
        pct = (self.dry - raw) * 100 / (self.dry - self.wet)
        return max(0.0, min(100.0, round(pct, 1)))

    def read(self):
        soil1 = self._til_pct(self._les(self.fugt1))
        soil2 = self._til_pct(self._les(self.fugt2))
        return soil1, soil2

    def pump_if_needed(self, soil1, soil2, soil_min, soil_max):
        nu = time.time()

        if self.pumping:
            # Stop pumpen når varighed er nået — ignorer sensor under kørsel
            if self.pumpe_start_tid and (nu - self.pumpe_start_tid) >= PUMPE_VARIGHED:
                self.pump.value(0)
                self.pumping = False
                self.pumpe_slut_tid = nu
        else:
            # Vent pausen ud mens vandet siver ind og sensor stabiliserer
            if self.pumpe_slut_tid and (nu - self.pumpe_slut_tid) < PUMPE_PAUSE:
                return self.pumping
            # Start pumpe hvis gennemsnittet er for tørt
            avg = (soil1 + soil2) / 2
            if avg < soil_min:
                self.pump.value(1)
                self.pumping = True
                self.pumpe_start_tid = nu

        return self.pumping

    def set_pumpe(self, state):
        self.pump.value(1 if state else 0)
        self.pumping = state
        if state:
            self.pumpe_start_tid = time.time()
            self.pumpe_slut_tid  = None
        else:
            self.pumpe_slut_tid  = time.time()
            self.pumpe_start_tid = None


class LightSystem:
    def __init__(self, ldr_pin, led_pin, led_antal, adc_dark, adc_bright):
        self.ldr = ADC(Pin(ldr_pin))
        self.ldr.width(ADC.WIDTH_12BIT)
        self.ldr.atten(ADC.ATTN_11DB)
        self.led = NeoPixel(Pin(led_pin), led_antal)
        self.antal = led_antal
        self.a = (0 - 100) / (adc_bright - adc_dark)
        self.b = 100 - self.a * adc_dark
        self.profil = STANDARD_PROFILE
        self.profil_navn = "standard"
        self.led_pct = 0
        self.set_color(0, 0, 0)

    def set_color(self, r, g, b):
        r = int(r / 100 * 255)
        g = int(g / 100 * 255)
        b = int(b / 100 * 255)
        for i in range(self.antal):
            self.led[i] = (r, g, b)
        self.led.write()

    def vaelg_profil(self, navn):
        if navn == "seedling":
            self.profil = SEEDLING_PROFILE
            self.profil_navn = "seedling"
        elif navn == "standard":
            self.profil = STANDARD_PROFILE
            self.profil_navn = "standard"

    def opdater(self):
        adc = self.ldr.read()
        led_pct = max(0, min(100, self.a * adc + self.b))
        self.led_pct = int(led_pct)
        skala = led_pct / 100
        r, g, b = self.profil
        self.set_color(r * skala, g * skala, b * skala)
        light = min(100, max(0, adc * 100 // ADC_BRIGHT))
        return light


class WaterLevel:
    def __init__(self, pin):
        try:
            self.sensor = Pin(pin, Pin.IN, Pin.PULL_DOWN)
        except ValueError:
            self.sensor = Pin(pin, Pin.IN)

    def read(self):
        return "Fyld vand" if self.sensor.value() == 1 else "Massere af vand"


uart         = UART(2, baudrate=115200, tx=UART_TX, rx=UART_RX)
water_system = WaterSystem(FUGT1_PIN, FUGT2_PIN, PUMP_PIN, SOIL_DRY, SOIL_WET)
light_system = LightSystem(LDR_PIN, LED_PIN, LED_ANTAL, ADC_DARK, ADC_BRIGHT)
water_level  = WaterLevel(VANDSTAND_PIN)


def modtag_indstillinger():
    global SOIL_MIN, SOIL_MAX
    if uart.any():
        try:
            linje = uart.readline().decode("utf-8", "ignore").strip()
            if not linje.startswith("indstil:"):
                return
            for d in linje.replace("indstil:", "").split(","):
                if "=" not in d:
                    continue
                key, val = d.split("=", 1)
                key = key.strip()
                val = val.strip()
                if key == "soil_min":    SOIL_MIN = int(val)
                elif key == "soil_max":  SOIL_MAX = int(val)
                elif key == "pumpe":     water_system.set_pumpe(val == "TIL")
                elif key == "lysprofil": light_system.vaelg_profil(val)
        except Exception:
            pass


while True:
    modtag_indstillinger()
    soil1, soil2 = water_system.read()
    light        = light_system.opdater()
    vandstand    = water_level.read()
    pumpe        = water_system.pump_if_needed(soil1, soil2, SOIL_MIN, SOIL_MAX)
    besked = "vandstand:{},soil1:{},soil2:{},light:{},pumpe:{},lysprofil:{},led:{}\n".format(
        vandstand, soil1, soil2, light,
        "TIL" if pumpe else "FRA",
        light_system.profil_navn,
        light_system.led_pct
    )
    uart.write(besked)
    print(besked)
    sleep(1)