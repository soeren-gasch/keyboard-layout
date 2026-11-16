"""Erzeugt die Tastatur- und Bewertungskonfigurationen für den keyboard_layout_optimizer.

Aufruf (aus dem Repo-Wurzelverzeichnis):
    python3 optimizer/konfiguration.py

Ausgabe:
    optimizer/tastaturen/<tastatur>-<variante>-<kosten>.yml   Tastatur, Ebenen, Modifikatoren
    optimizer/bewertung/<kosten>.yml                        Bewertungsparameter

YAML ist eine Obermenge von JSON; die Dateien werden deshalb als JSON geschrieben und vom Optimizer als YAML gelesen.

Modell (Entscheidungen vom 16.11.2026, siehe optimizer/README.md):
- 32 Tasten: je Hand 3 × 5 plus eine Daumentaste.
- Ebene 0 Basis, Ebene 1 Shift, Ebene 2 Symbole, Ebene 3 Navigation und Ziffernblock.
- Shift, Symbol- und Navigations-Ebene werden über Home-Row-Tasten gehalten (bei Variante B die Symbol-Ebene über den
  Daumen), links und rechts symmetrisch. Gehalten wird jeweils auf der Gegenhand (Zeichen links -> Taste rechts).
- Ctrl, Alt und Win liegen ebenfalls auf der Grundreihe, kommen in den Korpora aber nicht vor und werden deshalb nicht
  modelliert; ihre Lage steht nur zur Dokumentation in VARIANTEN.
- Symbol- und Navigations-Ebene sind fest (wie in Sörens Oryx-Layout); optimiert werden Basis und Shift.
"""

import copy
import json
from pathlib import Path

HIER = Path(__file__).resolve().parent
OPTIMIZER = Path.home() / "keyboard" / "keyboard_layout_optimizer"

# ----------------------------------------------------------------------------- Geometrie
# Je Tastatur: Spalten der linken Hand von außen nach innen (kleiner Finger, Ring, Mittel, Zeige, Zeige innen) als
# (x, Versatz in y) in Tasten-Einheiten, die genutzte Daumentaste links als (x, y) und die Breite, an der die rechte
# Hand gespiegelt wird (x_rechts = breite - x_links). Reihen liegen bei y = 1, 2, 3 (plus Versatz).
# Die Matrix-Positionen sind für alle Tastaturen gleich (links x 1..5, rechts 10..14, Daumen 5 und 10), damit
# Modifikatoren und die Shortcut-Metrik (Matrix-x <= 5 = linke Hand) überall gleich wirken.
EINHEIT = 50.0
GEOMETRIEN = {
    # QMK keyboards/zsa/voyager/keyboard.json; Daumen k24/k51 unter der inneren Spalte
    "voyager32": {"spalten": [(1, 0.5), (2, 0.25), (3, 0.0), (4, 0.25), (5, 0.5)], "daumen": (5, 4.5), "breite": 15},
    # QMK ferris/sweep LAYOUT_split_3x5_2, Versatz der ersten Reihe; Daumen: die äußere der beiden (3,5 | 3,75)
    "sweep": {"spalten": [(1, 0.93), (2, 0.31), (3, 0.0), (4, 0.28), (5, 0.42)], "daumen": (4.5, 3.75 + 1),
              "breite": 15},
    # QMK crkbd LAYOUT_split_3x5_3; Daumen: die mittlere der drei (4 | 3,7)
    "corne": {"spalten": [(1, 0.3), (2, 0.1), (3, 0.0), (4, 0.1), (5, 0.2)], "daumen": (5, 3.7 + 1), "breite": 15},
}
FINGER_LINKS = ["Pinky", "Ring", "Middle", "Index", "Index"]
FINGER_RECHTS = ["Index", "Index", "Middle", "Ring", "Pinky"]
MATRIX_LINKS = [1, 2, 3, 4, 5]
MATRIX_RECHTS = [10, 11, 12, 13, 14]  # innen -> außen
MATRIX_DAUMEN = {"links": 5, "rechts": 10}

