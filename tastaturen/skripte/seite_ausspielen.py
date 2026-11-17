"""Spielt tastaturen/web/dist/ in das Auslieferungsverzeichnis aus (Standard: /srv/keyboard-test/site).

Das Verzeichnis gehört dem Benutzer decaswift; der nginx-Container des Wunschzettels liefert es unter
https://wunschzettel.familie-gasch.net/keyboard-test/ aus (Ansible-Rolle wunschzettel, siehe tastaturen/web/ausspielen.md).
Kein root nötig.

Reihenfolge, damit Besucher nie eine halbe Fassung sehen: erst alle neuen Dateien außer index.html, dann index.html
(verweist auf die neuen Index-Dateien), zuletzt veraltete Dateien löschen.

Aufruf: python3 tastaturen/skripte/seite_ausspielen.py [Zielverzeichnis] [--ohne-bauen]
"""

import filecmp
import os
import shutil
import subprocess
import sys
from pathlib import Path

ORDNER = Path(__file__).resolve().parent.parent
DIST = ORDNER / "web" / "dist"
AUSLASSEN = {".png"}            # Bildschirmfotos aus Tests


def dateien(wurzel):
    return {p.relative_to(wurzel) for p in wurzel.rglob("*") if p.is_file() and p.suffix not in AUSLASSEN}


def kopieren(rel, ziel):
    quelle, dest = DIST / rel, ziel / rel
    if dest.exists() and filecmp.cmp(quelle, dest, shallow=False):
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    shutil.copy2(quelle, tmp)
    os.chmod(tmp, 0o644)
    os.replace(tmp, dest)          # atomar je Datei
    return True


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ziel = Path(args[0] if args else "/srv/keyboard-test/site")
    if not ziel.is_dir() or not os.access(ziel, os.W_OK):
        sys.exit(f"{ziel} fehlt oder ist nicht beschreibbar (Ansible-Rolle wunschzettel angewendet?)")
    if "--ohne-bauen" not in sys.argv:
        subprocess.run([sys.executable, str(ORDNER / "skripte" / "seite_bauen.py"), "--noindex"], check=True)
    neu = dateien(DIST)
    zuerst = sorted(r for r in neu if not r.name.startswith("index.html"))
    geaendert = sum(kopieren(r, ziel) for r in zuerst)
    geaendert += sum(kopieren(r, ziel) for r in sorted(neu) if r.name.startswith("index.html"))
    alt = dateien(ziel) - neu
    for r in alt:
        (ziel / r).unlink()
    for d in sorted((p for p in ziel.rglob("*") if p.is_dir()), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()
    print(f"{ziel}: {geaendert} Dateien neu oder geändert, {len(alt)} gelöscht, {len(neu)} insgesamt")


if __name__ == "__main__":
    main()
