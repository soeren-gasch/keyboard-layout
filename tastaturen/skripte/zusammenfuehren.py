"""Führt Datensätze verschiedener Quellen zu Geräten zusammen und verdichtet ihre Facetten-Angaben.

Ein Gerät ist eine physische Tastatur samt Revisionen und Varianten (z. B. Corne mit 36, 42 und 46 Tasten).
Zuordnungsregeln, jede wird je Datensatz festgehalten:
  familie   QMK/Vial: gleicher Pfad nach Entfernen von Revisions-, Controller- und Variantenteilen
  repo      gleiches Projekt-Repository (github.com/<besitzer>/<repo>) in URL oder Belegen
  name      gleicher normalisierter Name und verträgliche Tastenzahl
Manuelle Korrekturen: tastaturen/zusammenfuehrung.json ("trennen": Datensätze, die nie per Name verbunden werden;
"verbinden": Listen von Datensätzen, die zusammengehören). Datensätze werden als "<quelle>:<quell_id>" angegeben.

Verdichtung je Facette: Auswahl-Facetten nehmen den Wert der vertrauenswürdigsten Quelle (Reihenfolge VORRANG,
Angaben "quelle" vor "abgeleitet"); abweichende Werte werden als Konflikt gespeichert. Mehrfach-Facetten vereinigen
alle Werte. Zahlen werden zu Bereichen (min, max).
"""

import json
import re
from collections import Counter, defaultdict

from basis import ORDNER

VORRANG = ["manuell", "yal", "splitkbcompare", "golem", "deskthority", "shops", "shopseiten", "kbdnews", "zmk", "qmk", "vial", "via", "ergogen", "github", "reddit", "keymapdb"]
ZAHLEN = {"tasten", "tasten_je_haelfte", "daumentasten", "tasten_genutzt", "jahr", "polling", "geraete_kopplung",
          "akku_mah", "gewicht_g"}
MEHRFACH = {"versatz", "maus_art", "schalter", "schalter_montage", "drahtlos_technik", "energie", "firmware",
            "verfuegbarkeit", "raster", "keycap_profil", "beleuchtung_farbe", "positionierung",
            "material", "gehaeusefarbe", "keycap_farbe", "anschluss", "norm_layout", "sprachlayout", "keycap_material",
            "beschriftung", "betriebssystem", "konfiguration", "verbindung_haelften"}
VARIANTE = re.compile(r"^(rev(\d\w*|_\w+|[a-z]?\d*)|v\d[\w.]*|r\d+|mk(\d\w*|_\w+)?|mark(\d\w*|_\w+)?|base|standard|mini|pro_?micro|elite_?c|rp2040|kb2040|"
                      r"stm32\w*|proton_?c|blackpill|bluepill|splinky\w*|teensy\w*|ble|wireless|wired|hotswap|"
                      r"solder(ed)?|ansi|iso|jis|lp|choc|mx|f\d{3}\w*|nrf\w*|ec|left|right|\d[\d_.]*|promicro|"
                      r"pico|xiao\w*|helios|sea_picro|liatris|frood|gd32\w*|atmega\w*|at90\w*|apm32\w*|wb32\w*)$")
GENERISCH = {"ansi", "iso", "macropad", "numpad", "keyboard", "split", "test", "prototype", "custom", "ortho",
             "unnamed", "untitled", "planck", "60", "65", "75", "tkl", "40", "ergo", "mini", "plus", "lite", "max",
             "ultra", "wireless", "mechanical", "gaming", "keypad", "board", "keeb", "keebs", "macro", "compact"}
FREMD_REPOS = {"yal-tools/ergo-keyboards", "qmk/qmk_firmware", "zmkfirmware/zmk", "vial-kb/vial-qmk", "jhelvy/splitkbcompare",
               "precondition/keymapdb"}


def normname(name, hersteller=None):
    n = (name or "").lower()
    if hersteller:
        for w in re.findall(r"[a-z0-9]+", hersteller.lower()):
            if len(w) >= 3:
                n = re.sub(rf"^\s*{re.escape(w)}\b", "", n)
    n = re.sub(r"\b(keyboard|wireless|split|ergonomic|mechanical|rev\s*\d+\w*|v\d+(\.\d+)*|mk\s*\w+|mark\s*\w+|pro|kit|"
               r"review|build|the|ansi|iso|jis|rgb|knob|encoder|white|backlit|backlight|hot-?swap|wired|pcb|pre-?built|"
               r"assembled|diy|lp|low[- ]profile|choc|mx|ce|set|edition|bundle|case|plate)\b", " ", n)
    return re.sub(r"[^a-z0-9]", "", n)


