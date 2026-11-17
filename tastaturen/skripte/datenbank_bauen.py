"""Baut die Tastatur-Datenbank aus den geladenen Quellen.

Aufruf (aus dem Repo-Wurzelverzeichnis), nachdem `tastaturen/skripte/quellen_laden.py` gelaufen ist:
    python3 tastaturen/skripte/datenbank_bauen.py

Eingang:  ~/keyboard/tastatur-quellen/<quelle>/ (Stand je Quelle in tastaturen/quellen.json)
Ausgang:  tastaturen/tastaturen.sqlite (Schema siehe tastaturen/README.md)
          tastaturen/export/*.csv   (Übersichten, diff-bar)

Je Quelle ein Leser; alle schreiben in dieselben Tabellen. Abgeleitete Werte (Tastenzahl, geteilt, Hälften) werden
aus den Tastenpositionen berechnet und als abgeleitet markiert; Angaben der Quelle bleiben unverändert daneben stehen.
"""

import csv
import datetime
import glob
import html
import json
import math
import os
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
QUELLEN = Path(os.environ.get("TASTATUR_QUELLEN", Path.home() / "keyboard" / "tastatur-quellen"))
DB = REPO / "tastaturen" / "tastaturen.sqlite"
EXPORT = REPO / "tastaturen" / "export"

SCHEMA = """
CREATE TABLE meta (schluessel TEXT PRIMARY KEY, wert TEXT);
CREATE TABLE quelle (
  id TEXT PRIMARY KEY, name TEXT, url TEXT, stand TEXT, lizenz TEXT, beschreibung TEXT);
CREATE TABLE tastatur (
  id INTEGER PRIMARY KEY,
  quelle TEXT REFERENCES quelle(id),
  quell_id TEXT,              -- Schlüssel in der Quelle (Pfad, Dateiname, Zeilen-ID)
  name TEXT,
  hersteller TEXT,            -- Hersteller bzw. Entwickler laut Quelle
  url TEXT,
  familie TEXT,               -- grobe Gruppierung innerhalb der Quelle (QMK: oberster Ordner)
  geteilt INTEGER,            -- laut Quelle: 1 getrennte Hälften, 0 nein, NULL unbekannt
  drahtlos INTEGER,
  tasten_min INTEGER,         -- laut Quelle
  tasten_max INTEGER,
  versatz TEXT,               -- laut Quelle: columnar, row, ortho, ...
  verfuegbarkeit TEXT,        -- laut Quelle: open source, prebuilt, kit, prototype, ...
  open_source INTEGER,
  jahr INTEGER,
  firmware TEXT,              -- qmk, zmk, ...
  prozessor TEXT,
  schalter TEXT,              -- mx, choc v1, choc v2, ...
  merkmale TEXT,              -- JSON: weitere Angaben der Quelle
  UNIQUE (quelle, quell_id));
CREATE TABLE layout (
  id INTEGER PRIMARY KEY,
  tastatur_id INTEGER REFERENCES tastatur(id),
  name TEXT,
  tasten INTEGER,             -- abgeleitet: Anzahl Tasten
  geteilt_geometrisch INTEGER,-- abgeleitet: deutliche Lücke in x, beide Seiten mit ähnlich vielen Tasten
  tasten_links INTEGER,       -- abgeleitet, nur wenn geteilt_geometrisch
  tasten_rechts INTEGER,
  breite REAL, hoehe REAL,    -- abgeleitet: Ausdehnung in Tasten-Einheiten (1u = 19,05 mm bei MX)
  rotiert INTEGER,            -- abgeleitet: Anzahl Tasten mit Drehung
  raster_links TEXT,          -- abgeleitet (Heuristik), nur bei geteilt_geometrisch: Reihen x Spalten + Daumen, z. B. 3x5+2
  raster_rechts TEXT,
  daumen_links INTEGER, daumen_rechts INTEGER,
  raster_quelle TEXT,         -- "name" (aus dem Layout-Namen, z. B. LAYOUT_split_3x5_2) oder "heuristik"
  signatur TEXT);             -- abgeleitet: Fingerabdruck der Geometrie (gerundete Positionen) zum Finden von Dubletten
CREATE TABLE taste (
  layout_id INTEGER REFERENCES layout(id),
  idx INTEGER,                -- Reihenfolge wie in der Quelle
  x REAL, y REAL, w REAL, h REAL,   -- Tasten-Einheiten, x/y = linke obere Ecke vor Drehung (KLE-Konvention)
  r REAL, rx REAL, ry REAL,          -- Drehung in Grad um (rx, ry)
  cx REAL, cy REAL,                  -- abgeleitet: Mittelpunkt nach Drehung
  matrix_zeile INTEGER, matrix_spalte INTEGER,
  bezeichnung TEXT,
  PRIMARY KEY (layout_id, idx));
CREATE TABLE verweis (          -- dieselbe physische Tastatur in verschiedenen Quellen (Kandidaten)
  tastatur_a INTEGER REFERENCES tastatur(id),
  tastatur_b INTEGER REFERENCES tastatur(id),
  methode TEXT,
  PRIMARY KEY (tastatur_a, tastatur_b));
CREATE INDEX layout_tastatur ON layout(tastatur_id);
CREATE INDEX layout_tasten ON layout(tasten);
CREATE INDEX tastatur_name ON tastatur(name);
"""


