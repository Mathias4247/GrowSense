# Genererer Matplotlib-grafer og returnerer dem som base64-strenge.
# Samme teknik som den eksisterende app.py bruger med BytesIO + base64.

from matplotlib.figure import Figure
from io import BytesIO
import base64


def lav_graf(x_vals: list, y_vals: list, xlabel: str, ylabel: str, titel: str) -> str:
    """Returnerer en base64-encoded PNG-streng klar til brug i <img src='...'> i HTML."""
    fig = Figure(figsize=(7, 3))
    ax = fig.subplots()
    ax.plot(x_vals, y_vals, marker="o", markersize=3, linewidth=1.5)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(titel, fontsize=10)
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.tick_params(axis="y", labelsize=8)
    fig.subplots_adjust(bottom=0.3)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    return base64.b64encode(buf.getbuffer()).decode("ascii")


def lav_alle_grafer(historik: list) -> dict:
    if not historik:
        return {}

    timestamps = [r.get("timestamp", "") for r in historik]
    timestamps = [t[11:19] if len(t) >= 19 else t for t in timestamps]

    def saml(kolonne):
        vals = []
        for r in historik:
            try:
                vals.append(float(r.get(kolonne) or 0))
            except ValueError:
                vals.append(0.0)
        return vals

    def saml_vandstand(kolonne):        # ← tilføj her
        vals = []
        for r in historik:
            val = r.get(kolonne, "")
            vals.append(1 if val == "Fyld vand" else 0)
        return vals

    return {
        "soil":      lav_graf(timestamps, saml("soil"),      "Tidspunkt", "Jordfugtighed %", "Jordfugtighed over tid"),
        "light":     lav_graf(timestamps, saml("light"),     "Tidspunkt", "Lysniveau",        "Lysniveau over tid"),
        "vandstand": lav_graf(timestamps, saml_vandstand("vandstand"), "Tidspunkt", "Lav vandstand (1=ja)", "Vandstand over tid"),  # ← tilføj her
    }