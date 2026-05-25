from machine import Pin, ADC, UART
from neopixel import NeoPixel
from time import sleep
import time

# ====== PIN CONFIGURATION ======
SOIL1_PIN       = 34
SOIL2_PIN       = 35
LDR_PIN         = 39
WATER_LEVEL_PIN = 25
PUMP_PIN        = 27
LED_PIN         = 18
LED_COUNT       = 22
UART_TX         = 4
UART_RX         = 5

# ====== CALIBRATION ======
SOIL_DRY   = 2600
SOIL_WET   = 870
ADC_DARK   = 0
ADC_BRIGHT = 1615

# ====== THRESHOLDS ======
SOIL_MIN = 50
SOIL_MAX = 70

# ====== LIGHT PROFILES (R, G, B in %) ======
PROFILES = {
    "seedling": (25, 100, 25),
    "standard": (70, 100, 58),
}

# ====== PUMP TIMING ======
PUMP_DURATION    = 0.1     # seconds the pump runs each time
PUMP_PAUSE       = 3    # seconds to wait after stopping before measuring again
PUMP_LED_DELAY   = 3     # seconds LED is off before the pump starts
LED_RESUME_DELAY = 3     # seconds after the pump stops before the LED turns on again

# ====== SENSOR TIMING ======
SOIL_INTERVAL  = 5     # seconds between soil moisture readings


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


class WaterSystem:
    def __init__(self, soil1_pin, soil2_pin, pump_pin, dry, wet, light=None):
        self.soil1 = self._adc(soil1_pin)
        self.soil2 = self._adc(soil2_pin)
        self.pump = Pin(pump_pin, Pin.OUT)
        self.pump.value(0)
        self.dry = dry
        self.wet = wet
        self.light = light          # reference to LightSystem
        self.pumping = False
        self.start_time = None
        self.end_time = None
        self.last_soil = (0, 0)     # cached reading
        self.last_read_time = None

    def _adc(self, pin):
        adc = ADC(Pin(pin))
        adc.atten(ADC.ATTN_11DB)
        return adc

    def _to_percent(self, raw):
        pct = (self.dry - raw) * 100 / (self.dry - self.wet)
        return clamp(int(round(pct)))

    def read(self):
        # Only read the sensors every SOIL_INTERVAL seconds, otherwise reuse last value
        now = time.time()
        if self.last_read_time is None or now - self.last_read_time >= SOIL_INTERVAL:
            self.last_soil = (
                self._to_percent(self.soil1.read()),
                self._to_percent(self.soil2.read()),
            )
            self.last_read_time = now
        return self.last_soil

    def _set_pump(self, state):
        if state:
            # Turn LED off and wait PUMP_LED_DELAY seconds before the pump starts
            if self.light:
                self.light.set_color(0, 0, 0)
                sleep(PUMP_LED_DELAY)
            self.pump.value(1)
        else:
            self.pump.value(0)
        self.pumping = state

    def lights_should_be_off(self):
        # LEDs stay off while pumping, and for LED_RESUME_DELAY seconds after it stops
        if self.pumping:
            return True
        if self.end_time and time.time() - self.end_time < LED_RESUME_DELAY:
            return True
        return False

    def pump_if_needed(self, soil1, soil2, soil_min, soil_max):
        now = time.time()
        if self.pumping:
            # Stop once it has run long enough
            if self.start_time and now - self.start_time >= PUMP_DURATION:
                self._set_pump(False)
                self.end_time = now
        else:
            # Wait out the pause so water can soak in
            if self.end_time and now - self.end_time < PUMP_PAUSE:
                return self.pumping
            # Start if the average is too dry
            if (soil1 + soil2) / 2 < soil_min:
                self._set_pump(True)
                self.start_time = now
        return self.pumping

    def set_pump(self, state):
        self._set_pump(state)
        self.start_time = time.time() if state else None
        self.end_time = None if state else time.time()