# ----------------------------------------------------------------------------- Kosten je Taste
# "standard": Werte der Corne-Konfiguration des Optimizers (Community), auf 3 × 5 gekürzt.
# "soeren": Sörens Einschätzung vom 16.11.2026: kleine Finger weniger schlimm (Geige), Ringfinger unangenehmer,
#           besonders der Ringfinger in der unteren Reihe.
# Reihenfolge je Reihe: links kleiner Finger .. Zeige innen | rechts Zeige innen .. kleiner Finger
KOSTEN = {
    "standard": {
        "oben":   [20, 9, 5, 11, 17,   17, 11, 5, 9, 20],
        "mitte":  [5, 3, 2, 2, 8,      8, 2, 2, 3, 5],
        "unten":  [10, 11, 11, 7, 11,  11, 7, 11, 11, 10],
        "daumen": [3, 3],
        "finger_last": {"Pinky": 1.0, "Ring": 1.6, "Middle": 2.0, "Index": 2.0},
    },
    "soeren": {
        "oben":   [14, 11, 5, 11, 17,  17, 11, 5, 11, 14],
        "mitte":  [4, 4, 2, 2, 8,      8, 2, 2, 4, 4],
        "unten":  [8, 16, 11, 7, 11,   11, 7, 11, 16, 8],
        "daumen": [3, 3],
        "finger_last": {"Pinky": 1.3, "Ring": 1.3, "Middle": 2.0, "Index": 2.0},
    },
}

# ----------------------------------------------------------------------------- Home-Row-Varianten
# Spalte 0..4 von außen nach innen (kleiner Finger .. Zeige innen), "daumen" = Daumentaste. Links und rechts gleich.
VARIANTEN = {
    "A": {"beschreibung": "wie heute plus Alt: kleiner Finger Navigation, Ring Symbole, Mittel Shift, Zeige Ctrl, innen Win, Daumen Alt",
          "shift": 2, "symbol": 1, "navigation": 0},
    "B": {"beschreibung": "Muster GACS: kleiner Finger Win, Ring Alt, Mittel Ctrl, Zeige Shift, innen Navigation, Daumen Symbole",
          "shift": 3, "symbol": "daumen", "navigation": 4},
    "C": {"beschreibung": "Ring entlastet: kleiner Finger Navigation, Ring Win/Alt, Mittel Symbole, Zeige Shift, innen Ctrl, Daumen Alt",
          "shift": 3, "symbol": 2, "navigation": 0},
}

# ----------------------------------------------------------------------------- Ebenen
# Je Reihe 10 Zeichen (links außen -> innen, rechts innen -> außen) und 2 Daumen. Aus Sörens Oryx-Layout (xmKwY):
# Symbole links aus Oryx-Ebene 1, rechts aus Ebene 2; Navigation links aus Ebene 3, Ziffern rechts aus Ebene 4.
SYMBOLE = {
    "oben":  ["@", "_", "[", "]", "^",   "!", "<", ">", "=", "&"],
    "mitte": ["\\", "/", "{", "}", "*",  "?", "(", ")", "-", ":"],
    "unten": ["#", "$", "|", "~", "`",   "+", "%", '"', "'", ";"],
}
NAVIGATION = {
    "oben":  ["⇞", "⌫", "⇡", "⌦", "⇟",   "*", "7", "8", "9", "/"],
    "mitte": ["⇱", "⇠", "⇣", "⇢", "⇲",   "+", "4", "5", "6", "-"],
    "unten": ["⎋", "\t", "⎀", "\n", "↷",  "", "1", "2", "3", ","],
    "daumen": ["↶", "0"],
}
SHIFT = {",": ";", ".": ":", "-": "_", " ": " ", "ß": "ẞ"}

# Basis-Belegungen (Reihenfolge der Tasten: oben 10, Mitte 10, unten 10, Daumen links, Daumen rechts)
IST = "xflpbäqo,ö" + "csntgj aiu" + "mwvdkßzüyh" + "er"      # Oryx xmKwY, Revision NjXvj
NEU_START = "xflpbäjo,ö" + "csntg. aiu" + "mwvdk-züyh" + "er"  # Start für die Optimierung: q, ß raus; Punkt, Strich rein


