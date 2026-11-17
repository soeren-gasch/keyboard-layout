"""Gemeinsame Bausteine der Tastatur-Datenbank: Pfade, Schema, Geometrie, Schreiber mit Herkunftsnachweis."""

import json
import math
import os
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ORDNER = REPO / "tastaturen"
QUELLEN = Path(os.environ.get("TASTATUR_QUELLEN", Path.home() / "keyboard" / "tastatur-quellen"))
DB = ORDNER / "tastaturen.sqlite"
EXPORT = ORDNER / "export"

SCHEMA = """
CREATE TABLE meta (schluessel TEXT PRIMARY KEY, wert TEXT);

-- Eine Zeile je Quelle, mit allem, was für Nennung und Lizenzprüfung nötig ist.
CREATE TABLE quelle (
  id TEXT PRIMARY KEY,
  name TEXT,
  url TEXT,                   -- Startseite bzw. Repository
  stand TEXT,                 -- Commit und Datum oder Abrufdatum
  lizenz TEXT,                -- Lizenz der Quelle (SPDX, wo möglich)
  lizenz_url TEXT,            -- Lizenztext am verwendeten Stand
  nutzung TEXT,               -- was wir übernehmen (z. B. nur Fakten und Links)
  nennung TEXT,               -- wie die Quelle zu nennen ist
  beschreibung TEXT);

-- Ein Datensatz je Tastatur und Quelle, genau so, wie die Quelle sie beschreibt.
CREATE TABLE datensatz (
  id INTEGER PRIMARY KEY,
  quelle TEXT REFERENCES quelle(id),
  quell_id TEXT,              -- Schlüssel in der Quelle (Pfad, Dateiname, Zeile, Artikelnummer)
  quell_url TEXT,             -- genaue Fundstelle: Datei am gepinnten Commit, Detailseite, Artikel
  weitere_urls TEXT,          -- JSON: weitere Fundstellen (geerbte Dateien, Belege)
  lizenz TEXT,                -- Lizenz dieses Datensatzes (in der Regel die der Quelle)
  abgerufen TEXT,             -- Abrufdatum bzw. Commit-Datum
  name TEXT,
  hersteller TEXT,
  url TEXT,                   -- Projekt- oder Produktseite laut Quelle
  roh TEXT);                  -- JSON: weitere Angaben der Quelle, unverändert

-- Jede Facetten-Angabe mit Herkunft. Mehrere Angaben je Facette sind erlaubt (Varianten, widersprüchliche Quellen).
CREATE TABLE angabe (
  datensatz_id INTEGER REFERENCES datensatz(id),
  facette TEXT,               -- ID aus tastaturen/facetten.json
  wert TEXT,                  -- Wert-ID bzw. Zahl als Text
  methode TEXT,               -- quelle: steht so in der Quelle; abgeleitet: aus Angaben der Quelle berechnet
  beleg TEXT,                 -- woraus genau (Feld, Tag, Specs-Zeile, Layoutname)
  beleg_url TEXT);            -- falls abweichend von datensatz.quell_url

CREATE TABLE layout (
  id INTEGER PRIMARY KEY,
  datensatz_id INTEGER REFERENCES datensatz(id),
  name TEXT,
  tasten INTEGER,
  geteilt_geometrisch INTEGER,
  tasten_links INTEGER, tasten_rechts INTEGER,
  breite REAL, hoehe REAL,
  rotiert INTEGER,
  raster_links TEXT, raster_rechts TEXT,
  daumen_links INTEGER, daumen_rechts INTEGER,
  raster_quelle TEXT,         -- name (aus dem Layoutnamen) oder heuristik
  versatz TEXT,               -- abgeleitet aus der Geometrie: spalten, ortho, reihen, sonstige
  signatur TEXT);

CREATE TABLE taste (
  layout_id INTEGER REFERENCES layout(id),
  idx INTEGER,
  x REAL, y REAL, w REAL, h REAL,   -- Tasten-Einheiten, linke obere Ecke vor Drehung (KLE-Konvention)
  r REAL, rx REAL, ry REAL,         -- Drehung in Grad um (rx, ry)
  cx REAL, cy REAL,                 -- Mittelpunkt nach Drehung
  matrix_zeile INTEGER, matrix_spalte INTEGER,
  bezeichnung TEXT,
  PRIMARY KEY (layout_id, idx));

-- Zusammengeführte Geräte: eine physische Tastatur (Familie mit Varianten) über alle Quellen.
CREATE TABLE geraet (
  id INTEGER PRIMARY KEY,
  slug TEXT UNIQUE,
  name TEXT,
  hersteller TEXT,
  facetten TEXT,              -- JSON: Facette -> Werte bzw. {min, max}
  konflikte TEXT,             -- JSON: Facetten mit widersprüchlichen Angaben
  abgeleitet TEXT,            -- JSON: Auswahl-Facetten, deren Wert nur abgeleitet ist (keine Quelle nennt ihn)
  haupt_layout INTEGER REFERENCES layout(id));
CREATE TABLE geraet_datensatz (
  geraet_id INTEGER REFERENCES geraet(id),
  datensatz_id INTEGER REFERENCES datensatz(id),
  regel TEXT,                 -- warum zugeordnet
  PRIMARY KEY (geraet_id, datensatz_id));

CREATE INDEX angabe_ds ON angabe(datensatz_id);
CREATE INDEX angabe_facette ON angabe(facette, wert);
CREATE INDEX layout_ds ON layout(datensatz_id);
CREATE INDEX datensatz_name ON datensatz(name);
"""


