from flask import Flask, render_template, request, redirect, url_for

import sensor_reader
import actuators
import graphs
import camera
from profiles import PLANT_PROFILES
import schedule
import threading
import time
from camera import tag_billede_og_analyser

app = Flask(__name__)

# Start baggrundstråd der læser ESP32 via UART
sensor_reader.start()

# Holder styr på hvilken planteprofil der er aktiv
aktiv_profil_key = "basilikum"


# Kører den automatiske billedtagning ud fra et givent tidspunkt også sover scheduler funktionen efter beregning til næste billede
def automatisk_analyse():
    print("Automatisk analyse køres...")
    tag_billede_og_analyser()

schedule.every().day.at("12:00").do(automatisk_analyse)

def scheduler_interval():
    while True:
        schedule.run_pending()
        tid_til_næste = schedule.idle_seconds()
        time.sleep(max(1, tid_til_næste))

scheduler_tråd = threading.Thread(target=scheduler_interval, daemon=True)
scheduler_tråd.start()


# -------------------------------------------------------------------
# Hjem - dashboard oversigt
# -------------------------------------------------------------------
@app.route("/")
def hjem():
    data    = sensor_reader.get_data()
    tilstand = actuators.get_tilstand()
    profil  = PLANT_PROFILES[aktiv_profil_key]
    return render_template("home.html", data=data, tilstand=tilstand, profil=profil)


# -------------------------------------------------------------------
# Sensorer - live data + grafer
# -------------------------------------------------------------------
@app.route("/sensorer")
def sensorer():
    data     = sensor_reader.get_data()
    historik = sensor_reader.get_historik(30)
    grafer   = graphs.lav_alle_grafer(historik)
    return render_template("sensors.html", data=data, grafer=grafer)


# -------------------------------------------------------------------
# Manuel styring
# -------------------------------------------------------------------
@app.route("/styring", methods=["GET", "POST"])
def styring():
    if request.method == "POST":
        handling = request.form.get("handling")

        if handling == "pumpe_til":
            actuators.set_pumpe(True)
        elif handling == "pumpe_fra":
            actuators.set_pumpe(False)
        elif handling == "led_saet":
            rod = int(request.form.get("led_rod", 0))
            bla = int(request.form.get("led_bla", 0))
            actuators.set_led(rod, bla)
        elif handling == "led_fra":
            actuators.set_led(0, 0)

        return redirect(url_for("styring"))

    tilstand = actuators.get_tilstand()
    return render_template("control.html", tilstand=tilstand)


# -------------------------------------------------------------------
# Planteprofiler
# -------------------------------------------------------------------
@app.route("/profiler", methods=["GET", "POST"])
def profiler():
    global aktiv_profil_key
    if request.method == "POST":
        valgt = request.form.get("profil")
        if valgt in PLANT_PROFILES:
            aktiv_profil_key = valgt
            # Anvend profilens LED-indstilling med det samme
            profil = PLANT_PROFILES[aktiv_profil_key]
            actuators.set_led(profil["led_rod"], profil["led_bla"])
        return redirect(url_for("profiler"))

    return render_template(
        "profiles.html",
        profiler=PLANT_PROFILES,
        aktiv=aktiv_profil_key,
    )


# -------------------------------------------------------------------
# Kamera + Computer Vision
# -------------------------------------------------------------------
@app.route("/kamera", methods=["GET", "POST"])
def kamera():
    resultat = camera.seneste_resultat.copy()
    if request.method == "POST":
        resultat = camera.tag_billede_og_analyser()
    return render_template("camera.html", resultat=resultat)


# -------------------------------------------------------------------
# Billedgalleri
# -------------------------------------------------------------------
@app.route("/galleri")
def galleri():
    billeder = camera.get_galleri(12)
    return render_template("gallery.html", billeder=billeder)


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