def _geometrie(name):
    g = GEOMETRIEN[name]
    links = g["spalten"]
    rechts = [(g["breite"] - x, v) for x, v in reversed(links)]  # innen -> außen
    tasten = []
    for zeile, (reihe, dy) in enumerate((("oben", 1.0), ("mitte", 2.0), ("unten", 3.0))):
        for i, (x, versatz) in enumerate(links):
            tasten.append({"reihe": reihe, "index": i, "hand": "Left", "finger": FINGER_LINKS[i],
                           "matrix": [MATRIX_LINKS[i], zeile + 1], "pos": [x * EINHEIT, (dy + versatz) * EINHEIT]})
        for i, (x, versatz) in enumerate(rechts):
            tasten.append({"reihe": reihe, "index": 5 + i, "hand": "Right", "finger": FINGER_RECHTS[i],
                           "matrix": [MATRIX_RECHTS[i], zeile + 1], "pos": [x * EINHEIT, (dy + versatz) * EINHEIT]})
    x, y = g["daumen"]
    for seite, hand, dx in (("links", "Left", x), ("rechts", "Right", g["breite"] - x)):
        tasten.append({"reihe": "daumen", "index": 0 if seite == "links" else 1, "hand": hand, "finger": "Thumb",
                       "matrix": [MATRIX_DAUMEN[seite], 4], "pos": [dx * EINHEIT, y * EINHEIT]})
    return tasten


def _unbalancing(t):
    # wie Corne: innere Spalte zieht die Hand seitlich, obere/untere Reihe der inneren Spalte zusätzlich vertikal
    if t["finger"] == "Thumb":
        return [0, 0]
    innen = (t["hand"] == "Left" and t["index"] == 4) or (t["hand"] == "Right" and t["index"] == 5)
    dx = (1 if t["hand"] == "Left" else -1) if innen else 0
    dy = {"oben": 1, "mitte": 0, "unten": -1}[t["reihe"]] if innen else (
        0.5 if t["reihe"] == "oben" and t["finger"] in ("Pinky", "Index") else 0)
    return [dx, dy]


def _reihen(liste, tasten):
    """Teilt eine flache Liste (je Taste) in die Reihen-Struktur des Optimizers."""
    reihen, aktuell, letzte = [], [], None
    for t, wert in zip(tasten, liste):
        if t["reihe"] != letzte and aktuell:
            reihen.append(aktuell)
            aktuell = []
        aktuell.append(wert)
        letzte = t["reihe"]
    reihen.append(aktuell)
    return reihen


def _plot(n):
    z = lambda i: "{{" + str(i) + "}}"  # noqa: E731
    reihe = lambda a: " ".join(z(i) for i in range(a, a + 5))  # noqa: E731
    return (f"{reihe(0)}   {reihe(5)}\n{reihe(10)}   {reihe(15)}\n{reihe(20)}   {reihe(25)}\n"
            f"          {z(30)}   {z(31)}\n")


