"""Sammelt Bild-URLs je Datensatz (nur Adressen, keine Bilder) für die interne Prüfseite.

Ausgang: ~/keyboard/tastatur-quellen/bilder.json  {"<quelle>:<quell_id>": [url, …], "_stand": {...}}

Die Bilder gehören den jeweiligen Urhebern. Sie werden nur verlinkt (Hotlink) und nicht veröffentlicht; die öffentliche
Seite zeigt keine Fotos.

Quellen:
- QMK: erstes Bild in readme.md (Ordnerkette von unten nach oben)
- Shops (Shopify): erstes Produktbild
- Keebfolio, Aposymbiont, YAL: Bilddatei aus dem Repository (raw.githubusercontent.com am gepinnten Commit)
- golem.hu: Foto der Detailseite; KBD.news: og:image des Artikels
- eigene Recherche: og:image der gespeicherten Herstellerseite (~/manuell-html)
- Deskthority: Seitenbild über die MediaWiki-API (prop=pageimages), nur mit --deskthority; das Wiki sperrt das
  Einbinden im Browser (403), die Prüfseite verlinkt stattdessen die Wiki-Seite

Aufruf: python3 tastaturen/skripte/bilder_sammeln.py [--deskthority | --deskthority-neu]
"""

import csv
import datetime
import html
import json
import re
import sqlite3
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from basis import DB, QUELLEN  # noqa: E402

ZIEL = QUELLEN / "bilder.json"
UA = "Mozilla/5.0 (compatible; keyboard-research)"
BILD = re.compile(r"!\[[^\]]*\]\((https?://[^)\s]+)\)|<img[^>]+src=\"(https?://[^\"]+)\"", re.I)