# ----------------------------------------------------------------------------- Dateien und Quellen
def manifest():
    return json.loads((ORDNER / "quellen.json").read_text(encoding="utf-8"))["quellen"]


def git_stand(pfad):
    if not (pfad / ".git").exists():
        return None, None
    aus = subprocess.run(["git", "-C", str(pfad), "log", "-1", "--format=%H %cs"], capture_output=True,
                         text=True).stdout.split()
    return (aus[0], aus[1]) if len(aus) == 2 else (None, None)


def github_blob(repo_url, commit, pfad):
    return f"{repo_url.rstrip('/')}/blob/{commit}/{pfad}"


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
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    text = re.sub(r'([}\]"]|\d|true|false|null)(\s*\n\s*)(["{\[])', r"\1,\2\3", text)
    return json.loads(text)


def tief_mischen(a, b):
    erg = dict(a)
    for k, v in b.items():
        erg[k] = tief_mischen(erg[k], v) if isinstance(v, dict) and isinstance(erg.get(k), dict) else v
    return erg


# ----------------------------------------------------------------------------- Geometrie
def mittelpunkt(t):
    cx, cy = t["x"] + t["w"] / 2, t["y"] + t["h"] / 2
    if t["r"]:
        a = math.radians(t["r"])
        dx, dy = cx - t["rx"], cy - t["ry"]
        cx, cy = t["rx"] + dx * math.cos(a) - dy * math.sin(a), t["ry"] + dx * math.sin(a) + dy * math.cos(a)
    return cx, cy


def _gruppen(tasten, schluessel, sprung):
    gruppen, letzte = [], None
    for t in sorted(tasten, key=lambda t: t[schluessel]):
        if letzte is None or t[schluessel] - letzte > sprung:
            gruppen.append([])
        gruppen[-1].append(t)
        letzte = t[schluessel]
    return gruppen