# ----------------------------------------------------------------------------- Hilfen
def json_tolerant(text):
    """QMK-Dateien sind teils hjson-artig: Kommentare, \\' in Strings, fehlende oder überzählige Kommata."""
    aus, i, n, in_str = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            if c == "\\" and i + 1 < n:
                aus.append("'" if text[i + 1] == "'" else text[i:i + 2])
                i += 2
                continue
            if c == '"':
                in_str = False
            aus.append(c)
        elif c == '"':
            in_str = True
            aus.append(c)
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
            continue
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        else:
            aus.append(c)
        i += 1
    text = "".join(aus)
    text = re.sub(r",(\s*[}\]])", r"\1", text)                      # überzählige Kommata
    text = re.sub(r'([}\]"]|\d|true|false|null)(\s*\n\s*)(["{\[])', r"\1,\2\3", text)  # fehlende Kommata
    return json.loads(text)


def tief_mischen(a, b):
    erg = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(erg.get(k), dict):
            erg[k] = tief_mischen(erg[k], v)
        else:
            erg[k] = v
    return erg


def mittelpunkt(t):
    cx, cy = t["x"] + t["w"] / 2, t["y"] + t["h"] / 2
    if t["r"]:
        a = math.radians(t["r"])
        dx, dy = cx - t["rx"], cy - t["ry"]
        cx, cy = t["rx"] + dx * math.cos(a) - dy * math.sin(a), t["ry"] + dx * math.sin(a) + dy * math.cos(a)
    return cx, cy


def _spalten(tasten):
    """Gruppiert Tasten nach x-Mittelpunkt: neue Spalte bei einem Sprung von mehr als 0,6 Tasten."""
    spalten, letzte = [], None
    for t in sorted(tasten, key=lambda t: t["cx"]):
        if letzte is None or t["cx"] - letzte > 0.6:
            spalten.append([])
        spalten[-1].append(t)
        letzte = t["cx"]
    return spalten


