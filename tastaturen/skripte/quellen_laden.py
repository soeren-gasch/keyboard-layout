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
KENNUNG = {"User-Agent": "Mozilla/5.0 (compatible; keyboard-layout research script)"}


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


def lade_kbdnews(name, q):
    """Alle Artikel über ihre Nummer (https://kbd.news/x-<id>.html; der Namensteil ist beliebig). Die höchste Nummer
    stammt aus der neuesten Ausgabe. Seiten ohne Artikel (Titel "Keyboard Builders' Digest") werden als leer gemerkt.
    Vorhandene Dateien bleiben; höchstens eine Anfrage je Sekunde."""
    ordner = ZIEL / name / "artikel"
    ordner.mkdir(parents=True, exist_ok=True)
    start = hole("https://kbd.news/").decode("utf-8", "replace")
    hoechste = max(int(n) for n in re.findall(r'-(\d+)\.html"', start))
    neu = leer = 0
    for nr in range(1, hoechste + 1):
        datei, leer_marke = ordner / f"{nr}.html", ordner / f"{nr}.leer"
        if (datei.exists() and datei.stat().st_size > 1000) or leer_marke.exists():
            continue
        for versuch in range(3):
            try:
                inhalt = hole(f"https://kbd.news/x-{nr}.html")
                if b"<title>Keyboard Builders' Digest" in inhalt[:5000] or b"<article" not in inhalt:
                    leer_marke.touch()
                    leer += 1
                else:
                    datei.write_bytes(inhalt)
                    neu += 1
                break
            except OSError:
                time.sleep(5)
        time.sleep(1)
    print(f"{name}: Artikel 1..{hoechste}, {neu} neu geladen, {leer} ohne Artikel")


def lade_github(name, q):
    """GitHub-Suche nach Topics (ohne Anmeldung: höchstens 10 Anfragen je Minute, je Anfrage 100 Treffer, höchstens
    1000 Treffer je Topic). Ergebnis je Topic als JSON."""
    ordner = ZIEL / name
    ordner.mkdir(parents=True, exist_ok=True)
    import urllib.error
    for thema in q["topics"]:
        if (ordner / f"{thema}.json").exists() and "--neu" not in sys.argv:
            continue
        treffer, seite = [], 1
        while True:
            url = (f"https://api.github.com/search/repositories?q=topic:{thema}&per_page=100&page={seite}"
                   "&sort=updated")
            for versuch in range(5):
                try:
                    daten = json.loads(hole(url))
                    break
                except urllib.error.HTTPError as e:
                    if e.code not in (403, 429):
                        raise
                    time.sleep(65)     # Rate-Limit der Suche ohne Anmeldung
            else:
                raise SystemExit(f"{thema}: Rate-Limit hält an")
            treffer += daten.get("items", [])
            time.sleep(7)
            if len(daten.get("items", [])) < 100 or seite >= 10:
                break
            seite += 1
        (ordner / f"{thema}.json").write_text(json.dumps({"topic": thema, "abgerufen": time.strftime("%Y-%m-%d"),
                                                          "anzahl": daten.get("total_count"), "items": treffer},
                                                         ensure_ascii=False), encoding="utf-8")
        print(f"{name}: topic {thema}: {len(treffer)} Repositories")


def lade_mediawiki(name, q):
    """Alle Seiten, die eine der Vorlagen einbinden, mit Wikitext (je Anfrage 50 Seiten, eine Anfrage je Sekunde)."""
    import urllib.parse
    ordner = ZIEL / name
    ordner.mkdir(parents=True, exist_ok=True)
    titel = []
    for vorlage in q["vorlagen"]:
        weiter = {}
        while True:
            parameter = {"action": "query", "list": "embeddedin", "eititle": vorlage, "eilimit": "500",
                         "einamespace": "0", "format": "json", **weiter}
            d = json.loads(hole(q["api"] + "?" + urllib.parse.urlencode(parameter)))
            titel += [e["title"] for e in d["query"]["embeddedin"]]
            time.sleep(1)
            if "continue" not in d:
                break
            weiter = d["continue"]
    seiten = {}
    for i in range(0, len(titel), 50):
        parameter = {"action": "query", "prop": "revisions", "rvprop": "content|ids|timestamp", "rvslots": "main",
                     "titles": "|".join(titel[i:i + 50]), "format": "json"}
        d = json.loads(hole(q["api"] + "?" + urllib.parse.urlencode(parameter)))
        for p in d["query"]["pages"].values():
            rev = (p.get("revisions") or [{}])[0]
            seiten[p["title"]] = {"pageid": p.get("pageid"), "revid": rev.get("revid"),
                                  "zeitstempel": rev.get("timestamp"),
                                  "text": ((rev.get("slots") or {}).get("main") or {}).get("*", "")}
        time.sleep(1)
    (ordner / "seiten.json").write_text(json.dumps({"abgerufen": time.strftime("%Y-%m-%d"), "seiten": seiten},
                                                  ensure_ascii=False), encoding="utf-8")
    print(f"{name}: {len(seiten)} Seiten")