def raster(haelfte):
    """Heuristik je Hälfte: Daumentasten liegen mehr als 0,6 Tasten unter der typischen untersten Fingerreihe oder
    sind gedreht und tief. Ergebnis wie "3x5+2D": Reihen x volle Fingerspalten, +/- Zusatztasten, Daumen."""
    if len(haelfte) < 4:
        return None, None
    unten = sorted(max(k["cy"] for k in sp) for sp in _gruppen(haelfte, "cx", 0.6) if len(sp) >= 3)
    if not unten:
        return None, None
    grenze = unten[len(unten) // 2] + 0.6
    daumen = [t for t in haelfte if t["cy"] > grenze or (abs(t["r"]) >= 5 and t["cy"] > grenze - 0.8)]
    finger = [t for t in haelfte if t not in daumen]
    hoehen = [len(sp) for sp in _gruppen(finger, "cx", 0.6) if len(sp) >= 2]
    if not hoehen:
        return None, len(daumen)
    reihen = max(sorted(set(hoehen)), key=hoehen.count)
    voll = sum(1 for h in hoehen if h >= reihen)
    rest = len(finger) - reihen * voll
    return f"{reihen}x{voll}" + (f"{rest:+d}" if rest else "") + f"+{len(daumen)}D", len(daumen)


def versatz_geometrie(tasten):
    """Ortho: Mittelpunkte in x und y auf einem gemeinsamen Raster. Spalten: x auf Raster, y je Spalte verschoben.
    Reihen: y auf Raster, Reihen in x verschoben (klassisch). Bewertet werden nur ungedrehte 1u-Tasten einer Hälfte
    (bei geteilten Layouts die linke), damit der Abstand zwischen den Hälften nicht stört."""
    gerade = [t for t in tasten if not t["r"] and abs(t["w"] - 1) < 0.01 and abs(t["h"] - 1) < 0.01]
    if len(gerade) < 12:
        return None

    def auf_raster(werte):
        # mindestens 85 % der Tasten haben denselben Bruchteil (Achtel) -> Achse liegt auf einem Raster
        anteile = [round((v % 1) * 8) % 8 for v in werte]
        return max(anteile.count(a) for a in set(anteile)) >= 0.85 * len(anteile)

    x, y = auf_raster([t["cx"] for t in gerade]), auf_raster([t["cy"] for t in gerade])
    return "ortho" if x and y else "spalten" if x else "reihen" if y else "sonstige"


def ableiten(tasten):
    for t in tasten:
        t["cx"], t["cy"] = mittelpunkt(t)
    n = len(tasten)
    xs = sorted(t["cx"] for t in tasten)
    ys = [t["cy"] for t in tasten]
    a = {"tasten": n, "geteilt_geometrisch": 0, "rotiert": sum(1 for t in tasten if t["r"]),
         "breite": round(xs[-1] - xs[0] + 1, 3), "hoehe": round(max(ys) - min(ys) + 1, 3),
         "versatz": versatz_geometrie(tasten)}
    luecken = [(xs[i + 1] - xs[i], i) for i in range(n - 1)]
    if luecken:
        g, i = max(luecken)
        l, r = i + 1, n - i - 1
        if g >= 1.25 and min(l, r) >= 0.4 * n:
            schnitt = (xs[i] + xs[i + 1]) / 2
            a.update(geteilt_geometrisch=1, tasten_links=l, tasten_rechts=r,
                     versatz=versatz_geometrie([t for t in tasten if t["cx"] < schnitt]))
            a["raster_links"], a["daumen_links"] = raster([t for t in tasten if t["cx"] < schnitt])
            a["raster_rechts"], a["daumen_rechts"] = raster([t for t in tasten if t["cx"] >= schnitt])
    a["signatur"] = ";".join(f"{round(t['cx'] * 4) / 4:g},{round(t['cy'] * 4) / 4:g}" for t in
                             sorted(tasten, key=lambda t: (round(t["cy"] * 4), round(t["cx"] * 4))))
    return a


# ----------------------------------------------------------------------------- Schreiber
class Schreiber:
    def __init__(self, db):
        self.db = db

    def quelle(self, **q):
        felder = ["id", "name", "url", "stand", "lizenz", "lizenz_url", "nutzung", "nennung", "beschreibung"]
        self.db.execute(f"INSERT INTO quelle ({','.join(felder)}) VALUES ({','.join('?' * len(felder))})",
                        [q.get(f) for f in felder])

    def datensatz(self, quelle, quell_id, quell_url, lizenz, abgerufen, name, hersteller=None, url=None,
                  weitere_urls=None, roh=None):
        cur = self.db.execute(
            "INSERT INTO datensatz (quelle, quell_id, quell_url, weitere_urls, lizenz, abgerufen, name, hersteller, "
            "url, roh) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (quelle, quell_id, quell_url, json.dumps(weitere_urls or [], ensure_ascii=False), lizenz, abgerufen,
             name, hersteller, url, json.dumps(roh or {}, ensure_ascii=False, sort_keys=True, default=str)))
        return cur.lastrowid

    def angabe(self, ds, facette, wert, methode="quelle", beleg=None, beleg_url=None):
        if wert is None or wert == "":
            return
        self.db.execute("INSERT INTO angabe VALUES (?,?,?,?,?,?)", (ds, facette, str(wert), methode, beleg, beleg_url))

    def layout(self, ds, name, tasten):
        a = ableiten(tasten)
        m = re.search(r"split_(\d+)x(\d+)_(\d+)", name or "")
        if m and a.get("geteilt_geometrisch"):
            r, c, d = m.groups()
            a["raster_links"] = a["raster_rechts"] = f"{r}x{c}+{d}D"
            a["daumen_links"] = a["daumen_rechts"] = int(d)
            a["raster_quelle"] = "name"
        elif a.get("raster_links"):
            a["raster_quelle"] = "heuristik"
        felder = ["tasten", "geteilt_geometrisch", "tasten_links", "tasten_rechts", "breite", "hoehe", "rotiert",
                  "raster_links", "raster_rechts", "daumen_links", "daumen_rechts", "raster_quelle", "versatz",
                  "signatur"]
        cur = self.db.execute(
            f"INSERT INTO layout (datensatz_id, name, {','.join(felder)}) VALUES (?,?,{','.join('?' * len(felder))})",
            [ds, name] + [a.get(f) for f in felder])
        lid = cur.lastrowid
        self.db.executemany(
            "INSERT INTO taste VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(lid, i, t["x"], t["y"], t["w"], t["h"], t["r"], t["rx"], t["ry"], round(t["cx"], 4),
              round(t["cy"], 4), t.get("mz"), t.get("ms"), t.get("label")) for i, t in enumerate(tasten)])
        return lid, a


