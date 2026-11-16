"""Trägt neue Original-Dateien ins Manifest ein: lädt sie einmalig, berechnet SHA-256 und Größe.

Das ist der Weg, eine neue Quelle aufzunehmen. Danach sind die Dateien an ihrem Pfad unter
korpora/<sprache>/original/ vorhanden und im Manifest (quellen.json) mit Prüfsumme geführt.

Aufruf (aus dem Repo-Wurzelverzeichnis):
    python3 korpora/skripte/manifest_eintragen.py englisch antrag.json [--parallel 3]

antrag.json ist eine Liste von Einträgen:
    {"pfad": "leipzig/x.tar.gz", "url": "https://...", "beschreibung": "...", "genutzt_von": ["en-quelle"]}
Optional: "lizenz", "commit", "repo" (werden ins Manifest übernommen). Bei .tar.gz wird zusätzlich die Prüfsumme
des entpackten Inhalts als "sha256_inhalt" gespeichert.

Bereits eingetragene Pfade werden übersprungen. Quellen-Versionen sollten in der URL festgenagelt sein
(z. B. Commit-Hash statt "main"), damit der Download später dieselbe Datei liefert.
Danach: beispieldaten.py --in-index (Dummys in den Git-Index) und den Leser in quellen.py ergänzen.
"""

import argparse
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import herunterladen  # noqa: E402

sperre = threading.Lock()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sprache")
    parser.add_argument("antrag")
    parser.add_argument("--parallel", type=int, default=3)
    args = parser.parse_args()

    manifest_pfad = herunterladen.KORPORA / args.sprache / "quellen.json"
    if manifest_pfad.exists():
        manifest = json.loads(manifest_pfad.read_text(encoding="utf-8"))
    else:
        manifest = {"sprache": args.sprache, "verzeichnis": f"korpora/{args.sprache}/original", "dateien": []}
    wurzel = herunterladen.REPO / manifest["verzeichnis"]
    vorhanden = {d["pfad"] for d in manifest["dateien"]}
    antraege = [a for a in json.loads(Path(args.antrag).read_text(encoding="utf-8")) if a["pfad"] not in vorhanden]
    print(f"{len(antraege)} neue Dateien", flush=True)

    def bearbeite(a):
        ziel = wurzel / a["pfad"]
        teil = ziel.with_name(ziel.name + ".teil")
        herunterladen.lade_teil(f"{args.sprache}/{a['pfad']}", a["url"], teil)
        sha = herunterladen.sha256_von(teil)
        os.replace(teil, ziel)
        eintrag = {"pfad": a["pfad"], "url": a["url"], "sha256": sha, "bytes": ziel.stat().st_size,
                   "beschreibung": a["beschreibung"], "genutzt_von": a["genutzt_von"]}
        if ziel.name.endswith(".tar.gz"):
            eintrag["sha256_inhalt"] = herunterladen.sha256_entpackt(ziel)
        for zusatz in ("lizenz", "commit", "repo"):
            if zusatz in a:
                eintrag[zusatz] = a[zusatz]
        with sperre:
            manifest["dateien"].append(eintrag)
            manifest_pfad.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        herunterladen.vor_git_verbergen(ziel)
        return f"eingetragen: {a['pfad']} ({eintrag['bytes'] / 1e6:,.0f} MB)"

    fehler = 0
    with ThreadPoolExecutor(args.parallel) as pool:
        for a, erg in zip(antraege, [pool.submit(bearbeite, a) for a in antraege]):
            try:
                print(erg.result(), flush=True)
            except Exception as ex:  # noqa: BLE001
                fehler += 1
                print(f"FEHLER {a['pfad']}: {ex}", flush=True)
    sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main()
