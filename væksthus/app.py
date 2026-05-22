import pigpio
from time import sleep, time
import smbus
import schedule
from flask import Flask, render_template, redirect, url_for
import threading
import os
import sqlite3
from datetime import datetime
from matplotlib.figure import Figure
import base64
from io import BytesIO

lights_on = False

RED_PIN = 12
BLUE_PIN = 13
PUMP_PIN = 26

RED_MAX = 8
BLUE_MAX = 55

RED_MIN = 11
BLUE_MIN = 1

LDR_ADDRESS = 0x48
SOIL_ADDRESS = 0x4b

bus = smbus.SMBus(1)

LDR_DARK = 900
LDR_LIGHT = 100

SOIL_DRY = 770
SOIL_WET = 290

SOIL_TARGET = 40
PUMP_DURATION = 0.05
PUMP_PAUSE = 5

LIGHT_ON_HOUR = 6
LIGHT_OFF_HOUR = 20

pi = pigpio.pi()

conn = sqlite3.connect("greenhouse.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS SoilMoisture (
    timestamp TEXT,
    moisture REAL
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS Images (
    filename TEXT
)
""")
conn.commit()

pi.set_mode(RED_PIN, pigpio.OUTPUT)
pi.set_mode(BLUE_PIN, pigpio.OUTPUT)
pi.set_mode(PUMP_PIN, pigpio.OUTPUT)

pi.set_PWM_range(RED_PIN, 100)
pi.set_PWM_range(BLUE_PIN, 100)

class WaterSystem:
    def __init__(self, bus, address, dry, wet, pump_pin, pi, cursor, conn):
        self.bus = bus
        self.address = address
        self.dry = dry
        self.wet = wet
        self.pump_pin = pump_pin
        self.pi = pi
        self.cursor = cursor
        self.conn = conn
        self.pumping = False

    def read(self):
        rd = self.bus.read_word_data(self.address, 0)
        data = ((rd & 0xFF) << 8) | ((rd & 0xFF00) >> 8)
        raw = data >> 2

        if raw < self.wet:
            return 100

        pct = (self.dry - raw) * 100 / (self.dry - self.wet)

        if pct < 0:
            return 0

        return pct

    def save(self, value):
        timestamp = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        self.cursor.execute(
            "INSERT INTO SoilMoisture VALUES (?, ?)",
            (timestamp, value)
        )
        self.conn.commit()

    def _pump_cycle(self, duration, pause):
        self.pumping = True
        self.pi.write(self.pump_pin, 1)
        sleep(duration)
        self.pi.write(self.pump_pin, 0)
        sleep(pause)
        self.pumping = False

    def pump_if_needed(self, soil_pct, target, duration, pause):
        if soil_pct < target and not self.pumping:
            threading.Thread(
                target=self._pump_cycle,
                args=(duration, pause),
                daemon=True
            ).start()

water_system = WaterSystem(
    bus,
    SOIL_ADDRESS,
    SOIL_DRY,
    SOIL_WET,
    PUMP_PIN,
    pi,
    cursor,
    conn
)

class LightSystem:
    def __init__(self, pi, red_pin, blue_pin, red_max, blue_max, red_min, blue_min,
                 bus, ldr_address, ldr_light, ldr_dark):
        self.pi = pi
        self.red_pin = red_pin
        self.blue_pin = blue_pin

        self.red_max = red_max
        self.blue_max = blue_max
        self.red_min = red_min
        self.blue_min = blue_min

        self.bus = bus
        self.ldr_address = ldr_address
        self.ldr_light = ldr_light
        self.ldr_dark = ldr_dark

    def read(self):
        rd = self.bus.read_word_data(self.ldr_address, 0)
        data = ((rd & 0xFF) << 8) | ((rd & 0xFF00) >> 8)
        raw = data >> 2

        if raw < self.ldr_light:
            return 0

        pct = (raw - self.ldr_light) * 100 / (self.ldr_dark - self.ldr_light)

        if pct > 100:
            return 100

        return pct

    def set_led_percent(self, red_pct, blue_pct):
        if red_pct < 0:
            red_pct = 0
        elif red_pct > 100:
            red_pct = 100

        if blue_pct < 0:
            blue_pct = 0
        elif blue_pct > 100:
            blue_pct = 100

        if red_pct > 0:
            red_pct = RED_MIN + (red_pct / 100) * (100 - RED_MIN)

        if blue_pct > 0:
            blue_pct = BLUE_MIN + (blue_pct / 100) * (100 - BLUE_MIN)

        red_value = int((red_pct / 100) * RED_MAX)
        blue_value = int((blue_pct / 100) * BLUE_MAX)

        self.pi.set_PWM_dutycycle(self.red_pin, red_value)
        self.pi.set_PWM_dutycycle(self.blue_pin, blue_value)

    def off(self):
        self.pi.set_PWM_dutycycle(self.red_pin, 0)
        self.pi.set_PWM_dutycycle(self.blue_pin, 0)

    def update(self, lights_on):
        pct = self.read()

        if lights_on and pct > 0:
            self.set_led_percent(pct, pct)
        else:
            self.off()

        return pct

light_system = LightSystem(
    pi,
    RED_PIN,
    BLUE_PIN,
    RED_MAX,
    BLUE_MAX,
    RED_MIN,
    BLUE_MIN,
    bus,
    LDR_ADDRESS,
    LDR_LIGHT,
    LDR_DARK
)

def light_on():
    global lights_on
    lights_on = True

def light_off():
    global lights_on
    lights_on = False
    light_system.off()

schedule.every().day.at("06:00").do(light_on)
schedule.every().day.at("20:00").do(light_off)

current_hour = datetime.now().hour
lights_on = LIGHT_ON_HOUR <= current_hour < LIGHT_OFF_HOUR

last_save_time = 0
SAVE_INTERVAL = 3600

def control_loop():
    global last_save_time

    while True:
        schedule.run_pending()

        light_pct = light_system.update(lights_on)

        soil_pct = water_system.read()

        current_time = time()
        if current_time - last_save_time > SAVE_INTERVAL:
            water_system.save(soil_pct)
            last_save_time = current_time

        water_system.pump_if_needed(soil_pct, SOIL_TARGET, PUMP_DURATION, PUMP_PAUSE)

        print(f"LEDs: {int(light_pct)}% | Moisture: {int(soil_pct)}% | LEDs active?: {lights_on}")

        sleep(1)

app = Flask(__name__)

@app.route("/")
def home():
    cursor.execute("SELECT * FROM Images ORDER BY rowid DESC")
    rows = cursor.fetchall()

    image = None

    for row in rows:
        filepath = f"static/img/{row[0]}"
        if os.path.exists(filepath):
            image = row[0]
            break
        else:
            cursor.execute("DELETE FROM Images WHERE filename = ?", (row[0],))
            conn.commit()

    return render_template("home.html", image=image)

@app.route("/take_photo")
def take_photo():
    filename = datetime.now().strftime("%d-%m-%Y_%H-%M-%S.jpg")

    result = os.system(f"libcamera-still -o static/img/{filename}")
    
    cursor.execute("INSERT INTO Images VALUES (?)", (filename,))
    conn.commit()

    return redirect(url_for("home"))

@app.route("/soil")
def soil():
    cursor.execute("SELECT * FROM SoilMoisture ORDER BY rowid DESC LIMIT 10")
    rows = cursor.fetchall()

    fig = Figure()
    ax = fig.subplots()

    x = []
    y = []

    ax.tick_params(axis='x', which='both', rotation=30)
    fig.subplots_adjust(bottom=0.3)
    ax.set_xlabel("Timestamps")
    ax.set_ylabel("Soil moisture (%)")

    for row in rows:
        x.append(row[0])
        y.append(row[1])

    ax.plot(x, y)

    buf = BytesIO()
    fig.savefig(buf, format="png")

    data = base64.b64encode(buf.getbuffer()).decode("ascii")

    return render_template("soil.html", soil_data=data)

@app.route("/gallery")
def gallery():
    cursor.execute("SELECT * FROM Images ORDER BY rowid DESC")
    rows = cursor.fetchall()

    valid_images = []

    for row in rows:
        filepath = f"static/img/{row[0]}"
        if os.path.exists(filepath):
            valid_images.append(row)
        else:
            cursor.execute("DELETE FROM Images WHERE filename = ?", (row[0],))
            conn.commit()

    return render_template("gallery.html", image_rows=valid_images)

if __name__ == "__main__":
    try:
        threading.Thread(target=control_loop, daemon=True).start()
        app.run(host="0.0.0.0", port=5000, use_reloader=False)

    except KeyboardInterrupt:
        pass
    finally:
        light_system.off()
        pi.write(PUMP_PIN, 0)
        pi.stop()