def raster(haelfte):
    """Heuristik für eine Hälfte: Daumentasten liegen mehr als 0,6 Tasten unter der typischen untersten Fingerreihe
    oder sind gedreht und tief. Ergebnis wie "3x5+2D": Reihen x volle Fingerspalten, +/- Zusatztasten, Daumen."""
    if len(haelfte) < 4:
        return None, None
    unten = sorted(max(k["cy"] for k in sp) for sp in _spalten(haelfte) if len(sp) >= 3)
    if not unten:
        return None, None
    grenze = unten[len(unten) // 2] + 0.6
    daumen = [t for t in haelfte if t["cy"] > grenze or (abs(t["r"]) >= 5 and t["cy"] > grenze - 0.8)]
    finger = [t for t in haelfte if t not in daumen]
    hoehen = [len(sp) for sp in _spalten(finger) if len(sp) >= 2]
    if not hoehen:
        return None, len(daumen)
    reihen = max(sorted(set(hoehen)), key=hoehen.count)
    voll = sum(1 for h in hoehen if h >= reihen)
    rest = len(finger) - reihen * voll
    return f"{reihen}x{voll}" + (f"{rest:+d}" if rest else "") + f"+{len(daumen)}D", len(daumen)


def ableiten(tasten):
    """Abgeleitete Kennzahlen eines Layouts aus den Tastenpositionen."""
    for t in tasten:
        t["cx"], t["cy"] = mittelpunkt(t)
    n = len(tasten)
    if not n:
        return {"tasten": 0}
    xs = sorted(t["cx"] for t in tasten)
    ys = [t["cy"] for t in tasten]
    geteilt, links, rechts = 0, None, None
    # größte Lücke zwischen benachbarten Mittelpunkten in x
    luecken = [(xs[i + 1] - xs[i], i) for i in range(n - 1)]
    rl = rr = dl = dr = None
    if luecken:
        g, i = max(luecken)
        l, r = i + 1, n - i - 1
        if g >= 1.25 and min(l, r) >= 0.4 * n:
            geteilt, links, rechts = 1, l, r
            schnitt = (xs[i] + xs[i + 1]) / 2
            rl, dl = raster([t for t in tasten if t["cx"] < schnitt])
            rr, dr = raster([t for t in tasten if t["cx"] >= schnitt])
    sig = ";".join(f"{round(t['cx'] * 4) / 4:g},{round(t['cy'] * 4) / 4:g}" for t in
                   sorted(tasten, key=lambda t: (round(t["cy"] * 4), round(t["cx"] * 4))))
    xmin = min(min(t["cx"] for t in tasten), 0)
    return {"tasten": n, "geteilt_geometrisch": geteilt, "tasten_links": links, "tasten_rechts": rechts,
            "breite": round(max(xs) - min(xs) + 1, 3), "hoehe": round(max(ys) - min(ys) + 1, 3),
            "rotiert": sum(1 for t in tasten if t["r"]), "signatur": sig,
            "raster_links": rl, "raster_rechts": rr, "daumen_links": dl, "daumen_rechts": dr}


class Schreiber:
    def __init__(self, db):
        self.db = db

    def quelle(self, **q):
        self.db.execute("INSERT INTO quelle VALUES (:id,:name,:url,:stand,:lizenz,:beschreibung)", q)

    def tastatur(self, **t):
        spalten = ["quelle", "quell_id", "name", "hersteller", "url", "familie", "geteilt", "drahtlos", "tasten_min",
                   "tasten_max", "versatz", "verfuegbarkeit", "open_source", "jahr", "firmware", "prozessor",
                   "schalter", "merkmale"]
        werte = [t.get(s) for s in spalten]
        if isinstance(werte[-1], (dict, list)):
            werte[-1] = json.dumps(werte[-1], ensure_ascii=False, sort_keys=True)
        cur = self.db.execute(f"INSERT INTO tastatur ({','.join(spalten)}) VALUES ({','.join('?' * len(spalten))})",
                              werte)
        return cur.lastrowid

    def layout(self, tastatur_id, name, tasten):
        a = ableiten(tasten)
        m = re.search(r"split_(\d+)x(\d+)_(\d+)", name or "")
        if m and a.get("geteilt_geometrisch"):
            r, c, d = m.groups()
            a["raster_links"] = a["raster_rechts"] = f"{r}x{c}+{d}D"
            a["daumen_links"] = a["daumen_rechts"] = int(d)
            a["raster_quelle"] = "name"
        elif a.get("raster_links"):
            a["raster_quelle"] = "heuristik"
        cur = self.db.execute(
            "INSERT INTO layout (tastatur_id,name,tasten,geteilt_geometrisch,tasten_links,tasten_rechts,breite,hoehe,"
            "rotiert,raster_links,raster_rechts,daumen_links,daumen_rechts,raster_quelle,signatur) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tastatur_id, name, a["tasten"], a.get("geteilt_geometrisch"), a.get("tasten_links"),
             a.get("tasten_rechts"), a.get("breite"), a.get("hoehe"), a.get("rotiert"), a.get("raster_links"),
             a.get("raster_rechts"), a.get("daumen_links"), a.get("daumen_rechts"), a.get("raster_quelle"),
             a.get("signatur")))
        lid = cur.lastrowid
        self.db.executemany(
            "INSERT INTO taste VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(lid, i, t["x"], t["y"], t["w"], t["h"], t["r"], t["rx"], t["ry"], round(t["cx"], 4),
              round(t["cy"], 4), t.get("mz"), t.get("ms"), t.get("label")) for i, t in enumerate(tasten)])
        return lid