# ----------------------------------------------------------------------------- Keycap-Profile im Text
KEYCAP_MUSTER = [
    ("cherry", r"\bcherry[- ]profile|\bpbt cherry\b|\bcherry (?:keycaps?|caps)\b|\bcherry[- ]height"),
    ("oem", r"\boem[- ]profile|\boem (?:keycaps?|caps)\b"), ("sa", r"\bsa[- ]profile|\bsa (?:keycaps?|caps)\b|\bsa wob\b"),
    ("dsa", r"\bdsa\b"), ("xda", r"\bxda\b"), ("kat", r"\bkat\b"), ("kam", r"\bkam\b"), ("mt3", r"\bmt3\b"),
    ("dcs", r"\bdcs\b"), ("mda", r"\bmda\b"), ("osa", r"\bosa\b"), ("ksa", r"\bksa\b"), ("asa", r"\basa\b"), ("moa", r"\bmoa\b"),
    ("xvx", r"\bxvx\b"), ("mbk", r"\bmbk\b"), ("cfx", r"\bcfx\b"),
    ("lp-sonstige", r"\b(?:lpx|lak|lck|ldsa|klp|nsa|lsa)\b|low[- ]profile (?:keycaps|caps)"),
    ("topre", r"\btopre (?:keycaps?|profile)\b"), ("chiclet", r"\bchiclet"),
    ("eigen", r"custom[- ]sculpted|sculpted (?:keycaps|caps)\b|spherical profile")]


def keycap_profile(text):
    """Keycap-Profile, die ein Text ausdrücklich nennt (nur Profilnamen, kein Material)."""
    t = (text or "").lower()
    return [wert for wert, muster in KEYCAP_MUSTER if re.search(muster, t)]


