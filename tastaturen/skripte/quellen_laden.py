"""Lädt alle Quellen der Tastatur-Datenbank mit dem Stand aus tastaturen/quellen.json.

Aufruf (aus dem Repo-Wurzelverzeichnis):
    python3 tastaturen/skripte/quellen_laden.py            # alles laden bzw. auf den Stand bringen
    python3 tastaturen/skripte/quellen_laden.py qmk zmk    # nur diese Quellen

Ziel: ~/keyboard/tastatur-quellen/<id>/ (außerhalb des Repos; änderbar mit TASTATUR_QUELLEN).
Git-Quellen werden ohne Blobs geklont und nur mit den Pfaden aus "sparse" ausgecheckt. golem.hu wird höflich
geladen (eine Anfrage je Sekunde); vorhandene Seiten werden nicht erneut geholt.
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ZIEL = Path(os.environ.get("TASTATUR_QUELLEN", Path.home() / "keyboard" / "tastatur-quellen"))
KENNUNG = {"User-Agent": "keyboard-layout research script"}


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True)


def lade_git(name, q):
    ordner = ZIEL / name
    if not (ordner / ".git").exists():
        git("clone", "-q", "--filter=blob:none", "--no-checkout", q["url"], str(ordner))
    git("sparse-checkout", "set", "--no-cone", *q["sparse"], cwd=ordner)
    git("fetch", "-q", "--filter=blob:none", "origin", q["commit"], cwd=ordner)
    git("checkout", "-q", "--detach", q["commit"], cwd=ordner)
    print(f"{name}: {q['commit'][:12]}")


def hole(url):
    req = urllib.request.Request(url, headers=KENNUNG)
    return urllib.request.urlopen(req, timeout=30).read()


def lade_golem(name, q):
    ordner = ZIEL / name
    (ordner / "board").mkdir(parents=True, exist_ok=True)
    uebersicht = ordner / "boards.html"
    if not uebersicht.exists():
        uebersicht.write_bytes(hole(q["url"]))
    links = sorted(set(re.findall(r'href="(board/[^"/]+\.html)"', uebersicht.read_text(encoding="utf-8"))))
    neu = 0
    for link in links:
        datei = ordner / link
        if datei.exists() and datei.stat().st_size > 1000:
            continue
        for versuch in range(3):
            try:
                datei.write_bytes(hole("https://golem.hu/" + link))
                neu += 1
                break
            except OSError:
                time.sleep(5)
        time.sleep(1)
    print(f"{name}: {len(links)} Detailseiten, {neu} neu geladen")


def main():
    quellen = json.loads((REPO / "tastaturen" / "quellen.json").read_text(encoding="utf-8"))["quellen"]
    auswahl = sys.argv[1:] or list(quellen)
    ZIEL.mkdir(parents=True, exist_ok=True)
    for name in auswahl:
        q = quellen[name]
        {"git": lade_git, "web": lade_golem}[q["art"]](name, q)


if __name__ == "__main__":
    main()