def git_stand(pfad):
    kopf = (pfad / ".git" / "HEAD")
    if not kopf.exists():
        return None
    import subprocess
    return subprocess.run(["git", "-C", str(pfad), "log", "-1", "--format=%H %cs"], capture_output=True,
                          text=True).stdout.strip()


# ----------------------------------------------------------------------------- QMK
def lies_qmk(s):
    basis = QUELLEN / "qmk" / "keyboards"
    s.quelle(id="qmk", name="QMK Firmware (keyboards/)", url="https://github.com/qmk/qmk_firmware",
             stand=git_stand(QUELLEN / "qmk"), lizenz="GPL-2.0-or-later (Repository); Tastatur-Metadaten",
             beschreibung="Data-driven Tastatur-Definitionen (keyboard.json, geerbte info.json) mit Tastenpositionen "
                          "je Layout-Makro")
    return _lies_qmk_baum(s, "qmk", basis, sorted(p.parent for p in basis.glob("**/keyboard.json")))


def lies_vial(s):
    """Nur Tastaturen, die im QMK-Stand fehlen (Vial ist ein QMK-Fork mit älterer Ordnerstruktur)."""
    basis = QUELLEN / "vial" / "keyboards"
    qmk = QUELLEN / "qmk" / "keyboards"
    s.quelle(id="vial", name="Vial (vial-qmk, nur Tastaturen ohne QMK-Gegenstück)",
             url="https://github.com/vial-kb/vial-qmk", stand=git_stand(QUELLEN / "vial"),
             lizenz="GPL-2.0-or-later (Repository); Tastatur-Metadaten",
             beschreibung="QMK-Fork; übernommen werden nur Ordner, die es im QMK-Stand nicht gibt")
    ziele = []
    for p in sorted(set(basis.glob("**/keyboard.json")) | set(basis.glob("**/info.json"))):
        ordner = p.parent
        rel = ordner.relative_to(basis)
        if (qmk / rel).exists():
            continue
        # nur Blätter: Ordner ohne Unterordner mit eigener Definition
        if any(q.parent != ordner for q in ordner.glob("*/**/info.json")) or \
                any(q.parent != ordner for q in ordner.glob("*/**/keyboard.json")):
            continue
        ziele.append(ordner)
    return _lies_qmk_baum(s, "vial", basis, sorted(set(ziele)))


def _lies_qmk_baum(s, quelle, basis, ziele):
    fehler = []
    cache = {}

    def lade(p):
        if p not in cache:
            try:
                cache[p] = json_tolerant(p.read_text(encoding="utf-8-sig"))
            except Exception as e:  # noqa: BLE001
                fehler.append((str(p.relative_to(basis)), str(e)[:80]))
                cache[p] = {}
        return cache[p]

    anzahl = 0
    for ordner in ziele:
        rel = ordner.relative_to(basis)
        daten = {}
        for i in range(1, len(rel.parts) + 1):
            info = basis.joinpath(*rel.parts[:i]) / "info.json"
            if info.exists():
                daten = tief_mischen(daten, lade(info))
        if (ordner / "keyboard.json").exists():
            daten = tief_mischen(daten, lade(ordner / "keyboard.json"))
        layouts = daten.get("layouts") or {}
        merkmale = {k: daten[k] for k in ("community_layouts", "layout_aliases", "features") if k in daten}
        if "split" in daten and isinstance(daten["split"], dict):
            merkmale["split_transport"] = (daten["split"].get("serial") or {}).get("driver")
        tid = s.tastatur(
            quelle=quelle, quell_id=str(rel), name=daten.get("keyboard_name") or rel.parts[-1],
            hersteller=daten.get("manufacturer"), url=daten.get("url") or None, familie=rel.parts[0],
            geteilt=1 if (daten.get("split") or {}).get("enabled") else 0, firmware=quelle,
            prozessor=daten.get("processor"), merkmale=merkmale)
        for name, l in layouts.items():
            tasten = []
            for t in (l.get("layout") or []):
                if not isinstance(t, dict):
                    continue
                m = t.get("matrix") or [None, None]
                tasten.append({"x": float(t.get("x", 0)), "y": float(t.get("y", 0)), "w": float(t.get("w", 1)),
                               "h": float(t.get("h", 1)), "r": float(t.get("r", 0)), "rx": float(t.get("rx", 0)),
                               "ry": float(t.get("ry", 0)), "mz": m[0], "ms": m[1], "label": t.get("label")})
            if tasten:
                s.layout(tid, name, tasten)
        anzahl += 1
    return anzahl, fehler