def tastatur(variante, kosten, basis, mit_q_ss_auf_symbol=True, geometrie="voyager32"):
    tasten = _geometrie(geometrie)
    k = KOSTEN[kosten]
    kosten_liste = k["oben"] + k["mitte"] + k["unten"] + k["daumen"]
    symmetrie = list(range(1, 6)) + list(range(5, 0, -1)) + list(range(6, 11)) + list(range(10, 5, -1)) + \
        list(range(11, 16)) + list(range(15, 10, -1)) + [16, 16]

    # Zeichen je Taste und Ebene
    zeichen = []
    for i, t in enumerate(tasten):
        b = basis[i]
        s = SHIFT.get(b, b.upper())
        if t["reihe"] == "daumen":
            sym = ("q" if t["index"] == 0 else "ß") if mit_q_ss_auf_symbol else ""
            nav = NAVIGATION["daumen"][t["index"]]
        else:
            sym = SYMBOLE[t["reihe"]][t["index"]]
            nav = NAVIGATION[t["reihe"]][t["index"]]
        zeichen.append([b, s, sym, nav])

    v = VARIANTEN[variante]

    def position(spalte, hand):
        if spalte == "daumen":
            return MATRIX_DAUMEN["links" if hand == "Left" else "rechts"], 4
        return (MATRIX_LINKS[spalte] if hand == "Left" else MATRIX_RECHTS[4 - spalte]), 2

    def modifikator(spalte):
        return {"Left": {"type": "hold", "value": [list(position(spalte, "Left"))]},
                "Right": {"type": "hold", "value": [list(position(spalte, "Right"))]}}

    return {
        "keyboard": {
            "matrix_positions": _reihen([t["matrix"] for t in tasten], tasten),
            "positions": _reihen([t["pos"] for t in tasten], tasten),
            "hands": _reihen([t["hand"] for t in tasten], tasten),
            "fingers": _reihen([t["finger"] for t in tasten], tasten),
            "key_costs": _reihen(kosten_liste, tasten),
            "unbalancing_positions": _reihen([_unbalancing(t) for t in tasten], tasten),
            "symmetries": _reihen(symmetrie, tasten),
            "finger_resting_positions": {
                "Left": {f: tasten[10 + i]["pos"] for i, f in enumerate(["Pinky", "Ring", "Middle", "Index"])} |
                        {"Thumb": tasten[30]["pos"]},
                "Right": {f: tasten[19 - i]["pos"] for i, f in enumerate(["Pinky", "Ring", "Middle", "Index"])} |
                         {"Thumb": tasten[31]["pos"]},
            },
            "plot_template": _plot(32),
            "plot_template_short": _plot(32),
        },
        "base_layout": {
            "keys": _reihen(zeichen, tasten),
            "fixed_keys": _reihen([False] * 32, tasten),
            "fixed_layers": [2, 3],
            "grouped_layers": 2,
            # Reihenfolge = Ebene 1 (Shift), 2 (Symbole), 3 (Navigation)
            "modifiers": [modifikator(v["shift"]), modifikator(v["symbol"]), modifikator(v["navigation"])],
        },
    }


def bewertung(kosten):
    """Standard-Bewertung des Optimizers mit zwei Änderungen: Kürzel-Tasten (Strg+Z/X/C/V unter Windows, Maus rechts)
    sollen auf der linken Hand liegen; die angestrebte Fingerlast folgt dem Kostenprofil."""
    import re

    text = (OPTIMIZER / "config" / "evaluation" / "default.yml").read_text(encoding="utf-8")
    text = text.replace("  shortcut_keys:\n    enabled: false", "  shortcut_keys:\n    enabled: true", 1)
    text = re.sub(r"shortcut_chars: cvx", "shortcut_chars: zxcv", text, count=1)
    last = KOSTEN[kosten]["finger_last"]
    for hand in ("Left", "Right"):
        for finger, wert in last.items():
            text = re.sub(rf"(\[{hand}, {finger}\]: )[0-9.]+", rf"\g<1>{wert}", text, count=1)
    return text


def _schreibe(pfad, text):
    """Schreibt nur bei Änderung (laufende Optimierungen lesen die Dateien)."""
    if not pfad.exists() or pfad.read_text(encoding="utf-8") != text:
        pfad.write_text(text, encoding="utf-8")


def main():
    (HIER / "tastaturen").mkdir(exist_ok=True)
    (HIER / "bewertung").mkdir(exist_ok=True)
    for kosten in KOSTEN:
        _schreibe(HIER / "bewertung" / f"{kosten}.yml",
                  "# Erzeugt von optimizer/konfiguration.py aus config/evaluation/default.yml des Optimizers\n"
                  + bewertung(kosten))
        for geometrie in GEOMETRIEN:
            for variante in VARIANTEN:
                cfg = tastatur(variante, kosten, NEU_START, geometrie=geometrie)
                _schreibe(HIER / "tastaturen" / f"{geometrie}-{variante}-{kosten}.yml",
                          json.dumps(cfg, ensure_ascii=False, indent=1) + "\n")
    # Ist-Zustand: q und ß auf der Basis, kein Punkt und kein Strich auf der Basis, Ebenen wie in Oryx (Variante A)
    ist = tastatur("A", "standard", IST, mit_q_ss_auf_symbol=False)
    _schreibe(HIER / "tastaturen" / "voyager32-ist.yml", json.dumps(ist, ensure_ascii=False, indent=1) + "\n")
    print("geschrieben:", sorted(p.name for p in (HIER / "tastaturen").glob("*.yml")))


if __name__ == "__main__":
    main()