def repos(ds):
    urls = [ds["url"] or ""] + (json.loads(ds["weitere_urls"] or "[]") if ds["quelle"] != "keymapdb" else [])
    if ds["quelle"] in ("manuell", "github", "ergogen"):
        urls.append(ds["quell_url"] or "")
    erg = set()
    for u in urls:
        m = re.search(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", u or "")
        if m:
            r = f"{m.group(1)}/{m.group(2)}".lower().removesuffix(".git")
            if r not in FREMD_REPOS:
                erg.add(r)
    return erg


class Mengen:
    """Union-Find; je Gruppe werden Tastenzahlen und QMK-Familien mitgeführt, damit Verbindungen über Datensätze
    ohne Tastenzahl keine unverträglichen Tastaturen zusammenketten."""

    def __init__(self):
        self.eltern, self.tasten, self.familien = {}, {}, {}

    def finde(self, a):
        self.eltern.setdefault(a, a)
        while self.eltern[a] != a:
            self.eltern[a] = self.eltern[self.eltern[a]]
            a = self.eltern[a]
        return a

    def vertraeglich(self, a, b):
        ra, rb = self.finde(a), self.finde(b)
        if ra == rb:
            return True
        ta, tb = self.tasten.get(ra, set()), self.tasten.get(rb, set())
        if ta and tb and (min(tb) > max(ta) + 2 or min(ta) > max(tb) + 2):
            return False
        for fa in self.familien.get(ra, set()):
            for fb in self.familien.get(rb, set()):
                if not (fa == fb or fa.startswith(fb + "/") or fb.startswith(fa + "/")):
                    return False
        return True

    def vereine(self, a, b, pruefen=True):
        ra, rb = self.finde(a), self.finde(b)
        if ra == rb or (pruefen and not self.vertraeglich(ra, rb)):
            return ra == rb
        neu, alt = min(ra, rb), max(ra, rb)
        self.eltern[alt] = neu
        self.tasten[neu] = self.tasten.get(neu, set()) | self.tasten.pop(alt, set())
        self.familien[neu] = self.familien.get(neu, set()) | self.familien.pop(alt, set())
        return True


def zusammenfuehren(db):
    db.row_factory = None
    spalten = ["id", "quelle", "quell_id", "quell_url", "weitere_urls", "name", "hersteller", "url"]
    alle = [dict(zip(spalten, z)) for z in db.execute(f"SELECT {','.join(spalten)} FROM datensatz")]
    tasten = defaultdict(set)
    for ds, w in db.execute("SELECT datensatz_id, wert FROM angabe WHERE facette = 'tasten'"):
        tasten[ds].add(int(w))
    korrektur_datei = ORDNER / "zusammenfuehrung.json"
    korr = json.loads(korrektur_datei.read_text(encoding="utf-8")) if korrektur_datei.exists() else {}
    schluessel = {f"{d['quelle']}:{d['quell_id']}": d["id"] for d in alle}
    getrennt = {schluessel[k] for k in korr.get("trennen", []) if k in schluessel}

    m = Mengen()
    regel = {}
    for d in alle:
        m.finde(d["id"])
        m.tasten[d["id"]] = set(tasten[d["id"]])
    # 1. QMK/Vial-Familie
    fam, fam_von = defaultdict(list), {}
    for d in alle:
        if d["quelle"] in ("qmk", "vial"):
            teile = d["quell_id"].split("/")
            mindestens = 2 if len(teile) >= 3 else 1
            while len(teile) > mindestens and VARIANTE.match(teile[-1]):
                teile = teile[:-1]
            fam["/".join(teile)].append(d["id"])
            fam_von[d["id"]] = "/".join(teile)
            m.familien[d["id"]] = {"/".join(teile)}
    for ids in fam.values():
        for i in ids[1:]:
            m.vereine(ids[0], i, pruefen=False)
            regel.setdefault(i, "familie")
    # 2. Repository
    nach_repo = defaultdict(list)
    for d in alle:
        for r in repos(d):
            nach_repo[r].append(d["id"])
    nach_id = {d["id"]: d for d in alle}

    def verwandt(a, b):
        """Gleiches Repository allein reicht nicht (Sammel-Repos wie gtips/reviung): Name oder Tastenzahl muss passen."""
        na = {normname(nach_id[a]["name"]), normname(nach_id[a]["name"], nach_id[a]["hersteller"])} - {""}
        nb = {normname(nach_id[b]["name"]), normname(nach_id[b]["name"], nach_id[b]["hersteller"])} - {""}
        if any(x == y or (len(x) >= 4 and len(y) >= 4 and (x in y or y in x)) for x in na for y in nb):
            return True
        # Ergogen-Repositories enthalten oft mehrere Tastaturen: dort zählt nur der Name
        if "ergogen" in (nach_id[a]["quelle"], nach_id[b]["quelle"]):
            return False
        return bool(tasten[a] & tasten[b])

    for r, ids in nach_repo.items():
        for i in ids[1:]:
            for j in ids:
                if j < i and verwandt(i, j) and m.vereine(j, i):
                    regel.setdefault(i, f"repo {r}")
                    break
    # 3. Name mit verträglicher Tastenzahl
    marken = {re.sub(r"[^a-z0-9]", "", w) for d in alle for w in [(d["hersteller"] or "").lower()] +
              (d["hersteller"] or "").lower().split()}
    nach_name = defaultdict(list)
    for d in alle:
        for n in {normname(d["name"], d["hersteller"]), normname(d["name"])}:
            # ein Name, der nach dem Normalisieren nur noch die Marke ist (Keychron V1 -> keychron), verbindet nichts
            if len(n) >= 4 and n not in GENERISCH and n not in marken and d["id"] not in getrennt:
                nach_name[n].append(d)
    for n, ds in nach_name.items():
        if len({x["quelle"] for x in ds}) < 2 and not any(x["quelle"] in ("qmk", "vial") for x in ds):
            continue
        for k, x in enumerate(ds[1:], 1):
            for y in ds[:k]:
                if m.vereine(y["id"], x["id"]):
                    regel.setdefault(x["id"], f"name {n}")
                    break
    # 4. manuelle Verbindungen
    for gruppe in korr.get("verbinden", []):
        ids = [schluessel[k] for k in gruppe if k in schluessel]
        for i in ids[1:]:
            m.vereine(ids[0], i, pruefen=False)
            regel[i] = "manuell"

    gruppen = defaultdict(list)
    for d in alle:
        gruppen[m.finde(d["id"])].append(d)
    angaben = defaultdict(list)
    for ds, f, w, meth in db.execute("SELECT datensatz_id, facette, wert, methode FROM angabe"):
        angaben[ds].append((f, w, meth))
    haupt = {}
    for lid, ds, name, n in db.execute("SELECT id, datensatz_id, name, tasten FROM layout"):
        bewertung = (name == "LAYOUT", n)
        if ds not in haupt or bewertung > haupt[ds][0]:
            haupt[ds] = (bewertung, lid)

    slugs = Counter()
    for wurzel, ds in sorted(gruppen.items()):
        ds.sort(key=lambda d: (VORRANG.index(d["quelle"]), d["id"]))
        # Gerätename: der häufigste Name über alle Quellen, bei Gleichstand die vertrauenswürdigste Quelle
        haeufig = Counter((d["name"] or "").strip().lower() for d in ds if d["name"])
        name = min((d["name"] for d in ds if d["name"]),
                   key=lambda n: (-haeufig[n.strip().lower()], 0)) if haeufig else ds[0]["name"]
        hersteller = next((d["hersteller"] for d in ds if d["hersteller"]), None)
        basis = re.sub(r"[^a-z0-9]+", "-", (name or "tastatur").lower()).strip("-") or "tastatur"
        slug, k = basis, 1
        while slug in slugs:
            k += 1
            slug = f"{basis}-{k}"
        slugs[slug] += 1
        facetten, konflikte = verdichten(ds, angaben)
        lids = [haupt[d["id"]] for d in ds if d["id"] in haupt]
        haupt_layout = max(lids)[1] if lids else None
        cur = db.execute("INSERT INTO geraet (slug, name, hersteller, facetten, konflikte, haupt_layout) "
                         "VALUES (?,?,?,?,?,?)", (slug, name, hersteller, json.dumps(facetten, ensure_ascii=False),
                                                 json.dumps(konflikte, ensure_ascii=False), haupt_layout))
        gid = cur.lastrowid
        db.executemany("INSERT INTO geraet_datensatz VALUES (?,?,?)",
                       [(gid, d["id"], "anker" if d["id"] == wurzel else regel.get(d["id"], "anker")) for d in ds])
    return len(gruppen)


def verdichten(datensaetze, angaben):
    rang = {d["id"]: VORRANG.index(d["quelle"]) for d in datensaetze}
    gesammelt = defaultdict(list)
    for d in datensaetze:
        for f, w, meth in angaben[d["id"]]:
            gesammelt[f].append((rang[d["id"]], 0 if meth == "quelle" else 1, w))
    facetten, konflikte = {}, {}
    for f, werte in gesammelt.items():
        if f in ZAHLEN:
            zahlen = sorted(int(w) for _, _, w in werte)
            facetten[f] = {"min": zahlen[0], "max": zahlen[-1]} if f != "jahr" else zahlen[0]
        elif f in MEHRFACH:
            facetten[f] = sorted({w for _, _, w in werte})
        else:
            werte.sort()
            facetten[f] = werte[0][2]
            andere = sorted({w for _, _, w in werte} - {werte[0][2]})
            if andere:
                konflikte[f] = andere
    if facetten.get("maus_art") and "maus" not in facetten:
        facetten["maus"] = "ja"
    return facetten, konflikte