# ----------------------------------------------------------------------------- ZMK
_ATTR = re.compile(r"<&key_physical_attrs\s+([^>]*)>")
_LAYOUT_NODE = re.compile(r"(\w+)\s*:\s*\w+\s*\{[^{}]*?compatible\s*=\s*\"zmk,physical-layout\"(.*?)\};", re.S)


def _zmk_zahl(z):
    return float(z.strip("()").replace(" ", ""))


def zmk_layouts_in(text):
    erg = {}
    for m in _LAYOUT_NODE.finditer(text):
        label, rumpf = m.group(1), m.group(2)
        anzeige = re.search(r"display-name\s*=\s*\"([^\"]*)\"", rumpf)
        tasten = []
        for a in _ATTR.finditer(rumpf):
            teile = re.findall(r"\(\s*-?\s*\d+\s*\)|-?\d+", a.group(1))
            if len(teile) < 7:
                continue
            w, h, x, y, rot, rx, ry = (_zmk_zahl(t) for t in teile[:7])
            tasten.append({"x": x / 100, "y": y / 100, "w": w / 100, "h": h / 100, "r": rot / 100,
                           "rx": rx / 100, "ry": ry / 100})
        if tasten:
            erg[label] = (anzeige.group(1) if anzeige else label, tasten)
    return erg


def lies_zmk(s):
    import yaml
    app = QUELLEN / "zmk" / "app"
    s.quelle(id="zmk", name="ZMK Firmware (app/boards)", url="https://github.com/zmkfirmware/zmk",
             stand=git_stand(QUELLEN / "zmk"), lizenz="MIT",
             beschreibung="Boards und Shields mit Metadaten (*.zmk.yml) und physischen Layouts (zmk,physical-layout)")
    # alle physischen Layouts im Baum, nach Label
    alle = {}
    for f in list(app.glob("dts/layouts/**/*.dtsi")) + list(app.glob("boards/**/*.dtsi")) + \
            list(app.glob("boards/**/*.overlay")) + list(app.glob("boards/**/*.dts")):
        for label, wert in zmk_layouts_in(f.read_text(encoding="utf-8", errors="replace")).items():
            alle.setdefault(label, wert)
    anzahl = 0
    for yml in sorted(app.glob("boards/**/*.zmk.yml")):
        meta = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
        if meta.get("type") not in ("shield", "board"):
            continue
        ordner = yml.parent
        # Layouts: im eigenen Ordner definiert oder per #include aus dts/layouts eingebunden
        labels = []
        for f in sorted(list(ordner.glob("*.dtsi")) + list(ordner.glob("*.overlay")) + list(ordner.glob("*.dts"))):
            text = f.read_text(encoding="utf-8", errors="replace")
            labels += list(zmk_layouts_in(text))
            for inc in re.findall(r"#include\s*<(layouts/[^>]+)>", text):
                p = app / "dts" / inc
                if p.exists():
                    labels += list(zmk_layouts_in(p.read_text(encoding="utf-8", errors="replace")))
        labels = list(dict.fromkeys(labels))
        features = meta.get("features") or []
        tid = s.tastatur(
            quelle="zmk", quell_id=str(yml.relative_to(app)), name=meta.get("name") or meta.get("id"),
            url=meta.get("url"), familie=meta.get("id"),
            geteilt=1 if meta.get("siblings") else None, drahtlos=1 if meta.get("type") == "board" else None,
            firmware="zmk",
            merkmale={"typ": meta.get("type"), "features": features, "requires": meta.get("requires"),
                      "arch": meta.get("arch")})
        for label in labels:
            if label in alle:
                s.layout(tid, alle[label][0], [dict(t) for t in alle[label][1]])
        anzahl += 1
    return anzahl, []