# ----------------------------------------------------------------------------- Facetten aus Produkttexten
# (Facette, Wert, Muster); ein Treffer im Text ergibt eine Angabe "quelle" mit dem Fundstück als Beleg.
TEXT_MUSTER = [
    ("geteilt", "ja", r"\bsplit (?:mechanical |ergonomic |wireless |low[- ]profile )*keyboard|\bsplit design|two (?:separate|independent) halves"),
    ("drahtlos", "ja", r"\bwireless\b|\bbluetooth\b|\b2\.4 ?g(?:hz)?\b|tri-mode"),
    ("drahtlos_technik", "bluetooth", r"\bbluetooth\b|\bble\b"), ("drahtlos_technik", "funk-2-4", r"\b2\.4 ?g(?:hz)?\b|dongle|receiver"),
    ("anschluss", "usb-c", r"\busb[- ]?c\b|type[- ]c\b"), ("anschluss", "usb-a", r"\busb[- ]?a\b"),
    ("anschluss", "bluetooth", r"\bbluetooth\b"), ("anschluss", "dongle", r"\bdongle\b|usb receiver|2\.4 ?ghz receiver"),
    ("anschluss", "ps2", r"\bps/?2\b"), ("anschluss", "usb-micro", r"micro[- ]usb"), ("anschluss", "usb-mini", r"mini[- ]usb"),
    ("schalter", "mx", r"\bmx[- ](?:style|compatible|switch|hot-?swap)|cherry mx|gateron (?:g pro|ks-?9|yellow|red|brown|black)"),
    ("schalter", "choc-v1", r"choc v1|kailh choc(?! v?2)"), ("schalter", "choc-v2", r"choc v2"),
    ("schalter", "gateron-lp", r"gateron (?:low[- ]profile|ks-?33|lp)"), ("schalter", "magnetisch", r"hall[- ]effect|magnetic switch"),
    ("schalter", "optisch", r"optical switch"), ("schalter", "topre", r"\btopre\b|\bec switch"), ("schalter", "alps", r"\balps\b"),
    ("schalter_montage", "hotswap", r"hot[- ]?swap"), ("schalter_montage", "geloetet", r"\bsolder(?:ed|ing) (?:required|version)"),
    ("profil", "flach", r"low[- ]profile"),
    ("beleuchtung", "ja", r"\brgb\b|backlit|backlight|\bled\b|underglow"), ("beleuchtung_farbe", "rgb", r"\brgb\b"),
    ("beleuchtung_farbe", "rgbw", r"\brgbw\b"), ("beleuchtung_farbe", "weiss", r"white (?:led|backlight)"),
    ("nkro", "ja", r"\bnkro\b|n-key rollover"),
    ("display", "ja", r"\boled\b|\bdisplay\b|\bscreen\b|nice!view|e-?ink"), ("drehgeber", "ja", r"\bencoder|\bknob\b|rotary"),
    ("maus", "ja", r"trackball|trackpad|touchpad|trackpoint"), ("maus_art", "trackball", r"trackball"),
    ("maus_art", "trackpad", r"trackpad|touchpad"), ("maus_art", "trackpoint", r"trackpoint"),
    ("material", "aluminium", r"alumin(?:i)?um|cnc"), ("material", "holz", r"\bwood(?:en)?\b|walnut|\bash\b|bamboo"),
    ("material", "acryl", r"acrylic"), ("material", "pc", r"polycarbonate"), ("material", "stahl", r"\bsteel\b"),
    ("material", "pla", r"3d[- ]print"), ("material", "abs", r"\babs (?:case|plastic|housing)"),
    ("keycap_material", "pbt", r"\bpbt\b"), ("keycap_material", "abs", r"\babs keycaps"), ("keycap_material", "pom", r"\bpom keycaps"),
    ("beschriftung", "doubleshot", r"double[- ]shot"), ("beschriftung", "dyesub", r"dye[- ]?sub"),
    ("montageart", "gasket", r"gasket[- ]mount"), ("montageart", "tray", r"tray[- ]mount"), ("montageart", "top", r"top[- ]mount"),
    ("norm_layout", "ansi", r"\bansi\b"), ("norm_layout", "iso", r"\biso\b"), ("norm_layout", "jis", r"\bjis\b"),
    ("versatz", "spalten", r"column(?:ar|[- ]stagger)"), ("versatz", "ortho", r"ortholinear"), ("versatz", "alice", r"\balice\b"),
    ("zelt", "ja", r"\btent(?:ing)?\b"), ("positionierung", "zelt", r"\btent(?:ing)?\b"),
    ("positionierung", "neigung", r"\btilt"), ("positionierung", "negativ", r"negative tilt"),
    ("handballenauflage", "integriert", r"(?:integrated|built-in) (?:palm|wrist) rest"),
    ("betriebssystem", "windows", r"\bwindows\b"), ("betriebssystem", "macos", r"\bmac ?os\b|\bmac\b"),
    ("betriebssystem", "linux", r"\blinux\b"), ("betriebssystem", "ios", r"\bios\b|ipad"), ("betriebssystem", "android", r"\bandroid\b"),
    ("firmware", "qmk", r"\bqmk\b"), ("firmware", "zmk", r"\bzmk\b"), ("firmware", "via", r"\bvia\b"), ("firmware", "vial", r"\bvial\b"),
    ("firmware", "kmk", r"\bkmk\b"), ("firmware", "rmk", r"\brmk\b"), ("ziffernblock", "ja", r"\bnumpad\b|number pad|numeric keypad"),
    # deutsche Shop- und Herstellertexte
    ("geteilt", "ja", r"getrennte (?:tastatur)?hälften|zweigeteilte tastatur|geteilte tastatur(?:hälften)?\b(?! mit)"),
    ("drahtlos", "ja", r"\bkabellos|\bfunktastatur|\bfunk\b"), ("drahtlos_technik", "funk-2-4", r"2,4 ?ghz|usb-empfänger|nano-empfänger"),
    ("anschluss", "dongle", r"usb-empfänger|nano-empfänger"), ("energie", "kabel", r"kabelgebunden"),
    ("energie", "aaa", r"\baaa\b|micro-batterie"), ("energie", "aa", r"\baa-batterie|mignon"),
    ("energie", "akku-fest", r"\bakku\b|wiederaufladbar"),
    ("handballenauflage", "integriert", r"integrierte (?:handballen|handgelenk)auflage"),
    ("handballenauflage", "beigelegt", r"abnehmbare (?:handballen|handgelenk)auflage"),
    ("beleuchtung", "ja", r"hintergrundbeleuchtung|beleuchtete tasten"), ("schalter", "schere", r"scherenmechanik|scherentechnik"),
    ("schalter", "membran", r"rubberdome|rubber-dome|membrantastatur"), ("ziffernblock", "ja", r"ziffernblock|nummernblock"),
    ("ziffernblock", "separat", r"separate[rnm]? (?:ziffern|nummern)block"), ("zelt", "ja", r"zeltförmig|seitliche neigung"),
    ("positionierung", "negativ", r"negative neigung|negativneigung"), ("sprachlayout", "de", r"\bqwertz\b|deutsches layout|layout: deutsch"),
]
FORMFAKTOR = [("100", r"\b(?:100%|full[- ]size)"), ("96", r"\b(?:96%|1800)\b"), ("tkl", r"\btkl\b|tenkeyless|\b8[07]%"),
              ("75", r"\b75%"), ("65", r"\b65%"), ("60", r"\b60%"), ("40", r"\b40%"), ("makropad", r"macro ?pad"),
              ("ziffernblock", r"\bnumpad\b(?! keyboard)")]


