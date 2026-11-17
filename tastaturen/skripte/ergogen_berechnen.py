"""Berechnet die Tastenpositionen aller gefundenen Ergogen-Konfigurationen.

Aufruf (aus dem Repo-Wurzelverzeichnis, nach ergogen_suchen.py; braucht Node.js über nvm):
    python3 tastaturen/skripte/ergogen_berechnen.py           # nur noch nicht berechnete Dateien
    python3 tastaturen/skripte/ergogen_berechnen.py --neu     # alle

Je Datei: Abschnitte outlines, cases und pcbs werden entfernt (nur die Punkte werden gebraucht). Dann läuft Ergogen
4.2.1, bei einem Fehler Ergogen 3.1.2 (beide fest installiert unter ~/keyboard/werkzeuge/ergogen4 bzw. ergogen3).
Ergebnis je Datei: ~/keyboard/tastatur-quellen/ergogen-punkte/<besitzer>__<repo>/<pfad>.json mit Version, Punkten
und Fehlern. Die Datenbank liest nur diese Ergebnisse; zum Aufbau der Datenbank wird Node.js nicht gebraucht.
"""

import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from basis import ORDNER, QUELLEN  # noqa: E402

WERKZEUGE = Path.home() / "keyboard" / "werkzeuge"
VERSIONEN = [("4.2.1", WERKZEUGE / "ergogen4"), ("3.1.2", WERKZEUGE / "ergogen3")]
ZIEL = QUELLEN / "ergogen-punkte"


def nur_punkte(text):
    """Entfernt die Abschnitte outlines, cases und pcbs auf oberster Ebene, rein textuell (Ergogen nutzt js-yaml,
    das mehr erlaubt als PyYAML). None, wenn kein Abschnitt points vorkommt."""
    if not re.search(r"(?m)^points\s*[.:]", text):
        return None
    aus, ueberspringen = [], False
    for zeile in text.splitlines():
        if re.match(r"^[A-Za-z_]", zeile):
            ueberspringen = bool(re.match(r"^(outlines|cases|pcbs)\s*[.:]", zeile))
        if not ueberspringen:
            aus.append(zeile)
    return "\n".join(aus) + "\n"


def berechne(aufgabe):
    repo, pfad = aufgabe
    quelle = QUELLEN / "ergogen" / repo.replace("/", "__") / pfad
    ziel = ZIEL / repo.replace("/", "__") / (pfad + ".json")
    konfig = nur_punkte(quelle.read_text(encoding="utf-8", errors="replace"))
    ergebnis = {"repo": repo, "pfad": pfad, "version": None, "punkte": None, "fehler": []}
    if konfig is None:
        ergebnis["fehler"].append("kein Abschnitt points")
    else:
        for version, ordner in VERSIONEN:
            with tempfile.TemporaryDirectory() as tmp:
                eingabe = Path(tmp) / "config.yaml"
                eingabe.write_text(konfig, encoding="utf-8")
                lauf = subprocess.run(["bash", "-lc", f"npx --no-install ergogen '{eingabe}' -d -o '{tmp}/out'"],
                                      cwd=ordner, capture_output=True, text=True, timeout=180)
                punkte = Path(tmp) / "out" / "points" / "points.yaml"
                if lauf.returncode == 0 and punkte.exists():
                    ergebnis["version"] = version
                    ergebnis["punkte"] = yaml.safe_load(punkte.read_text(encoding="utf-8"))
                    break
                fehlertext = [z for z in (lauf.stdout + lauf.stderr).splitlines() if z.startswith("Error")]
                ergebnis["fehler"].append(f"{version}: {(fehlertext or ['unbekannter Fehler'])[0][:200]}")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps(ergebnis, ensure_ascii=False, default=str), encoding="utf-8")
    return repo, pfad, ergebnis["version"]


def main():
    manifest = json.loads((ORDNER / "ergogen.json").read_text(encoding="utf-8"))["repositories"]
    aufgaben = [(r, p) for r, e in sorted(manifest.items()) for p in e.get("ergogen", [])]
    if "--neu" not in sys.argv:
        aufgaben = [(r, p) for r, p in aufgaben
                    if not (ZIEL / r.replace("/", "__") / (p + ".json")).exists()]
    print(f"{len(aufgaben)} Ergogen-Dateien zu berechnen")
    ok = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        for repo, pfad, version in pool.map(berechne, aufgaben):
            ok += version is not None
    print(f"fertig: {ok} von {len(aufgaben)} berechnet")


if __name__ == "__main__":
    main()
