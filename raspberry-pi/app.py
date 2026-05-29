from flask import Flask, render_template, request, redirect, url_for, jsonify
import sensor_reader, actuators, graphs, camera
from profiles import PLANT_PROFILES
import schedule, threading, time
from datetime import datetime
from camera import tag_billede_og_analyser

app = Flask(__name__)
sensor_reader.start()
aktiv_profil_key = "basilikum"

LIGHT_START_HOUR = 6  


def _lys_skema_loop():
    """Sender hvert minut om lyset må være tændt (06:00 -> 06 + profilens timer)."""
    time.sleep(3)  
    while True:
        profil = PLANT_PROFILES[aktiv_profil_key]
        timer = profil.get("lys_timer", 14)
        nu = datetime.now()
        time_nu = nu.hour + nu.minute / 60
        tilladt = LIGHT_START_HOUR <= time_nu < LIGHT_START_HOUR + timer
        actuators.set_lys_tilladt(tilladt)
        
        actuators.set_profil(profil["soil_min"], profil["soil_max"])
        time.sleep(60)

threading.Thread(target=_lys_skema_loop, daemon=True).start()


def automatisk_analyse():
    print("Automatisk analyse køres...")
    tag_billede_og_analyser()

schedule.every().day.at("12:00").do(automatisk_analyse)

def scheduler_interval():
    while True:
        schedule.run_pending()
        time.sleep(max(1, schedule.idle_seconds()))

threading.Thread(target=scheduler_interval, daemon=True).start()


@app.route("/")
def hjem():
    data     = sensor_reader.get_data()
    tilstand = actuators.get_tilstand()
    profil   = PLANT_PROFILES[aktiv_profil_key]
    return render_template("home.html", data=data, tilstand=tilstand, profil=profil)

@app.route("/api/data")
def api_data():
    return jsonify(sensor_reader.get_data())

@app.route("/api/grafer")
def api_grafer():
    historik = sensor_reader.get_historik(60)
    return jsonify(graphs.lav_alle_grafer(historik))

@app.route("/sensorer")
def sensorer():
    data     = sensor_reader.get_data()
    historik = sensor_reader.get_historik(60)
    grafer   = graphs.lav_alle_grafer(historik)
    return render_template("sensors.html", data=data, grafer=grafer)

@app.route("/styring", methods=["GET", "POST"])
def styring():
    if request.method == "POST":
        handling = request.form.get("handling")
        if handling == "pumpe_til":      actuators.set_pumpe(True)
        elif handling == "pumpe_fra":    actuators.set_pumpe(False)
        elif handling == "lys_seedling": actuators.set_lysprofil("seedling")
        elif handling == "lys_standard": actuators.set_lysprofil("standard")
        return redirect(url_for("styring"))
    data     = sensor_reader.get_data()
    tilstand = actuators.get_tilstand()
    return render_template("control.html", data=data, tilstand=tilstand)

@app.route("/profiler", methods=["GET", "POST"])
def profiler():
    global aktiv_profil_key
    if request.method == "POST":
        valgt = request.form.get("profil")
        if valgt in PLANT_PROFILES:
            aktiv_profil_key = valgt
            profil = PLANT_PROFILES[aktiv_profil_key]
            actuators.set_profil(
                profil["soil_min"],
                profil["soil_max"],
                profil.get("lysprofil", "standard"),
            )
        return redirect(url_for("profiler"))
    return render_template("profiles.html", profiler=PLANT_PROFILES, aktiv=aktiv_profil_key)

@app.route("/kamera", methods=["GET", "POST"])
def kamera():
    resultat = camera.seneste_resultat.copy()
    if request.method == "POST":
        resultat = camera.tag_billede_og_analyser()
    return render_template("camera.html", resultat=resultat)

@app.route("/galleri")
def galleri():
    billeder = camera.get_galleri(12)
    return render_template("gallery.html", billeder=billeder)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, use_reloader=False)