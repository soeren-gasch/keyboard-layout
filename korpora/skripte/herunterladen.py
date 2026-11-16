"""Lädt die Original-Korpora herunter und prüft sie gegen das Manifest.

Im Repository liegen an den Pfaden der Originale nur kleine Dummy-Dateien mit wenigen erfundenen
Beispiel-Einträgen (siehe beispieldaten.py). Dieses Skript ersetzt sie lokal durch die vollen
Originale und sorgt dafür, dass git die Ersetzung nicht als Änderung führt (skip-worktree).

Aufruf (aus dem Repo-Wurzelverzeichnis):
    python3 korpora/skripte/herunterladen.py --status
    python3 korpora/skripte/herunterladen.py                       # alles herunterladen
    python3 korpora/skripte/herunterladen.py deutsch/leipzig       # nur Pfade, die so beginnen
    python3 korpora/skripte/herunterladen.py --status --pruefen    # Prüfsummen der vorhandenen Dateien
    python3 korpora/skripte/herunterladen.py --urls-pruefen        # URLs erreichbar, Größe wie im Manifest?
    python3 korpora/skripte/herunterladen.py --aus ~/keyboard/original-voll   # schon vorhandene Dateien einbinden

Manifeste: korpora/<sprache>/quellen.json mit Pfad, URL, SHA-256 und Größe je Datei.
Der Download wird bei Abbruch fortgesetzt; erst nach bestandener Prüfsumme ersetzt die Datei
die Dummy-Datei.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

KORPORA = Path(__file__).resolve().parent.parent
REPO = KORPORA.parent
KENNUNG = "keyboard-layout-downloader/1.0"


def lade_manifeste():
    eintraege = []
    for manifest in sorted(KORPORA.glob("*/quellen.json")):
        m = json.loads(manifest.read_text(encoding="utf-8"))
        wurzel = REPO / m["verzeichnis"]
        for d in m["dateien"]:
            eintraege.append({**d, "sprache": m["sprache"], "ziel": wurzel / d["pfad"],
                              "name": f"{m['sprache']}/{d['pfad']}"})
    return eintraege


def sha256_von(pfad):
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        for block in iter(lambda: f.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def sha256_entpackt(pfad):
    """SHA-256 des entpackten Inhalts einer .gz-Datei (robust gegen andere Kompression desselben Inhalts)."""
    import gzip

    h = hashlib.sha256()
    with gzip.open(pfad, "rb") as f:
        for block in iter(lambda: f.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def zustand(e, pruefen=False):
    """'fehlt', 'dummy' (Größe weicht ab), 'ok' (Größe passt), 'ok-geprueft' oder 'defekt'."""
    ziel = e["ziel"]
    if not ziel.exists():
        return "fehlt"
    if ziel.stat().st_size != e["bytes"]:
        return "dummy"
    if pruefen:
        return "ok-geprueft" if sha256_von(ziel) == e["sha256"] else "defekt"
    return "ok"


def git(*argumente):
    return subprocess.run(["git", "-C", str(REPO), *argumente], capture_output=True, text=True)


_git_sperre = threading.Lock()


def _git_mit_wiederholung(*argumente, versuche=8):
    """git-Aufruf, der bei gesperrtem Index (index.lock durch einen gleichzeitigen Aufruf) wiederholt wird."""
    for versuch in range(versuche):
        erg = git(*argumente)
        if erg.returncode == 0:
            return erg
        time.sleep(0.3 * (versuch + 1))
    return erg


def vor_git_verbergen(ziel):
    """Lokale Ersetzung der Dummy-Datei nicht als Änderung führen (skip-worktree bzw. .git/info/exclude).

    Läuft unter einer Sperre, weil parallele Downloads sonst den Git-Index gegenseitig blockieren."""
    rel = str(ziel.relative_to(REPO))
    with _git_sperre:
        if git("ls-files", "--error-unmatch", rel).returncode == 0:
            erg = _git_mit_wiederholung("update-index", "--skip-worktree", rel)
            if erg.returncode != 0:
                print(f"  WARNUNG: skip-worktree für {rel} nicht gesetzt: {erg.stderr.strip()}", flush=True)
        elif (REPO / ".git" / "info").is_dir():
            ausschluss = REPO / ".git" / "info" / "exclude"
            vorhanden = ausschluss.read_text().splitlines() if ausschluss.exists() else []
            if "/" + rel not in vorhanden:
                with open(ausschluss, "a") as f:
                    f.write("/" + rel + "\n")


def lade_teil(name, url, teil, groesse=None, versuche=5):
    """Lädt url nach `teil` (Abbruch wird fortgesetzt). Prüft nichts; die Datei ist danach vollständig."""
    teil.parent.mkdir(parents=True, exist_ok=True)
    for versuch in range(1, versuche + 1):
        bereits = teil.stat().st_size if teil.exists() else 0
        anfrage = urllib.request.Request(url, headers={"User-Agent": KENNUNG})
        if bereits:
            anfrage.add_header("Range", f"bytes={bereits}-")
        try:
            with urllib.request.urlopen(anfrage, timeout=60) as antwort:
                modus = "ab" if antwort.status == 206 else "wb"
                if modus == "wb":
                    bereits = 0
                letzte = time.time()
                with open(teil, modus) as f:
                    while True:
                        block = antwort.read(1 << 20)
                        if not block:
                            break
                        f.write(block)
                        bereits += len(block)
                        if time.time() - letzte > 30:
                            von = f" von {groesse / 1e6:,.0f}" if groesse else ""
                            print(f"  {name}: {bereits / 1e6:,.0f}{von} MB", flush=True)
                            letzte = time.time()
            return
        except (urllib.error.URLError, TimeoutError, ConnectionError) as fehler:
            if isinstance(fehler, urllib.error.HTTPError) and fehler.code == 416:
                return  # Datei ist schon vollständig
            print(f"  {name}: Versuch {versuch} fehlgeschlagen ({fehler}); neuer Versuch", flush=True)
            time.sleep(5 * versuch)
    raise RuntimeError(f"{name}: Download nach {versuche} Versuchen nicht möglich")


def herunterladen(e, versuche=5):
    ziel = e["ziel"]
    teil = ziel.with_name(ziel.name + ".teil")
    lade_teil(e["name"], e["url"], teil, e["bytes"], versuche)
    if teil.stat().st_size != e["bytes"] or sha256_von(teil) != e["sha256"]:
        # GitHub garantiert nicht, dass seine Archive bit-genau gleich bleiben. Ist wenigstens der entpackte
        # Inhalt unverändert, behalten wir die Datei und weisen auf die Abweichung hin.
        if e.get("sha256_inhalt") and sha256_entpackt(teil) == e["sha256_inhalt"]:
            print(f"  HINWEIS {e['name']}: Archiv-Bytes weichen vom Manifest ab, der Inhalt ist identisch. "
                  f"Für zaehlen.py bytes und sha256 im Manifest bewusst auf die neue Datei setzen.", flush=True)
        else:
            teil.unlink()
            raise RuntimeError(f"{e['name']}: Größe oder Prüfsumme stimmt nicht mit dem Manifest überein "
                               f"(Quelle geändert?). Die Datei wurde verworfen.")
    os.replace(teil, ziel)


def einbinden(e, quelle_dir, verschieben):
    quelle = Path(quelle_dir).expanduser() / e["sprache"] / e["pfad"]
    if not quelle.exists():
        return False
    if quelle.stat().st_size != e["bytes"] or sha256_von(quelle) != e["sha256"]:
        raise RuntimeError(f"{e['name']}: {quelle} stimmt nicht mit dem Manifest überein")
    e["ziel"].parent.mkdir(parents=True, exist_ok=True)
    (shutil.move if verschieben else shutil.copy2)(quelle, e["ziel"])
    return True


def bearbeite(e, args):
    z = zustand(e)
    if z in ("ok",) and not args.neu:
        if sha256_von(e["ziel"]) == e["sha256"]:
            vor_git_verbergen(e["ziel"])
            return f"vorhanden und geprüft: {e['name']}"
    if args.aus and einbinden(e, args.aus, args.verschieben):
        vor_git_verbergen(e["ziel"])
        return f"eingebunden: {e['name']}"
    herunterladen(e)
    vor_git_verbergen(e["ziel"])
    return f"heruntergeladen und geprüft: {e['name']}"


def url_pruefen(e):
    """HEAD-Anfrage: Ist die URL erreichbar und stimmt die Größe mit dem Manifest überein?"""
    anfrage = urllib.request.Request(e["url"], method="HEAD", headers={"User-Agent": KENNUNG})
    try:
        with urllib.request.urlopen(anfrage, timeout=60) as antwort:
            laenge = antwort.headers.get("Content-Length")
            if laenge is None:  # z. B. GitHub-Archive: werden erst beim Abruf erzeugt
                return f"ok (erreichbar, ohne Größenangabe): {e['name']}"
            return (f"ok {int(laenge):>13,} Bytes: {e['name']}" if int(laenge) == e["bytes"]
                    else f"GRÖSSE ABWEICHEND (Server {int(laenge):,}, Manifest {e['bytes']:,}): {e['name']}")
    except (urllib.error.URLError, TimeoutError) as fehler:
        return f"NICHT ERREICHBAR ({fehler}): {e['name']}"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("auswahl", nargs="*", help="Nur Dateien, deren Name (sprache/pfad) so beginnt")
    parser.add_argument("--status", action="store_true", help="Zustand anzeigen, nichts ändern")
    parser.add_argument("--pruefen", action="store_true", help="Mit --status: SHA-256 der vorhandenen Dateien prüfen")
    parser.add_argument("--urls-pruefen", action="store_true", help="nur prüfen, ob alle URLs erreichbar sind und die Größe stimmt")
    parser.add_argument("--aus", help="Verzeichnis mit bereits vorhandenen Originalen (gleiche Struktur <sprache>/<pfad>)")
    parser.add_argument("--verschieben", action="store_true", help="Mit --aus: Dateien verschieben statt kopieren")
    parser.add_argument("--neu", action="store_true", help="Auch vorhandene Dateien erneut laden")
    parser.add_argument("--parallel", type=int, default=3, help="gleichzeitige Downloads (Standard 3)")
    args = parser.parse_args()

    eintraege = [e for e in lade_manifeste()
                 if not args.auswahl or any(e["name"].startswith(a) for a in args.auswahl)]
    if not eintraege:
        sys.exit("Keine passende Datei im Manifest.")

    if args.urls_pruefen:
        for e in eintraege:
            print(url_pruefen(e), flush=True)
        return

    if args.status:
        for e in eintraege:
            print(f"{zustand(e, args.pruefen):12} {e['bytes'] / 1e6:9,.1f} MB  {e['name']}")
        return

    gesamt = sum(e["bytes"] for e in eintraege)
    print(f"{len(eintraege)} Dateien, zusammen {gesamt / 1e9:.1f} GB", flush=True)
    fehler = 0
    with ThreadPoolExecutor(args.parallel) as pool:
        for e, erg in zip(eintraege, [pool.submit(bearbeite, e, args) for e in eintraege]):
            try:
                print(erg.result(), flush=True)
            except Exception as ex:  # noqa: BLE001
                fehler += 1
                print(f"FEHLER {e['name']}: {ex}", flush=True)
    sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main()