class LightSystem:
    def __init__(self, ldr_pin, led_pin, led_count, adc_dark, adc_bright):
        self.ldr = ADC(Pin(ldr_pin))
        self.ldr.width(ADC.WIDTH_12BIT)
        self.ldr.atten(ADC.ATTN_11DB)
        self.led = NeoPixel(Pin(led_pin), led_count)
        self.count = led_count
        # Linear conversion: dark -> 100%, bright -> 0%
        self.a = -100 / (adc_bright - adc_dark)
        self.b = 100 - self.a * adc_dark
        self.profile = PROFILES["standard"]
        self.profile_name = "standard"
        self.led_percent = 0
        # The Pi decides (from the clock) whether light is allowed right now
        self.light_allowed = True
        self.set_color(0, 0, 0)         # start with LEDs off

    def set_color(self, r, g, b):
        color = (int(r / 100 * 255), int(g / 100 * 255), int(b / 100 * 255))
        for i in range(self.count):
            self.led[i] = color
        self.led.write()

    def select_profile(self, name):
        if name in PROFILES:
            self.profile = PROFILES[name]
            self.profile_name = name

    def set_light_allowed(self, state):
        # The Pi tells us whether the current time is inside the light window
        self.light_allowed = state

    def update(self, keep_off=False):
        adc = self.ldr.read()
        ambient = clamp(adc * 100 // ADC_BRIGHT)     # daylight outside, 0-100 %

        if keep_off or not self.light_allowed:
            # Pump priority, or outside the allowed time window -> LEDs off
            self.led_percent = 0
        else:
            # Allowed: LEDs follow darkness (on when dark, off in daylight)
            self.led_percent = clamp(int(self.a * adc + self.b))

        scale = self.led_percent / 100
        r, g, b = self.profile
        self.set_color(r * scale, g * scale, b * scale)
        return ambient


class WaterLevel:
    def __init__(self, pin):
        try:
            self.sensor = Pin(pin, Pin.IN, Pin.PULL_UP)
        except ValueError:
            self.sensor = Pin(pin, Pin.IN)

    def read(self):
        if self.sensor.value() == 1:
            return "Dine planter mangler vand!"
        return "Dine planter er glade :)"


uart = UART(2, baudrate=115200, tx=UART_TX, rx=UART_RX)
light_system = LightSystem(LDR_PIN, LED_PIN, LED_COUNT, ADC_DARK, ADC_BRIGHT)
water_system = WaterSystem(SOIL1_PIN, SOIL2_PIN, PUMP_PIN, SOIL_DRY, SOIL_WET, light_system)
water_level_sensor = WaterLevel(WATER_LEVEL_PIN)


def receive_settings():
    global SOIL_MIN, SOIL_MAX
    if not uart.any():
        return
    try:
        line = uart.readline().decode("utf-8", "ignore").strip()
        if not line.startswith("indstil:"):
            return
        for part in line.replace("indstil:", "").split(","):
            if "=" not in part:
                continue
            key, value = (s.strip() for s in part.split("=", 1))
            if key == "soil_min":
                SOIL_MIN = int(value)
            elif key == "soil_max":
                SOIL_MAX = int(value)
            elif key == "pumpe":
                water_system.set_pump(value == "TIL")
            elif key == "lysprofil":
                light_system.select_profile(value)
            elif key == "lys":
                light_system.set_light_allowed(value == "TIL")
    except Exception:
        pass


try:
    while True:
        receive_settings()
        soil1, soil2 = water_system.read()
        # Decide pump state FIRST, then let the LED follow it (never on together)
        pumping = water_system.pump_if_needed(soil1, soil2, SOIL_MIN, SOIL_MAX)
        light = light_system.update(water_system.lights_should_be_off())
        water_status = water_level_sensor.read()

        message = "vandstand:{},soil1:{},soil2:{},light:{},pumpe:{},lysprofil:{},led:{}\n".format(
            water_status, soil1, soil2, light,
            "TIL" if pumping else "FRA",
            light_system.profile_name,
            light_system.led_percent,
        )
        uart.write(message)
        print(message)
        sleep(1)
finally:
    # Always turn everything off when the program stops (crash, reset or Ctrl+C)
    water_system.pump.value(0)
    light_system.set_color(0, 0, 0)
    print("System slukket - pumpe og LED slaaet fra")