# ----------------------------------------------------------------------------- splitKbCompare
def lies_splitkbcompare(s):
    p = QUELLEN / "splitkbcompare"
    s.quelle(id="splitkbcompare", name="splitKbCompare (John Helveston)",
             url="https://github.com/jhelvy/splitKbCompare", stand=git_stand(p), lizenz="MIT",
             beschreibung="Kuratierte Tabelle von Split-Tastaturen mit Tastenzahl, Versatz, Bauart, Bezugsquellen")
    anzahl = 0
    with open(p / "keyboards.csv", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            if z.get("include") == "0":
                continue

            def b(k):
                v = z.get(k)
                return None if v in (None, "", "NA") else int(v)

            schalter = ", ".join(n for n, k in (("mx", "mxCompatible"), ("choc v1", "chocV1"), ("choc v2", "chocV2"))
                                 if z.get(k) == "1") or None
            verf = ", ".join(n for n, k in (("diy", "diy"), ("prebuilt", "prebuilt")) if z.get(k) == "1") or None
            s.tastatur(
                quelle="splitkbcompare", quell_id=z["id"], name=z["name"], url=z.get("url_source") or None,
                familie=z["id"], geteilt=0 if z.get("onePiece") == "1" else 1, drahtlos=b("wireless"),
                tasten_min=b("nKeysMin"), tasten_max=b("nKeysMax"),
                versatz=(z.get("colStagger") or None) if z.get("colStagger") not in ("", "NA", "0") else
                ("row" if z.get("rowStagger") == "1" else None),
                verfuegbarkeit=verf, open_source=b("openSource"), schalter=schalter,
                merkmale={k: z[k] for k in ("hasNumRow", "hasFuncRow", "numRows", "rotaryEncoder", "mxSpacing",
                                            "chocSpacing", "url_store", "colStagger", "rowStagger")
                          if z.get(k) not in (None, "", "NA")})
            anzahl += 1
    return anzahl, []


# ----------------------------------------------------------------------------- golem.hu
def lies_golem(s):
    p = QUELLEN / "golem"
    seiten = sorted((p / "board").glob("*.html"))
    stand = datetime.date.fromtimestamp(max(f.stat().st_mtime for f in seiten)).isoformat() if seiten else None
    s.quelle(id="golem", name="golem.hu Split keyboard database (dovenyi)", url="https://golem.hu/boards/",
             stand=stand, lizenz="keine Angabe; nur Fakten und Links übernommen",
             beschreibung="Sammlung von über 450 Split- und gewinkelten Einteiler-Tastaturen, Stand der Sammlung etwa "
                          "2021")
    anzahl, fehler = 0, []
    for f in seiten:
        h = f.read_text(encoding="utf-8", errors="replace")
        felder = {}
        for th, td in re.findall(r"<tr><th>([^<]*)<td[^>]*>(.*?)(?=<tr>|</table>)", h, re.S):
            felder[th.strip()] = td.strip()
        if not felder.get("Keyboard"):
            fehler.append((f.name, "keine Datentabelle"))
            continue
        tags = re.findall(r'<a href="board/tag/[^"]*">([^<]*)</a>', h)
        links = re.findall(r'href="(https?://[^"]+)"', felder.get("Resources", "") + felder.get("More info", ""))
        tasten = re.findall(r"\d+", felder.get("Keys", ""))
        jahr = re.match(r"(\d{4})", felder.get("Published", ""))

        def janein(v):
            v = (v or "").strip().lower()
            return 1 if v == "yes" else 0 if v == "no" else None

        sep = janein(felder.get("Separate"))
        s.tastatur(
            quelle="golem", quell_id=f.name, name=html.unescape(felder["Keyboard"]),
            hersteller=html.unescape(felder.get("Developer", "")) or None, url=links[0] if links else None,
            familie=None, geteilt=sep, drahtlos=janein(felder.get("Wireless")),
            tasten_min=int(min(tasten, key=int)) if tasten else None,
            tasten_max=int(max(tasten, key=int)) if tasten else None,
            versatz=felder.get("Stagger") or None, verfuegbarkeit=felder.get("Availability") or None,
            open_source=1 if "open" in (felder.get("Availability") or "").lower() else None,
            jahr=int(jahr.group(1)) if jahr and jahr.group(1) != "0000" else None,
            merkmale={"tags": tags, "links": links, "veroeffentlicht": felder.get("Published"),
                      "seite": "https://golem.hu/board/" + f.name})
        anzahl += 1
    return anzahl, fehler


# ----------------------------------------------------------------------------- keymapdb
def lies_keymapdb(s):
    import yaml
    p = QUELLEN / "keymapdb"
    s.quelle(id="keymapdb", name="KeymapDB (precondition)", url="https://keymapdb.com/", stand=git_stand(p),
             lizenz="GPL-3.0 (Repository); nur Fakten und Links übernommen",
             beschreibung="Dokumentierte persönliche Keymaps mit Tastatur, Tastenzahl, Versatz und Keymap-Merkmalen "
                          "(Home-Row-Mods, Buchstaben auf dem Daumen, Kombos, Ebenen)")
    anzahl, fehler = 0, []
    for f in sorted((p / "src" / "posts" / "keymaps").glob("*.md")):
        text = f.read_text(encoding="utf-8")
        m = re.match(r"---\n(.*?)\n---", text, re.S)
        try:
            d = yaml.safe_load(m.group(1)) if m else None
        except yaml.YAMLError as e:
            d = None
            fehler.append((f.name, str(e)[:60]))
        if not d or not d.get("keyboard"):
            continue
        firm = d.get("firmwares") or []
        s.tastatur(
            quelle="keymapdb", quell_id=f.stem, name=str(d["keyboard"]), url=d.get("keymapUrl"),
            geteilt=1 if d.get("isSplit") is True else 0 if d.get("isSplit") is False else None,
            tasten_min=d.get("keyCount"), tasten_max=d.get("keyCount"), versatz=d.get("stagger"),
            firmware=", ".join(map(str, firm)).lower() or None,
            merkmale={k: d.get(k) for k in ("author", "baseLayouts", "hasHomeRowMods", "hasLetterOnThumb",
                                            "isComboEnabled", "isAutoShiftEnabled", "isTapDanceEnabled",
                                            "layerCount", "languages", "OS", "keymapImage", "title")})
        anzahl += 1
    return anzahl, fehler


# ----------------------------------------------------------------------------- manuelle Einträge
def lies_manuell(s):
    p = REPO / "tastaturen" / "manuell.json"
    if not p.exists():
        return 0, []
    daten = json.loads(p.read_text(encoding="utf-8"))
    s.quelle(id="manuell", name="Eigene Recherche", url=None, stand=daten.get("stand"), lizenz="CC BY 4.0",
             beschreibung="Von Hand recherchierte Tastaturen, die in keiner maschinenlesbaren Quelle stehen; jede mit "
                          "Beleg-URL")
    for t in daten["tastaturen"]:
        felder = {k: v for k, v in t.items() if k not in ("belege",)}
        merkmale = dict(felder.pop("merkmale", {}) or {})
        merkmale["belege"] = t.get("belege", [])
        felder.setdefault("quell_id", t["name"])
        s.tastatur(quelle="manuell", merkmale=merkmale, **felder)
    return len(daten["tastaturen"]), []


# ----------------------------------------------------------------------------- Verweise zwischen Quellen
def normname(n):
    n = (n or "").lower()
    n = re.sub(r"\b(keyboard|v\d+(\.\d+)?|rev\s*\d+|mk\s*\w+|mark\s*\w+|wireless|split)\b", " ", n)
    return re.sub(r"[^a-z0-9]", "", n)


def verweise(db):
    zeilen = db.execute("SELECT id, quelle, name, familie FROM tastatur").fetchall()
    nach = {}
    for tid, q, name, fam in zeilen:
        for schl in {normname(name), normname(fam)} - {""}:
            if len(schl) >= 3:
                nach.setdefault(schl, []).append((tid, q))
    paare = set()
    for schl, liste in nach.items():
        quellen = {q for _, q in liste}
        if len(quellen) < 2 or len(liste) > 60:
            continue
        for a, qa in liste:
            for b, qb in liste:
                if a < b and qa != qb:
                    paare.add((a, b))
    db.executemany("INSERT OR IGNORE INTO verweis VALUES (?,?,'name')", sorted(paare))
    return len(paare)


# ----------------------------------------------------------------------------- Export
def exportieren(db):
    EXPORT.mkdir(parents=True, exist_ok=True)
    abfragen = {
        "tastaturen.csv": """
            SELECT t.id, t.quelle, t.quell_id, t.name, t.hersteller, t.url, t.geteilt, t.drahtlos, t.tasten_min,
                   t.tasten_max, t.versatz, t.verfuegbarkeit, t.jahr, t.firmware,
                   (SELECT COUNT(*) FROM layout l WHERE l.tastatur_id = t.id) AS layouts,
                   (SELECT MIN(l.tasten) FROM layout l WHERE l.tastatur_id = t.id) AS layout_tasten_min,
                   (SELECT MAX(l.tasten) FROM layout l WHERE l.tastatur_id = t.id) AS layout_tasten_max
            FROM tastatur t ORDER BY t.quelle, t.quell_id""",
        "layouts.csv": """
            SELECT l.id, t.quelle, t.quell_id, t.name AS tastatur, l.name, l.tasten, l.geteilt_geometrisch,
                   l.tasten_links, l.tasten_rechts, l.raster_links, l.raster_rechts, l.breite, l.hoehe, l.rotiert
            FROM layout l JOIN tastatur t ON t.id = l.tastatur_id ORDER BY t.quelle, t.quell_id, l.name""",
    }
    for datei, sql in abfragen.items():
        cur = db.execute(sql)
        with open(EXPORT / datei, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow([d[0] for d in cur.description])
            w.writerows(cur)


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if DB.exists():
        DB.unlink()
    db = sqlite3.connect(DB)
    db.executescript(SCHEMA)
    s = Schreiber(db)
    bericht = {}
    for name, leser in (("qmk", lies_qmk), ("vial", lies_vial), ("zmk", lies_zmk),
                        ("splitkbcompare", lies_splitkbcompare), ("golem", lies_golem), ("keymapdb", lies_keymapdb),
                        ("manuell", lies_manuell)):
        n, fehler = leser(s)
        bericht[name] = {"tastaturen": n, "fehler": len(fehler)}
        for f in fehler[:5]:
            print(f"  {name}: übersprungen {f[0]}: {f[1]}")
        print(f"{name}: {n} Tastaturen, {len(fehler)} Fehler")
    bericht["verweise"] = verweise(db)
    db.execute("INSERT INTO meta VALUES ('erzeugt_von', 'tastaturen/skripte/datenbank_bauen.py')")
    db.execute("INSERT INTO meta VALUES ('erzeugt_am', ?)", (datetime.date.today().isoformat(),))
    db.execute("INSERT INTO meta VALUES ('bericht', ?)", (json.dumps(bericht, ensure_ascii=False),))
    db.commit()
    exportieren(db)
    for q, n, l, k in db.execute("""SELECT t.quelle, COUNT(DISTINCT t.id), COUNT(DISTINCT l.id),
                                    (SELECT COUNT(*) FROM taste ts JOIN layout l2 ON l2.id = ts.layout_id
                                     JOIN tastatur t2 ON t2.id = l2.tastatur_id WHERE t2.quelle = t.quelle)
                                    FROM tastatur t LEFT JOIN layout l ON l.tastatur_id = t.id GROUP BY t.quelle"""):
        print(f"  {q:15} {n:5} Tastaturen {l:6} Layouts {k:8} Tasten")
    print("Verweise zwischen Quellen:", bericht["verweise"])
    db.execute("VACUUM")
    db.close()
    print(f"{DB.relative_to(REPO)}: {DB.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