def lade_arcticshift(name, q):
    """Alle Posts eines Subreddits aus dem Reddit-Archiv Arctic Shift, rückwärts nach Zeit, 100 je Anfrage, eine Anfrage
    je Sekunde. Ergebnis als JSON Lines; vorhandene Posts bleiben, neuere werden ergänzt."""
    import urllib.parse
    ordner = ZIEL / name
    ordner.mkdir(parents=True, exist_ok=True)
    for sub in q["subreddits"]:
        datei = ordner / f"{sub}.jsonl"
        bekannt, vor = set(), None
        if datei.exists():
            alt = [json.loads(z) for z in datei.read_text(encoding="utf-8").splitlines() if z]
            bekannt = {p["id"] for p in alt}
            if alt and "--neueste" not in sys.argv:
                vor = min(int(p["created_utc"]) for p in alt)   # dort weitermachen, wo der letzte Abruf endete
        neu = 0
        with open(datei, "a", encoding="utf-8") as aus:
            while True:
                parameter = {"subreddit": sub, "limit": "100", "sort": "desc", "fields": q["felder"]}
                if vor:
                    parameter["before"] = str(vor)
                import urllib.error
                for versuch in range(6):
                    try:
                        d = json.loads(hole(q["api"] + "?" + urllib.parse.urlencode(parameter)))
                        break
                    except urllib.error.HTTPError as e:
                        if e.code not in (422, 429, 500, 502, 503, 504):
                            raise
                        time.sleep(10 * (versuch + 1))   # Zeitüberschreitung beim Archiv: langsamer werden
                else:
                    raise SystemExit(f"{sub}: Archiv antwortet nicht, Abbruch bei {vor}")
                posts = d.get("data") or []
                if not posts:
                    break
                for p in posts:
                    if p["id"] not in bekannt:
                        aus.write(json.dumps(p, ensure_ascii=False) + "\n")
                        bekannt.add(p["id"])
                        neu += 1
                vor = min(int(p["created_utc"]) for p in posts)
                time.sleep(2)
        print(f"{name}: r/{sub}: {len(bekannt)} Posts, {neu} neu")


def lade_shopify(name, q):
    """Öffentliche Produktlisten von Shopify-Shops (/products.json, 250 je Seite, eine Anfrage alle 2 Sekunden).
    Je Shop eine Datei mit Abfragezeitpunkt (UTC, sekundengenau)."""
    import urllib.error
    ordner = ZIEL / name
    ordner.mkdir(parents=True, exist_ok=True)
    for shop in q["shops"]:
        datei = ordner / f"{shop}.json"
        if datei.exists() and "--neu" not in sys.argv:
            continue
        produkte, seite = [], 1
        zeitpunkt = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        while True:
            try:
                d = json.loads(hole(f"https://{shop}/products.json?limit=250&page={seite}"))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(60)
                    continue
                print(f"{name}: {shop}: HTTP {e.code}, abgebrochen")
                break
            teil = d.get("products") or []
            produkte += teil
            time.sleep(2)
            if len(teil) < 250 or seite >= 80:
                break
            seite += 1
        datei.write_text(json.dumps({"shop": shop, "abgerufen": zeitpunkt, "produkte": produkte}, ensure_ascii=False),
                         encoding="utf-8")
        print(f"{name}: {shop}: {len(produkte)} Produkte")


def main():
    quellen = json.loads((REPO / "tastaturen" / "quellen.json").read_text(encoding="utf-8"))["quellen"]
    auswahl = [a for a in sys.argv[1:] if not a.startswith("--")] or list(quellen)
    ZIEL.mkdir(parents=True, exist_ok=True)
    for name in auswahl:
        q = quellen[name]
        {"git": lade_git, "web": lade_golem, "kbdnews": lade_kbdnews, "github": lade_github, "mediawiki": lade_mediawiki, "arcticshift": lade_arcticshift, "shopify": lade_shopify,
         "datei": lambda *a: None}[q["art"]](name, q)


if __name__ == "__main__":
    main()
