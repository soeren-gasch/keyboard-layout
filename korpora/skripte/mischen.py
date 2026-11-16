"""Mischt N-Gramme mehrerer Quellen gewichtet zu einem abgeleiteten Datensatz.

Aufruf (aus dem Repo-Wurzelverzeichnis):
    python3 korpora/skripte/mischen.py korpora/mischungen/de-standard.json

Die Rezeptdatei nennt Quellen aus korpora/ngramme/ mit Gewichten. Jede Quelle wird je
N-Gramm-Ordnung auf relative Häufigkeiten gebracht und dann gewichtet summiert. Ein Gewicht
ist damit der Anteil an allen Zeichen (Tastenanschlägen) der Mischung. Gewichte werden auf
die Summe 1 normiert.

Ausgabe unter korpora/mischungen/<name>/ im selben Format wie die Quellen; die Anzahlen sind
relative Häufigkeiten mal SKALA, gerundet. N-Gramme, die dabei auf 0 fallen, entfallen.
"""

import argparse
import datetime
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from zaehlen import demaskiere, maskiere  # noqa: E402

KORPORA = Path(__file__).resolve().parent.parent
SKALA = 10**10


def lies_ngramme(pfad):
    zaehler = Counter()
    with open(pfad, encoding="utf-8") as f:
        for zeile in f:
            anzahl, ngramm = zeile.rstrip("\n").split(" ", 1)
            zaehler[demaskiere(ngramm)] += float(anzahl)
    return zaehler


def _sha256(pfad):
    return hashlib.sha256(Path(pfad).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("rezept", help="JSON-Datei mit {'beschreibung': ..., 'bestandteile': {quelle: gewicht}}")
    args = parser.parse_args()

    rezept_pfad = Path(args.rezept)
    rezept = json.loads(rezept_pfad.read_text(encoding="utf-8"))
    bestandteile = rezept["bestandteile"]
    summe = sum(bestandteile.values())
    gewichte = {q: g / summe for q, g in bestandteile.items()}

    ziel = rezept_pfad.with_suffix("")
    ziel.mkdir(parents=True, exist_ok=True)
    eingaben = {}
    for n in (1, 2, 3):
        mischung = Counter()
        for quelle, gewicht in gewichte.items():
            pfad = KORPORA / "ngramme" / quelle / f"{n}-grams.txt"
            zaehler = lies_ngramme(pfad)
            gesamt = sum(zaehler.values())
            for ngramm, anzahl in zaehler.items():
                mischung[ngramm] += gewicht * anzahl / gesamt
            eingaben[f"{quelle}/{n}-grams.txt"] = _sha256(pfad)
        with open(ziel / f"{n}-grams.txt", "w", encoding="utf-8") as f:
            for ngramm, wert in sorted(mischung.items(), key=lambda x: (-x[1], x[0])):
                anzahl = round(wert * SKALA)
                if anzahl:
                    f.write(f"{anzahl} {maskiere(ngramm)}\n")

    # Geschätzter Anteil britischer Schreibung in der Mischung: Wortpaar-Treffer je Zeichen und Quelle,
    # gewichtet mit dem Anteil der Quelle (nur Quellen mit Messung, siehe schreibweise.py).
    brit = amer = abgedeckt = 0.0
    for quelle, gewicht in gewichte.items():
        quell_meta = json.loads((KORPORA / "ngramme" / quelle / "meta.json").read_text(encoding="utf-8"))
        sw = quell_meta.get("schreibweise")
        if sw and (sw["britisch"] + sw["amerikanisch"]):
            zeichen = quell_meta["summen"]["zeichen"]
            brit += gewicht * sw["britisch"] / zeichen
            amer += gewicht * sw["amerikanisch"] / zeichen
            abgedeckt += gewicht
    schreibweise = {
        "anteil_britisch_geschaetzt": round(brit / (brit + amer), 4) if brit + amer else None,
        "gewicht_mit_messung": round(abgedeckt, 4),
    }
    meta = {
        "mischung": ziel.name,
        "beschreibung": rezept.get("beschreibung", ""),
        "erzeugt_von": {"skript": "korpora/skripte/mischen.py", "sha256": _sha256(__file__)},
        "datum": datetime.date.today().isoformat(),
        "rezept": str(rezept_pfad),
        "gewichte_normiert": gewichte,
        "schreibweise": schreibweise,
        "skala": SKALA,
        "eingaben_sha256": eingaben,
    }
    (ziel / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    anteil = schreibweise["anteil_britisch_geschaetzt"]
    zusatz = "" if anteil is None else f"; britische Schreibung geschätzt {100 * anteil:.0f} % (Gewicht mit Messung {100 * schreibweise['gewicht_mit_messung']:.0f} %)"
    print(f"{ziel}: {len(gewichte)} Quellen gemischt{zusatz}")


if __name__ == "__main__":
    main()