def merkmale_aus_text(text):
    """Liefert (facette, wert, fundstueck) für alle Muster, die im Text vorkommen, dazu Zahlen (Tasten, mAh, Hz, g)."""
    t = " ".join((text or "").split())
    klein = t.lower()
    erg = []
    for facette, wert, muster in TEXT_MUSTER:
        m = re.search(muster, klein)
        if m:
            erg.append((facette, wert, klein[max(0, m.start() - 40):m.end() + 40]))
    for wert, muster in FORMFAKTOR:
        m = re.search(muster, klein)
        if m:
            erg.append(("formfaktor", wert, klein[max(0, m.start() - 40):m.end() + 40]))
            break
    for w in keycap_profile(klein):
        erg.append(("keycap_profil", w, "Keycap-Profil im Text"))
    for facette, muster, lo, hi in (("tasten", r"\b(\d{2,3})[- ]?keys?\b", 10, 140), ("tasten", r"\b(\d{2,3}) tasten\b", 10, 140), ("akku_mah", r"\b(\d{3,4}) ?mah\b", 50, 20000),
                                    ("polling", r"\b(\d{3,4})\s?hz\b", 125, 8000), ("gewicht_g", r"\b(\d{3,4}) ?g\b(?!b|hz)", 100, 5000)):
        for m in re.finditer(muster, klein):
            if lo <= int(m.group(1)) <= hi:
                erg.append((facette, int(m.group(1)), klein[max(0, m.start() - 40):m.end() + 40]))
    return erg