def commit(ordner):
    return subprocess.run(["git", "-C", str(ordner), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def raw(repo, c, pfad):
    return f"https://raw.githubusercontent.com/{repo}/{c}/{urllib.parse.quote(pfad)}"


def qmk(datensaetze):
    basis, erg = QUELLEN / "qmk" / "keyboards", {}
    for qid in datensaetze:
        teile = qid.split("/")
        for i in range(len(teile), 0, -1):
            p = basis.joinpath(*teile[:i]) / "readme.md"
            if p.exists():
                urls = [a or b for a, b in BILD.findall(p.read_text(errors="replace"))]
                urls = [u for u in urls if not re.search(r"shields\.io|badge|\.svg(\?|$)", u)]
                if urls:
                    erg[qid] = urls[:2]
                break
    return erg


def shops():
    erg = {}
    for f in (QUELLEN / "shops").glob("*.json"):
        d = json.loads(f.read_text())
        for p in d.get("produkte", []):
            bilder = [i.get("src") for i in p.get("images", []) if i.get("src")]
            if bilder:
                erg[f"{f.stem}/{p['handle']}"] = bilder[:2]
    return erg


def keebfolio():
    w = QUELLEN / "keebfolio"
    c, erg = commit(w), {}
    for f in (w / "src" / "content" / "keyboards").glob("**/*.md"):
        m = re.search(r'^image:\s*"?([^"\n]+)"?', f.read_text(encoding="utf-8"), re.M)
        if m:
            pfad = (f.parent / m.group(1).strip()).resolve().relative_to(w.resolve()).as_posix()
            erg[f.relative_to(w).as_posix()] = [raw("Keycapsss/awesome-mechanical-keyboard", c, pfad)]
    return erg


def aposymbiont():
    w = QUELLEN / "aposymbiont"
    c, erg = commit(w), {}
    for datei in ("ergo.csv", "ortho.csv", "dish.csv", "traditional.csv", "other.csv"):
        with open(w / datei, encoding="utf-8") as f:
            for z in csv.DictReader(f):
                if z.get("Name") and z.get("Image"):
                    erg[f"{datei}#{z['Name']}"] = [raw("Aposymbiont/split-keyboards", c, "img/" + z["Image"])]
    return erg


def yal():
    w = QUELLEN / "yal"
    c, erg, name = commit(w), {}, None
    for zeile in (w / "docs" / "keyboards.js").read_text(encoding="utf-8").splitlines():
        m = re.match(r'\s*"name":\s*"([^"]+)"', zeile)
        if m:
            name = m.group(1)
        m = re.match(r'\s*"img":\s*"([^"]+)"', zeile)
        if m and name:
            erg.setdefault(f"docs/keyboards.js#{name}", []).append(raw("YAL-Tools/ergo-keyboards", c, "docs/img/" + m.group(1)))
    return erg


def golem():
    erg = {}
    for f in (QUELLEN / "golem" / "board").glob("*.html"):
        m = re.search(r'<img class="responsive photo"[^>]*src="([^"]+)"', f.read_text(errors="replace"))
        if m:
            src = m.group(1).replace("/800/", "/480/")
            erg[f.name] = [src if src.startswith("http") else "https://golem.hu/" + src.lstrip("/")]
    return erg


def kbdnews():
    erg = {}
    for f in (QUELLEN / "kbdnews" / "artikel").glob("*.html"):
        m = re.search(r'og:image" content="([^"]+)"', f.read_text(errors="replace"))
        if m and "kbdnews_128" not in m.group(1):
            erg[f.stem] = [m.group(1)]
    return erg


def manuell(db):
    erg = {}
    urls = {}
    for qid, url in db.execute("SELECT quell_id, url FROM datensatz WHERE quelle = 'manuell'"):
        if url:
            urls[url.rstrip("/").split("?")[0].lower()] = qid
    for f in (Path.home() / "manuell-html").glob("*.html"):
        t = f.read_text(errors="replace")
        bild = re.search(r'og:image" content="([^"]+)"', t)
        if not bild:
            continue
        for kand in re.findall(r'og:url" content="([^"]+)"|rel="canonical" href="([^"]+)"', t):
            for u in kand:
                qid = urls.get(u.rstrip("/").split("?")[0].lower()) if u else None
                if qid:
                    erg[qid] = [html.unescape(bild.group(1))]
    return erg


def deskthority(titel, neu):
    cache = QUELLEN / "deskthority" / "bilder.json"
    if cache.exists() and not neu:
        return json.loads(cache.read_text())["bilder"]
    erg, titel = {}, sorted(titel)
    for i in range(0, len(titel), 50):
        teil = "|".join(titel[i:i + 50])
        url = ("https://deskthority.net/wiki/api.php?action=query&prop=pageimages&pithumbsize=400&format=json&titles="
               + urllib.parse.quote(teil))
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
            d = json.load(r)
        rueck = {n["to"]: n["from"] for n in d["query"].get("normalized", [])}
        for p in d["query"]["pages"].values():
            if p.get("thumbnail"):
                erg[rueck.get(p["title"], p["title"])] = [p["thumbnail"]["source"]]
        time.sleep(1)
    cache.write_text(json.dumps({"abgerufen": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                                 "bilder": erg}, ensure_ascii=False))
    return erg


def main():
    db = sqlite3.connect(DB)
    ids = {}
    for q, qid in db.execute("SELECT quelle, quell_id FROM datensatz"):
        ids.setdefault(q, []).append(qid)
    teile = {"qmk": qmk(ids.get("qmk", [])), "shops": shops(), "keebfolio": keebfolio(), "aposymbiont": aposymbiont(),
             "yal": yal(), "golem": golem(), "kbdnews": kbdnews(), "manuell": manuell(db)}
    # Deskthority liefert Seitenbilder über die API, sperrt aber das Einbinden im Browser (HTTP 403, geprüft
    # 17.11.2026). Daher nur auf ausdrücklichen Wunsch (--deskthority) und nicht in der Prüfseite verwendet.
    if "--deskthority" in sys.argv or "--deskthority-neu" in sys.argv:
        teile["deskthority"] = deskthority(ids.get("deskthority", []), "--deskthority-neu" in sys.argv)
    bilder = {f"{q}:{k}": v for q, d in teile.items() for k, v in d.items() if k in set(ids.get(q, []))}
    bilder["_stand"] = {"erzeugt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                        "je_quelle": {q: sum(1 for k in bilder if k.startswith(q + ":")) for q in teile}}
    ZIEL.write_text(json.dumps(bilder, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(bilder["_stand"], ensure_ascii=False))


if __name__ == "__main__":
    main()
