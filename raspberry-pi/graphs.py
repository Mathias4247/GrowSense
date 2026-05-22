import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io, base64
from datetime import datetime

def _til_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded

def _timestamps(raekker):
    tider = []
    for r in raekker:
        try:
            tider.append(datetime.strptime(r["timestamp"], "%d-%m-%Y %H:%M:%S"))
        except Exception:
            tider.append(None)
    return tider

def _lav_graf(tider, vaerdier, titel, ylabel, farve):
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(tider, vaerdier, color=farve, marker="o", markersize=3, linewidth=1.5)
    ax.set_title(titel)
    ax.set_xlabel("Tidspunkt")
    ax.set_ylabel(ylabel)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    fig.autofmt_xdate(rotation=45)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return _til_base64(fig)

def lav_alle_grafer(raekker):
    tom = {"soil1": None, "soil2": None, "light": None, "vandstand": None}
    if not raekker:
        return tom

    tider       = _timestamps(raekker)
    soil1_vals  = []
    soil2_vals  = []
    light_vals  = []
    vand_vals   = []

    for r in raekker:
        try:
            soil1_vals.append(float(r.get("soil1", r.get("soil", 0))))
        except Exception:
            soil1_vals.append(0.0)
        try:
            soil2_vals.append(float(r.get("soil2", r.get("soil", 0))))
        except Exception:
            soil2_vals.append(0.0)
        try:
            light_vals.append(int(float(r.get("light", 0))))
        except Exception:
            light_vals.append(0)
        v = r.get("vandstand", "")
        vand_vals.append(1 if "Massere" in v or v == "OK" else 0)

    return {
        "soil1":     _lav_graf(tider, soil1_vals, "Jordfugtighed — Plante 1", "Fugtighed %",     "#2E7D32"),
        "soil2":     _lav_graf(tider, soil2_vals, "Jordfugtighed — Plante 2", "Fugtighed %",     "#1565C0"),
        "light":     _lav_graf(tider, light_vals,  "Lysniveau over tid",       "Lys %",           "#F9A825"),
        "vandstand": _lav_graf(tider, vand_vals,   "Vandstand over tid",       "1=OK  0=Fyld",   "#0288D1"),
    }