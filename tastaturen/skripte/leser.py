"""Leser je Quelle. Jeder Leser legt die Quelle an, schreibt je Tastatur einen Datensatz mit genauer Fundstelle und
übersetzt die Angaben der Quelle in Facetten (tastaturen/facetten.json). Jede Facetten-Angabe nennt ihren Beleg."""

import csv
import datetime
import html
import json
import re

import yaml

from basis import QUELLEN, ORDNER, git_stand, github_blob, json_tolerant, keycap_profile, manifest, tief_mischen

M = manifest()


def quelle_anlegen(s, qid, beschreibung, stand=None, commit=None):
    q = M[qid]
    lizenz_url = None
    if q.get("lizenz_datei") and commit:
        lizenz_url = github_blob(q["url"], commit, q["lizenz_datei"])
    s.quelle(id=qid, name=q.get("name"), url=q.get("url"), stand=stand, lizenz=q.get("lizenz"),
             lizenz_url=lizenz_url or q.get("lizenz_url"), nutzung=q.get("nutzung"), nennung=q.get("nennung"),
             beschreibung=beschreibung)
    return q


# ----------------------------------------------------------------------------- QMK und Vial
ZEIGER = {"pmw3360": "trackball", "pmw3389": "trackball", "pmw3320": "trackball", "adns5050": "trackball",
          "adns9800": "trackball", "paw3204": "trackball", "pmw3610": "trackball", "cirque_pinnacle_i2c": "trackpad",
          "cirque_pinnacle_spi": "trackpad", "azoteq_iqs5xx": "trackpad", "analog_joystick": "joystick",
          "ps2": "trackpoint", "pimoroni_trackball": "trackball"}


def lies_qmk(s):
    return _qmk_baum(s, "qmk", sorted(p.parent for p in (QUELLEN / "qmk" / "keyboards").glob("**/keyboard.json")))


def lies_vial(s):
    basis, qmk = QUELLEN / "vial" / "keyboards", QUELLEN / "qmk" / "keyboards"
    ziele = []
    for p in sorted(set(basis.glob("**/keyboard.json")) | set(basis.glob("**/info.json"))):
        ordner = p.parent
        if (qmk / ordner.relative_to(basis)).exists():
            continue
        if any(q.parent != ordner for q in ordner.glob("*/**/info.json")) or \
                any(q.parent != ordner for q in ordner.glob("*/**/keyboard.json")):
            continue
        ziele.append(ordner)
    return _qmk_baum(s, "vial", sorted(set(ziele)))


def _qmk_baum(s, qid, ziele):
    wurzel = QUELLEN / qid
    basis = wurzel / "keyboards"
    commit, datum = git_stand(wurzel)
    q = quelle_anlegen(s, qid, "Tastatur-Definitionen (keyboard.json und geerbte info.json) mit Tastenpositionen je "
                               "Layout-Makro", f"{commit} {datum}", commit)
    fehler, cache, anzahl = [], {}, 0

    def lade(p):
        if p not in cache:
            try:
                cache[p] = json_tolerant(p.read_text(encoding="utf-8-sig"))
            except Exception as e:  # noqa: BLE001
                fehler.append((str(p.relative_to(basis)), str(e)[:80]))
                cache[p] = {}
        return cache[p]

    for ordner in ziele:
        rel = ordner.relative_to(basis)
        daten, dateien = {}, []
        for i in range(1, len(rel.parts) + 1):
            info = basis.joinpath(*rel.parts[:i]) / "info.json"
            if info.exists():
                daten = tief_mischen(daten, lade(info))
                dateien.append(f"keyboards/{'/'.join(rel.parts[:i])}/info.json")
        if (ordner / "keyboard.json").exists():
            daten = tief_mischen(daten, lade(ordner / "keyboard.json"))
            dateien.append(f"keyboards/{rel.as_posix()}/keyboard.json")
        urls = [github_blob(q["url"], commit, d) for d in dateien]
        feat = daten.get("features") or {}
        roh = {k: daten[k] for k in ("community_layouts", "layout_aliases", "features", "processor", "usb") if k in daten}
        ds = s.datensatz(qid, rel.as_posix(), urls[-1] if urls else None, q["lizenz"], datum,
                         daten.get("keyboard_name") or rel.parts[-1], daten.get("manufacturer"),
                         daten.get("url") or None, urls[:-1], roh)
        s.angabe(ds, "firmware", "qmk" if qid == "qmk" else "vial", "quelle", f"{qid}-Repository")
        if qid == "vial":
            s.angabe(ds, "firmware", "qmk", "abgeleitet", "Vial ist ein QMK-Fork")
        if (daten.get("split") or {}).get("enabled"):
            s.angabe(ds, "geteilt", "ja", "quelle", "split.enabled = true")
        elif qid == "qmk":
            r = _readme_geteilt(basis, rel)
            if r:
                s.angabe(ds, "geteilt", r[0], "quelle", f"readme.md: …{r[1]}…", github_blob(q["url"], commit, r[2]))
        if feat.get("pointing_device") or daten.get("pointing_device"):
            s.angabe(ds, "maus", "ja", "quelle", "features.pointing_device")
            treiber = (daten.get("pointing_device") or {}).get("driver")
            if treiber in ZEIGER:
                s.angabe(ds, "maus_art", ZEIGER[treiber], "abgeleitet", f"pointing_device.driver = {treiber}")
        if feat.get("encoder") or daten.get("encoder"):
            s.angabe(ds, "drehgeber", "ja", "quelle", "features.encoder bzw. encoder")
        if feat.get("oled") or feat.get("quantum_painter"):
            s.angabe(ds, "display", "ja", "quelle", "features.oled bzw. quantum_painter")
        if feat.get("bluetooth") or daten.get("bluetooth"):
            s.angabe(ds, "drahtlos", "ja", "quelle", "features.bluetooth")
            s.angabe(ds, "drahtlos_technik", "bluetooth", "quelle", "features.bluetooth")
        for name, l in (daten.get("layouts") or {}).items():
            tasten = []
            for t in (l.get("layout") or []):
                if isinstance(t, dict):
                    m = t.get("matrix") or [None, None]
                    tasten.append({"x": float(t.get("x", 0)), "y": float(t.get("y", 0)), "w": float(t.get("w", 1)),
                                   "h": float(t.get("h", 1)), "r": float(t.get("r", 0)), "rx": float(t.get("rx", 0)),
                                   "ry": float(t.get("ry", 0)), "mz": m[0], "ms": m[1], "label": t.get("label")})
            if tasten:
                _layout_angaben(s, ds, name, tasten)
        anzahl += 1
    return anzahl, fehler


# Readme der Tastatur (erste Absätze): "split keyboard" bzw. "unibody". Ausgenommen geteilte Leertaste/Backspace,
# "pseudo-split", "conjoined split" und "split hand layout" (beschreiben Unibodys).
_NICHT = r"(?!\s*-?\s*(?:space|spacebar|backspace|bar|shift|enter|bs|rs|plus|keys?\b))"
README_UNIBODY = re.compile(r"\bunibody\b|\bmono-?block\b|\bone[- ]piece split\b|\bconjoined[- ]split\b|"
                            r"\bpseudo[- ]split\b|\bfixed split\b|\bsplit[- ]hand layout\b", re.I)
README_SPLIT = re.compile(r"\bsplit" + _NICHT + r"[\s,-]+(?:[\w%/()-]+[\s,]+){0,4}?(?:keyboard|keeb|board)s?\b|"
                          r"\btwo (?:separate |independent )?halves\b|\bsplit" + _NICHT +
                          r"(?: ergonomic| ergo| columnar| column[- ]staggered| ortholinear| wireless)", re.I)


def _readme_geteilt(basis, rel):
    for i in range(len(rel.parts), 0, -1):
        p = basis.joinpath(*rel.parts[:i]) / "readme.md"
        if p.exists():
            t = re.sub(r"!\[[^\]]*\]\([^)]*\)|\]\([^)]*\)|https?://\S+|`[^`]*`", " ", p.read_text(errors="replace"))
            t = " ".join(t.split())[:600]
            for wert, muster in (("einteilig-geteilt", README_UNIBODY), ("ja", README_SPLIT)):
                m = muster.search(t)
                if m:
                    return wert, t[max(0, m.start() - 40):m.end() + 30], f"keyboards/{'/'.join(rel.parts[:i])}/readme.md"
            return None
    return None


def _layout_angaben(s, ds, name, tasten):
    lid, a = s.layout(ds, name, tasten)
    beleg = f"Layout {name}"
    s.angabe(ds, "tasten", a["tasten"], "abgeleitet", f"{beleg}: Anzahl Tasten")
    if a.get("geteilt_geometrisch"):
        s.angabe(ds, "tasten_je_haelfte", max(a["tasten_links"], a["tasten_rechts"]), "abgeleitet", beleg)
        if a.get("raster_quelle") == "name":
            r = a["raster_links"].split("+")[0]
            s.angabe(ds, "raster", r, "quelle", f"Layoutname {name}")
            s.angabe(ds, "daumentasten", a["daumen_links"], "quelle", f"Layoutname {name}")
    lname = (name or "").lower()
    if "ortho" in lname:
        s.angabe(ds, "versatz", "ortho", "quelle", f"Layoutname {name}")
    elif "alice" in lname:
        s.angabe(ds, "versatz", "alice", "quelle", f"Layoutname {name}")
    elif a.get("versatz") in ("spalten", "ortho", "reihen"):
        s.angabe(ds, "versatz", a["versatz"], "abgeleitet", f"{beleg}: Tastenpositionen")
    return lid


# ----------------------------------------------------------------------------- ZMK
_ATTR = re.compile(r"<&key_physical_attrs\s+([^>]*)>")
_LAYOUT_NODE = re.compile(r"(\w+)\s*:\s*\w+\s*\{[^{}]*?compatible\s*=\s*\"zmk,physical-layout\"(.*?)\};", re.S)


def zmk_layouts_in(text):
    erg = {}
    for m in _LAYOUT_NODE.finditer(text):
        label, rumpf = m.group(1), m.group(2)
        anzeige = re.search(r"display-name\s*=\s*\"([^\"]*)\"", rumpf)
        tasten = []
        for a in _ATTR.finditer(rumpf):
            teile = re.findall(r"\(\s*-?\s*\d+\s*\)|-?\d+", a.group(1))
            if len(teile) >= 7:
                w, h, x, y, rot, rx, ry = (float(t.strip("()").replace(" ", "")) for t in teile[:7])
                tasten.append({"x": x / 100, "y": y / 100, "w": w / 100, "h": h / 100, "r": rot / 100,
                               "rx": rx / 100, "ry": ry / 100})
        if tasten:
            erg[label] = (anzeige.group(1) if anzeige else label, tasten)
    return erg


def lies_zmk(s):
    wurzel = QUELLEN / "zmk"
    app = wurzel / "app"
    commit, datum = git_stand(wurzel)
    q = quelle_anlegen(s, "zmk", "Boards und Shields mit Metadaten (*.zmk.yml) und physischen Layouts",
                       f"{commit} {datum}", commit)
    anzahl = 0
    for yml in sorted(app.glob("boards/**/*.zmk.yml")):
        meta = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
        if meta.get("type") not in ("shield", "board"):
            continue
        ordner = yml.parent
        # Layouts je Board-Ordner (Labels wie physical_layout0 kommen in vielen Boards vor)
        alle, herkunft = {}, {}
        for f in sorted(list(ordner.glob("*.dtsi")) + list(ordner.glob("*.overlay")) + list(ordner.glob("*.dts"))):
            text = f.read_text(encoding="utf-8", errors="replace")
            dateien = [f] + [app / "dts" / inc for inc in re.findall(r"#include\s*<(layouts/[^>]+)>", text)]
            for d in dateien:
                if d.exists():
                    for label, wert in zmk_layouts_in(d.read_text(encoding="utf-8", errors="replace")).items():
                        alle.setdefault(label, wert)
                        herkunft.setdefault(label, d.relative_to(wurzel).as_posix())
        labels = list(alle)
        features = meta.get("features") or []
        url = github_blob(q["url"], commit, yml.relative_to(wurzel).as_posix())
        ds = s.datensatz("zmk", yml.relative_to(app).as_posix(), url, q["lizenz"], datum,
                         meta.get("name") or meta.get("id"), None, meta.get("url"),
                         [github_blob(q["url"], commit, herkunft[l]) for l in labels],
                         {"typ": meta.get("type"), "features": features, "requires": meta.get("requires"),
                          "siblings": meta.get("siblings")})
        s.angabe(ds, "firmware", "zmk", "quelle", "ZMK-Repository")
        if meta.get("siblings"):
            s.angabe(ds, "geteilt", "ja", "quelle", f"siblings: {', '.join(meta['siblings'])}")
        if "display" in features:
            s.angabe(ds, "display", "optional", "quelle", "features: display")
        if "encoder" in features:
            s.angabe(ds, "drehgeber", "optional", "quelle", "features: encoder")
        if "pointing" in features:
            s.angabe(ds, "maus", "ja", "quelle", "features: pointing")
        for label in labels:
            _layout_angaben(s, ds, alle[label][0], [dict(t) for t in alle[label][1]])
        anzahl += 1
    return anzahl, []


# ----------------------------------------------------------------------------- splitKbCompare
VERSATZ_SKC = {"Aggressive": "spalten", "Agressive": "spalten", "Moderate": "spalten", "None": None}


def lies_splitkbcompare(s):
    wurzel = QUELLEN / "splitkbcompare"
    commit, datum = git_stand(wurzel)
    q = quelle_anlegen(s, "splitkbcompare", "Kuratierte Tabelle von Split-Tastaturen", f"{commit} {datum}", commit)
    anzahl = 0
    with open(wurzel / "keyboards.csv", encoding="utf-8") as f:
        for zeile_nr, z in enumerate(csv.DictReader(f), start=2):
            url = github_blob(q["url"], commit, "keyboards.csv") + f"#L{zeile_nr}"
            ds = s.datensatz("splitkbcompare", z["id"], url, q["lizenz"], datum, z["name"], None,
                             z.get("url_source") if z.get("url_source") not in ("", "NA") else None,
                             [z["url_store"]] if z.get("url_store") not in (None, "", "NA") else [], z)
            if z.get("include") == "0":
                continue

            def a(facette, wert, spalte):
                s.angabe(ds, facette, wert, "quelle", f"Spalte {spalte} = {z.get(spalte)}")

            for spalte in ("nKeysMin", "nKeysMax"):
                if z.get(spalte) not in ("", "NA"):
                    a("tasten", int(z[spalte]), spalte)
            a("geteilt", "einteilig-geteilt" if z.get("onePiece") == "1" else "ja", "onePiece")
            if z.get("wireless") in ("0", "1"):
                a("drahtlos", "ja" if z["wireless"] == "1" else "nein", "wireless")
            for wert, spalte in (("mx", "mxCompatible"), ("choc-v1", "chocV1"), ("choc-v2", "chocV2")):
                if z.get(spalte) == "1":
                    a("schalter", wert, spalte)
            if VERSATZ_SKC.get(z.get("colStagger")):
                a("versatz", "spalten", "colStagger")
            elif z.get("colStagger") == "None" and z.get("rowStagger") == "0":
                a("versatz", "ortho", "colStagger")
            if z.get("rowStagger") == "1":
                a("versatz", "reihen", "rowStagger")
            if z.get("hasNumRow") in ("0", "1"):
                a("zahlenreihe", "ja" if z["hasNumRow"] == "1" else "nein", "hasNumRow")
            if z.get("rotaryEncoder") == "1":
                a("drehgeber", "optional", "rotaryEncoder")
            if z.get("diy") == "1":
                a("verfuegbarkeit", "selbstbau", "diy")
            if z.get("prebuilt") == "1":
                a("verfuegbarkeit", "fertig", "prebuilt")
            if z.get("openSource") in ("0", "1"):
                a("open_source_hardware", "ja" if z["openSource"] == "1" else "nein", "openSource")
            anzahl += 1
    return anzahl, []


# ----------------------------------------------------------------------------- golem.hu
VERSATZ_GOLEM = {"columnar": "spalten", "ortholinear": "ortho", "regular": "reihen", "scooped": "mulde",
                 "fan": "radial", "unique": "sonstige", "symmetric": "sonstige"}
BEZUG_GOLEM = {"prototype": "prototyp", "open source": "selbstbau", "open-source": "selbstbau", "prebuilt": "fertig",
               "commercial": "fertig", "kit": "kit", "group buy": "gruppenbestellung", "gb": "gruppenbestellung",
               "discontinued": "eingestellt", "vintage": "eingestellt", "custom prototype": "prototyp"}
TAGS_GOLEM = {
    "hotswap": [("schalter_montage", "hotswap")], "low profile": [("profil", "flach")],
    "low-profile": [("profil", "flach")], "trackball": [("maus", "ja"), ("maus_art", "trackball")],
    "trackpoint": [("maus", "ja"), ("maus_art", "trackpoint")], "joystick": [("maus", "ja"), ("maus_art", "joystick")],
    "encoder": [("drehgeber", "ja")], "display": [("display", "ja")], "number row": [("zahlenreihe", "ja")],
    "keywell": [("versatz", "mulde")], "scooped": [("versatz", "mulde")], "ortholinear": [("versatz", "ortho")],
    "columnar": [("versatz", "spalten")], "Alice": [("versatz", "alice")], "fan": [("spreizung", "ja")],
    "pinky fan": [("spreizung", "ja")], "pinky-fan": [("spreizung", "ja")], "solar": [("energie", "solar")],
    "wireless": [("drahtlos", "ja")], "wired": [("drahtlos", "nein"), ("energie", "kabel")],
    "monoblock": [("geteilt", "einteilig-geteilt")], "separate": [("geteilt", "ja")],
    "handwired": [("schalter_montage", "geloetet")], "prebuilt": [("verfuegbarkeit", "fertig")],
    "kit": [("verfuegbarkeit", "kit")], "group buy": [("verfuegbarkeit", "gruppenbestellung")],
    "discontinued": [("verfuegbarkeit", "eingestellt")], "open source": [("open_source_hardware", "ja")],
    "open-source": [("open_source_hardware", "ja")]}


def lies_golem(s):
    wurzel = QUELLEN / "golem"
    seiten = sorted((wurzel / "board").glob("*.html"))
    stand = datetime.date.fromtimestamp(max(f.stat().st_mtime for f in seiten)).isoformat() if seiten else None
    q = quelle_anlegen(s, "golem", "Sammlung von Split- und gewinkelten Einteiler-Tastaturen, Stand etwa 2021",
                       f"abgerufen {stand}")
    anzahl, fehler = 0, []
    for f in seiten:
        h = f.read_text(encoding="utf-8", errors="replace")
        felder = {th.strip(): td.strip() for th, td in
                  re.findall(r"<tr><th>([^<]*)<td[^>]*>(.*?)(?=<tr>|</table>)", h, re.S)}
        if not felder.get("Keyboard"):
            fehler.append((f.name, "keine Datentabelle"))
            continue
        tags = re.findall(r'<a href="board/tag/[^"]*">([^<]*)</a>', h)
        links = re.findall(r'href="(https?://[^"]+)"', felder.get("Resources", "") + felder.get("More info", ""))
        url = "https://golem.hu/board/" + f.name
        ds = s.datensatz("golem", f.name, url, q["lizenz"], stand, html.unescape(felder["Keyboard"]),
                         html.unescape(felder.get("Developer", "")) or None, links[0] if links else None, links,
                         {"felder": {k: re.sub(r"<[^>]+>", " ", v).strip() for k, v in felder.items()
                                     if k not in ("Features",)}, "tags": tags})
        for n in re.findall(r"\d+", felder.get("Keys", "")):
            s.angabe(ds, "tasten", int(n), "quelle", f"Keys: {felder['Keys']}")
        sep = felder.get("Separate", "").lower()
        if sep in ("yes", "no"):
            s.angabe(ds, "geteilt", "ja" if sep == "yes" else "einteilig-geteilt", "quelle", f"Separate: {sep}")
        wl = felder.get("Wireless", "").lower()
        if wl in ("yes", "no"):
            s.angabe(ds, "drahtlos", "ja" if wl == "yes" else "nein", "quelle", f"Wireless: {wl}")
        if VERSATZ_GOLEM.get(felder.get("Stagger", "")):
            s.angabe(ds, "versatz", VERSATZ_GOLEM[felder["Stagger"]], "quelle", f"Stagger: {felder['Stagger']}")
        for teil in re.split(r"[,+/()]", felder.get("Availability", "").lower()):
            if BEZUG_GOLEM.get(teil.strip()):
                s.angabe(ds, "verfuegbarkeit", BEZUG_GOLEM[teil.strip()], "quelle",
                         f"Availability: {felder['Availability']}")
        jahr = re.match(r"(\d{4})", felder.get("Published", ""))
        if jahr and jahr.group(1) != "0000":
            s.angabe(ds, "jahr", int(jahr.group(1)), "quelle", f"Published: {felder['Published']}")
        for tag in tags:
            for facette, wert in TAGS_GOLEM.get(tag, []):
                s.angabe(ds, facette, wert, "quelle", f"Tag: {tag}")
            m = re.match(r"(\d)-key thumb cluster", tag)
            if m:
                s.angabe(ds, "daumentasten", int(m.group(1)), "quelle", f"Tag: {tag}")
        anzahl += 1
    return anzahl, fehler


# ----------------------------------------------------------------------------- KeymapDB
FIRMWARE_KMDB = {"QMK": "qmk", "ZMK": "zmk", "KMK": "kmk"}
VERSATZ_KMDB = {"columnar": "spalten", "ortholinear": "ortho", "row": "reihen"}


def lies_keymapdb(s):
    wurzel = QUELLEN / "keymapdb"
    commit, datum = git_stand(wurzel)
    q = quelle_anlegen(s, "keymapdb", "Dokumentierte persönliche Keymaps", f"{commit} {datum}", commit)
    anzahl, fehler = 0, []
    for f in sorted((wurzel / "src" / "posts" / "keymaps").glob("*.md")):
        text = f.read_text(encoding="utf-8")
        m = re.match(r"---\n(.*?)\n---", text, re.S)
        try:
            d = yaml.safe_load(m.group(1)) if m else None
        except yaml.YAMLError as e:
            fehler.append((f.name, str(e)[:60]))
            continue
        if not d or not d.get("keyboard"):
            continue
        datei = github_blob(q["url"], commit, f.relative_to(wurzel).as_posix())
        ds = s.datensatz("keymapdb", f.stem, f"https://keymapdb.com/keymaps/{f.stem}/", q["lizenz"], datum,
                         str(d["keyboard"]), None, None, [datei, d.get("keymapUrl")],
                         {k: d.get(k) for k in ("author", "baseLayouts", "hasHomeRowMods", "hasLetterOnThumb",
                                                "isComboEnabled", "isAutoShiftEnabled", "isTapDanceEnabled",
                                                "layerCount", "languages", "OS", "keymapImage", "keyCount",
                                                "firmwares", "stagger", "isSplit")})
        if d.get("keyCount"):
            s.angabe(ds, "tasten_genutzt", int(d["keyCount"]), "quelle", "keyCount (in der Keymap genutzte Tasten)")
        if d.get("isSplit") is True:
            s.angabe(ds, "geteilt", "ja", "quelle", "isSplit: true")
        if VERSATZ_KMDB.get(d.get("stagger")):
            s.angabe(ds, "versatz", VERSATZ_KMDB[d["stagger"]], "quelle", f"stagger: {d['stagger']}")
        for fw in d.get("firmwares") or []:
            if FIRMWARE_KMDB.get(str(fw)):
                s.angabe(ds, "firmware", FIRMWARE_KMDB[str(fw)], "quelle", f"firmwares: {fw}")
        if d.get("hasRotaryEncoder") is True:
            s.angabe(ds, "drehgeber", "ja", "quelle", "hasRotaryEncoder: true")
        anzahl += 1
    return anzahl, fehler


# ----------------------------------------------------------------------------- eigene Recherche
def lies_manuell(s):
    """manuell.json (eigene Recherche) und alle manuell/*.yaml (Blöcke nach tastaturen/recherche-vorlage.md)."""
    p = ORDNER / "manuell.json"
    daten = json.loads(p.read_text(encoding="utf-8"))
    for y in sorted((ORDNER / "manuell").glob("*.yaml")) if (ORDNER / "manuell").exists() else []:
        for block in yaml.safe_load_all(y.read_text(encoding="utf-8")):
            if block and block.get("name"):
                daten["tastaturen"].append(block)
    q = quelle_anlegen(s, "manuell", "Eigene Recherche: Herstellerseiten und Projektseiten, jede Angabe belegt",
                       daten.get("stand"))
    for t in daten["tastaturen"]:
        belege = t.get("belege") or []
        ds = s.datensatz("manuell", t["name"], belege[0] if belege else t.get("url"), q["lizenz"],
                         str(t.get("gelesen_am") or daten.get("stand")),
                         t["name"], t.get("hersteller"), t.get("url"), belege[1:], t)
        for facette, werte in (t.get("facetten") or {}).items():
            for w in werte if isinstance(werte, list) else [werte]:
                s.angabe(ds, facette, w, "quelle", "Herstellerangabe")
    return len(daten["tastaturen"]), []


# ----------------------------------------------------------------------------- GitHub-Topics
HW_TOPICS = {"pcb", "kicad", "ergogen", "3d-printing", "hardware", "open-hardware", "open-source-hardware",
             "handwired", "handwired-keyboard", "keyboard-pcb", "pcb-design", "cad", "fusion360", "freecad",
             "3d-models", "dactyl", "dactyl-manuform", "choc-switches", "hotswap", "keyboard-case", "openscad",
             "build123d", "cadquery"}
SW_TOPICS = {"zmk-config", "qmk-config", "qmk-keymap", "keymap", "keymap-drawer", "dotfiles", "typing-practice",
             "android", "ios", "macos", "windows", "tui", "cli", "colemak", "colemak-dh", "home-row-mods", "kanata",
             "karabiner", "ergogen-footprints", "keyboard-layout", "typing", "swift", "java", "python", "linux"}
HW_TEXT = re.compile(r"\b(pcb|kicad|ergogen|hand-?wired|3d[- ]print\w*|case|plate|\d{2,3}[- ]keys?|"
                     r"(split|ergonomic|ortholinear|columnar|mechanical) keyboard|keyboard (design|pcb)|"
                     r"choc|gateron|kailh)\b", re.I)
SW_TEXT = re.compile(r"\b(keymap|config(uration)?s? for|dotfiles|layout for|userspace|firmware for my|"
                     r"my (zmk|qmk) config)\b", re.I)
TOPICS_GH = {
    "split-keyboard": [("geteilt", "ja")], "wireless": [("drahtlos", "ja")], "wireless-keyboard": [("drahtlos", "ja")],
    "bluetooth": [("drahtlos", "ja"), ("drahtlos_technik", "bluetooth")],
    "nice-nano": [("drahtlos", "ja"), ("drahtlos_technik", "bluetooth")],
    "choc-switches": [("schalter", "choc-v1")], "hotswap": [("schalter_montage", "hotswap")],
    "handwired": [("schalter_montage", "geloetet")], "handwired-keyboard": [("schalter_montage", "geloetet")],
    "trackball": [("maus", "ja"), ("maus_art", "trackball")], "trackpad": [("maus", "ja"), ("maus_art", "trackpad")],
    "trackpoint": [("maus", "ja"), ("maus_art", "trackpoint")], "oled": [("display", "ja")],
    "rotary-encoder": [("drehgeber", "ja")], "ortholinear": [("versatz", "ortho")],
    "ortholinear-keyboard": [("versatz", "ortho")], "column-staggered": [("versatz", "spalten")],
    "zmk": [("firmware", "zmk")], "qmk": [("firmware", "qmk")], "kmk": [("firmware", "kmk")],
    "kmk-firmware": [("firmware", "kmk")], "vial": [("firmware", "vial")], "rmk": [("firmware", "rmk")],
    "open-hardware": [("open_source_hardware", "ja")], "open-source-hardware": [("open_source_hardware", "ja")],
    "low-profile": [("profil", "flach")], "dactyl": [("versatz", "mulde")], "dactyl-manuform": [("versatz", "mulde")]}


def lies_github(s):
    wurzel = QUELLEN / "github"
    dateien = sorted(wurzel.glob("*.json"))
    repos, themen, abruf = {}, {}, None
    for f in dateien:
        d = json.loads(f.read_text(encoding="utf-8"))
        abruf = d.get("abgerufen")
        for it in d["items"]:
            repos[it["full_name"]] = it
            themen.setdefault(it["full_name"], set()).add(d["topic"])
    q = quelle_anlegen(s, "github", "Hardware-Repositories aus der GitHub-Suche nach Topics", f"abgerufen {abruf}")
    anzahl = 0
    for name, r in sorted(repos.items()):
        topics = set(r.get("topics") or [])
        text = f"{r.get('name', '')} {r.get('description') or ''}"
        hw = bool(topics & HW_TOPICS) or bool(HW_TEXT.search(text))
        sw = bool(topics & SW_TOPICS) or bool(SW_TEXT.search(text)) or \
            re.search(r"(zmk|qmk)[-_]?(config|keymap|userspace)|keymaps?$|dotfiles", r.get("name", ""), re.I)
        if not hw or (sw and not topics & HW_TOPICS):
            continue
        lizenz = (r.get("license") or {}).get("spdx_id")
        ds = s.datensatz("github", name, r["html_url"], lizenz if lizenz and lizenz != "NOASSERTION" else
                         "unknown (no license detected by GitHub)", abruf, r.get("name"),
                         (r.get("owner") or {}).get("login"), r["html_url"],
                         [u for u in [r.get("homepage")] if u],
                         {"beschreibung": r.get("description"), "topics": sorted(topics),
                          "gefunden_ueber": sorted(themen[name]), "erstellt": r.get("created_at"),
                          "zuletzt_geaendert": r.get("pushed_at"), "sterne": r.get("stargazers_count"),
                          "lizenz_spdx": lizenz})
        s.angabe(ds, "verfuegbarkeit", "selbstbau", "abgeleitet", "öffentliches Hardware-Repository")
        if lizenz and lizenz != "NOASSERTION":
            s.angabe(ds, "hardware_lizenz", lizenz, "quelle", "Lizenz des Repositorys laut GitHub")
        if r.get("created_at"):
            s.angabe(ds, "jahr", int(r["created_at"][:4]), "abgeleitet", "Repository angelegt (frühestens)")
        for t in topics:
            for facette, wert in TOPICS_GH.get(t, []):
                s.angabe(ds, facette, wert, "quelle", f"Topic: {t}")
        beschreibung = (r.get("description") or "").lower()
        for von, bis in re.findall(r"(\d{2,3})\s*(?:-|–|to)\s*(\d{2,3})[- ]keys?\b", beschreibung):
            s.angabe(ds, "tasten", int(von), "quelle", "Beschreibung")
            s.angabe(ds, "tasten", int(bis), "quelle", "Beschreibung")
        for n in re.findall(r"\b(\d{2,3})[- ]keys?\b", beschreibung):
            s.angabe(ds, "tasten", int(n), "quelle", "Beschreibung")
        m = re.search(r"\b([2-6])x([4-8])\b", beschreibung)
        if m:
            s.angabe(ds, "raster", f"{m.group(1)}x{m.group(2)}", "quelle", "Beschreibung")
        for muster, facette, wert in ((r"low[- ]profile", "profil", "flach"), (r"\bsplit\b", "geteilt", "ja"),
                                      (r"wireless|bluetooth", "drahtlos", "ja"), (r"trackball", "maus_art", "trackball"),
                                      (r"columnar|column[- ]stagger", "versatz", "spalten"),
                                      (r"ortholinear", "versatz", "ortho"), (r"choc", "schalter", "choc-v1")):
            if re.search(muster, beschreibung):
                s.angabe(ds, facette, wert, "quelle", "Beschreibung")
        anzahl += 1
    return anzahl, []


# ----------------------------------------------------------------------------- YAL's ergo keyboard list
SCHALTER_YAL = {"MX": "mx", "Choc": "choc-v1", "ChocV2": "choc-v2", "GateronLP": "gateron-lp", "Alps": "alps",
                "HallEffect": "magnetisch", "Topre": "topre"}
FIRMWARE_YAL = {"QMK": "qmk", "ZMK": "zmk", "KMK": "kmk", "RMK": "rmk", "Vial": "vial", "VIA": "via",
                "Custom": "proprietaer"}


def _liste(v):
    return v if isinstance(v, list) else [] if v is None else [v]


def _zahlen(v):
    if isinstance(v, dict):
        return [v.get("min"), v.get("max")]
    return [x for x in _liste(v) if isinstance(x, (int, float))]


def lies_yal(s):
    wurzel = QUELLEN / "yal"
    commit, datum = git_stand(wurzel)
    q = quelle_anlegen(s, "yal", "YAL's ergo keyboard list: spalten-, ortho- und reihenversetzte Ergo-Tastaturen",
                       f"{commit} {datum}", commit)
    anzahl = 0
    for datei, versatz in (("docs/keyboards.js", None), ("docs/rowstag.js", "reihen")):
        text = (wurzel / datei).read_text(encoding="utf-8")
        eintraege = [e for e in json_tolerant(text[text.find("["):text.rfind("]") + 1]) if isinstance(e, dict)]
        nach_name = {e.get("name"): e for e in eintraege if e.get("name")}
        zeilen = text.split("\n")
        for e in eintraege:
            if not e.get("name"):
                continue
            daten, eltern = dict(e), e.get("parent")
            while eltern and eltern in nach_name:     # Varianten erben vom Eltern-Eintrag
                daten = {**nach_name[eltern], **daten}
                eltern = nach_name[eltern].get("parent") if nach_name[eltern] is not daten else None
            zeile = next((i + 1 for i, z in enumerate(zeilen) if f'"name": "{e["name"]}"' in z), None)
            url = github_blob(q["url"], commit, datei) + (f"#L{zeile}" if zeile else "")
            links = [u.lstrip("!").split("] ")[-1] for u in _liste(daten.get("source")) + _liste(daten.get("kit"))
                     + _liste(daten.get("prebuilt")) + _liste(daten.get("web")) if isinstance(u, str)]
            ds = s.datensatz("yal", f"{datei}#{e['name']}", url, q["lizenz"], datum, e["name"], None,
                             links[0] if links else None, links[1:],
                             {k: v for k, v in daten.items() if k not in ("img", "notes")})

            def a(f, w, feld):
                s.angabe(ds, f, w, "quelle", f"{feld}: {json.dumps(daten.get(feld), ensure_ascii=False)[:80]}")

            for n in _zahlen(daten.get("keys")):
                a("tasten", int(n), "keys")
            if isinstance(daten.get("rows"), int) and isinstance(daten.get("cols"), int):
                a("raster", f"{daten['rows']}x{daten['cols']}", "cols")
            for n in _zahlen(daten.get("thumbKeys")):
                a("daumentasten", int(n), "thumbKeys")
            form = _liste(daten.get("shape"))
            if "Split" in form:
                a("geteilt", "ja", "shape")
            elif {"Unibody", "Monoblock"} & set(form):
                a("geteilt", "einteilig-geteilt", "shape")
            if "Keywell" in form:
                a("versatz", "mulde", "shape")
            for st in _liste(daten.get("stagger")):
                if st in ("Column", "Ortho"):
                    a("versatz", "spalten" if st == "Column" else "ortho", "stagger")
            if versatz:
                s.angabe(ds, "versatz", versatz, "quelle", "Liste der reihenversetzten Tastaturen (rowstag.js)")
            verb = set(_liste(daten.get("connection")))
            funk = verb & {"Bluetooth", "Wireless"}
            if funk:
                a("drahtlos", "optional" if "Wired" in verb else "ja", "connection")
                if "Bluetooth" in verb:
                    a("drahtlos_technik", "bluetooth", "connection")
            elif verb == {"Wired"}:
                a("drahtlos", "nein", "connection")
                a("energie", "kabel", "connection")
            for h in _liste(daten.get("hotswap")):
                if h in ("Yes", True):
                    a("schalter_montage", "hotswap", "hotswap")
                elif h in ("No", False):
                    a("schalter_montage", "geloetet", "hotswap")
            for sp in _liste(daten.get("switchProfile")):
                if sp in SCHALTER_YAL:
                    a("schalter", SCHALTER_YAL[sp], "switchProfile")
            for fw in _liste(daten.get("firmware")) + _liste(daten.get("software")):
                if fw in FIRMWARE_YAL:
                    a("firmware", FIRMWARE_YAL[fw], "firmware" if fw in _liste(daten.get("firmware")) else "software")
            arten = {"trackballs": "trackball", "trackpads": "trackpad", "trackpoints": "trackpoint",
                     "joysticks": "joystick"}
            for feld in list(arten) + ["pointingDevices"]:
                werte = _zahlen(daten.get(feld))
                if werte and max(werte) > 0:
                    a("maus", "optional" if min(werte) == 0 else "ja", feld)
                    if feld in arten:
                        a("maus_art", arten[feld], feld)
            for feld, facette in (("encoders", "drehgeber"), ("displays", "display")):
                werte = _zahlen(daten.get(feld))
                if werte and max(werte) > 0:
                    a(facette, "optional" if min(werte) == 0 else "ja", feld)
            if daten.get("splay") in ("Yes", "PinkyOnly"):
                a("spreizung", "ja", "splay")
            elif daten.get("splay") == "No":
                a("spreizung", "nein", "splay")
            if daten.get("tenting") not in (None, "None", "No", False):
                a("zelt", "ja", "tenting")
            if daten.get("source"):
                a("verfuegbarkeit", "selbstbau", "source")
                a("open_source_hardware", "ja", "source")
            if daten.get("kit"):
                a("verfuegbarkeit", "kit", "kit")
            if daten.get("prebuilt"):
                a("verfuegbarkeit", "fertig", "prebuilt")
            if set(_liste(daten.get("switchProfile"))) <= {"Choc", "ChocV2", "GateronLP", "ChocMini"} and \
                    daten.get("switchProfile"):
                a("profil", "flach", "switchProfile")
            anzahl += 1
    return anzahl, []


# ----------------------------------------------------------------------------- Ergogen
KEIN_SCHALTER = re.compile(r"mcu|controller|promicro|pro_micro|nice|xiao|pico|battery|batt|jumper|power|reset|outline|"
                           r"hole|screw|logo|trrs|jst|oled|display|view|encoder|switch_?on|slider|led|magnet|foot|"
                           r"mount|standoff|label|text|cutout|usb|connector|diode", re.I)
MM_JE_U = 19.05


def lies_ergogen(s):
    manifest = json.loads((ORDNER / "ergogen.json").read_text(encoding="utf-8"))["repositories"]
    punkte_ordner = QUELLEN / "ergogen-punkte"
    github_lizenz = {}
    for f in (QUELLEN / "github").glob("*.json"):
        for it in json.loads(f.read_text(encoding="utf-8"))["items"]:
            github_lizenz[it["full_name"].lower()] = (it.get("license") or {}).get("spdx_id")
    q = quelle_anlegen(s, "ergogen", "Ergogen-Konfigurationen aus Projekt-Repositories, berechnet mit Ergogen 4.2.1 "
                                     "bzw. 3.1.2", None)
    anzahl, fehler = 0, []
    for repo, eintrag in sorted(manifest.items()):
        dateien = eintrag.get("ergogen") or []
        for pfad in dateien:
            ergebnis_datei = punkte_ordner / repo.replace("/", "__") / (pfad + ".json")
            if not ergebnis_datei.exists():
                continue
            erg = json.loads(ergebnis_datei.read_text(encoding="utf-8"))
            if not erg.get("punkte"):
                fehler.append((f"{repo}/{pfad}", "; ".join(erg.get("fehler", []))[:120]))
                continue
            tasten = []
            for name, p in erg["punkte"].items():
                meta = p.get("meta") or {}
                w, h = float(meta.get("width") or 0), float(meta.get("height") or 0)
                if meta.get("skip") or KEIN_SCHALTER.search(name):
                    continue
                if 0.5 <= w <= 3 and 0.5 <= h <= 3:        # Ergogen 3: Größe in Tasten-Einheiten
                    wu, hu = w, h
                elif 12 <= w <= 40 and 12 <= h <= 40:      # Größe in Millimetern
                    wu, hu = w / MM_JE_U, h / MM_JE_U
                else:
                    continue
                cx, cy = float(p["x"]) / MM_JE_U, -float(p["y"]) / MM_JE_U
                tasten.append({"x": cx - wu / 2, "y": cy - hu / 2, "w": wu, "h": hu, "r": -float(p.get("r") or 0),
                               "rx": cx, "ry": cy, "label": name})
            if len(tasten) < 4:
                fehler.append((f"{repo}/{pfad}", f"nur {len(tasten)} Tasten erkannt"))
                continue
            lizenz = github_lizenz.get(repo.lower())
            if not lizenz or lizenz == "NOASSERTION":
                lizdat = eintrag.get("lizenzdateien") or []
                lizenz = (f"see {github_blob('https://github.com/' + repo, eintrag['commit'], lizdat[0])}"
                          if lizdat else "no license found in repository")
            stamm = pfad.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            generisch = re.fullmatch(r"(config|ergogen|keyboard|main|points|board|layout|default|input|index|"
                                     r"config[_-]?\w{0,6}|ergogen[_-]?\w{0,6})", stamm, re.I)
            name = stamm
            if generisch:   # nächster aussagekräftiger Ordnername, sonst der Repository-Name
                ordner = [t for t in pfad.split("/")[:-1] if not re.fullmatch(
                    r"(ergogen|boards?|files|src|pcbs?|configs?|hardware|kicad|v\d[\w.]*|\d+keys?|keyboards?|docs?|"
                    r"documentation|design|cad)", t, re.I)]
                name = ordner[-1] if ordner else repo.split("/")[1]
            ds = s.datensatz("ergogen", f"{repo}/{pfad}",
                             github_blob(f"https://github.com/{repo}", eintrag["commit"], pfad), lizenz, None, name,
                             repo.split("/")[0], f"https://github.com/{repo}", [],
                             {"ergogen_version": erg["version"], "punkte": len(erg["punkte"]),
                              "tasten_erkannt": len(tasten)})
            s.angabe(ds, "verfuegbarkeit", "selbstbau", "abgeleitet", "öffentliche Ergogen-Konfiguration")
            gespiegelt = any(t["label"].startswith("mirror_") for t in tasten)
            _, a = s.layout(ds, stamm, tasten)
            if gespiegelt or a.get("geteilt_geometrisch"):
                s.angabe(ds, "tasten", len(tasten), "abgeleitet", "Ergogen-Punkte, beide Hälften")
                if a.get("geteilt_geometrisch"):
                    s.angabe(ds, "tasten_je_haelfte", max(a["tasten_links"], a["tasten_rechts"]), "abgeleitet",
                             "Ergogen-Punkte")
            else:
                s.angabe(ds, "tasten_je_haelfte", len(tasten), "abgeleitet",
                         "Ergogen-Punkte einer Hälfte (Konfiguration ohne Spiegelung)")
            if a.get("versatz") in ("spalten", "ortho", "reihen"):
                s.angabe(ds, "versatz", a["versatz"], "abgeleitet", "Ergogen-Punkte")
            winkel = {round(t["r"]) for t in tasten}
            if len(winkel) > 2:
                s.angabe(ds, "spreizung", "ja", "abgeleitet", f"Drehwinkel der Tasten: {sorted(winkel)[:6]}")
            anzahl += 1
    return anzahl, fehler


# ----------------------------------------------------------------------------- VIA (the-via/keyboards)
def kle_tasten(zeilen):
    """KLE-Layout (Keyboard Layout Editor) in Tasten; Logik wie kle-serial. Bei VIA-Layout-Optionen (4. Zeile der
    Beschriftung "gruppe,wahl") zählt nur Wahl 0."""
    akt = {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0, "r": 0.0, "rx": 0.0, "ry": 0.0}
    tasten = []
    for zeile in zeilen:
        if not isinstance(zeile, list):
            continue
        dekor = False
        for el in zeile:
            if isinstance(el, dict):
                if "r" in el:
                    akt["r"] = float(el["r"])
                if "rx" in el:
                    akt["rx"] = float(el["rx"])
                    akt["x"], akt["y"] = akt["rx"], akt["ry"]
                if "ry" in el:
                    akt["ry"] = float(el["ry"])
                    akt["x"], akt["y"] = akt["rx"], akt["ry"]
                akt["x"] += float(el.get("x", 0))
                akt["y"] += float(el.get("y", 0))
                if "w" in el:
                    akt["w"] = float(el["w"])
                if "h" in el:
                    akt["h"] = float(el["h"])
                dekor = bool(el.get("d", dekor))
            else:
                teile = str(el).split("\n")
                option = teile[3] if len(teile) > 3 else ""
                m = re.match(r"\s*(\d+)\s*,\s*(\d+)", teile[0])
                wahl = re.match(r"\s*\d+\s*,\s*(\d+)", option)
                if not dekor and not (wahl and wahl.group(1) != "0"):
                    tasten.append({"x": akt["x"], "y": akt["y"], "w": akt["w"], "h": akt["h"], "r": akt["r"],
                                   "rx": akt["rx"], "ry": akt["ry"], "mz": int(m.group(1)) if m else None,
                                   "ms": int(m.group(2)) if m else None})
                akt["x"] += akt["w"]
                akt["w"] = akt["h"] = 1.0
                dekor = False
        akt["y"] += 1
        akt["x"] = akt["rx"]
    return tasten


def lies_via(s):
    wurzel = QUELLEN / "via"
    commit, datum = git_stand(wurzel)
    q = quelle_anlegen(s, "via", "VIA-Tastaturdefinitionen (v3) mit Layout im KLE-Format", f"{commit} {datum}",
                       commit)
    anzahl, fehler = 0, []
    for f in sorted((wurzel / "v3").glob("**/*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8-sig"))
        except ValueError as e:
            fehler.append((f.name, str(e)[:60]))
            continue
        km = ((d.get("layouts") or {}).get("keymap"))
        if not isinstance(d.get("name"), str) or not d["name"].strip() or not isinstance(km, list):
            continue
        rel = f.relative_to(wurzel).as_posix()
        ds = s.datensatz("via", rel, github_blob(q["url"], commit, rel), q["lizenz"], datum, d["name"], rel.split("/")[1],
                         None, [], {"vendorId": d.get("vendorId"), "productId": d.get("productId"),
                                    "matrix": d.get("matrix")})
        s.angabe(ds, "firmware", "via", "quelle", "VIA-Definition")
        tasten = kle_tasten(km)
        if tasten:
            _layout_angaben(s, ds, "VIA keymap", tasten)
        anzahl += 1
    return anzahl, fehler


# ----------------------------------------------------------------------------- Deskthority-Wiki
SCHALTER_DT = [(r"topre|capacitive|electrostatic", "topre"), (r"cherry mx|\bmx\b|gateron|kailh(?! choc)|outemu",
                                                               "mx"),
               (r"\balps\b|matias|simplified alps|complicated alps", "alps"), (r"buckling spring", "knickfeder"),
               (r"rubber dome|membrane|dome", "membran"), (r"scissor", "schere"), (r"optical", "optisch"),
               (r"hall effect|magnetic|hall-effect", "magnetisch"), (r"choc", "choc-v1")]


def _wiki_text(v):
    v = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", v)
    v = re.sub(r"\{\{(?:bulleted list|plainlist|ubl)\|", "", v, flags=re.I)
    v = re.sub(r"\{\{[^{}]*\}\}", " ", v)
    v = re.sub(r"<[^>]+>", " ", v)
    return re.sub(r"\s+", " ", v.replace("}}", " ").replace("|", "; ")).strip()


def _infobox(text):
    i = text.lower().find("{{infobox d")
    if i < 0:
        return {}
    tiefe, j = 0, i
    while j < len(text):
        if text.startswith("{{", j):
            tiefe, j = tiefe + 1, j + 2
            continue
        if text.startswith("}}", j):
            tiefe, j = tiefe - 1, j + 2
            if tiefe == 0:
                break
            continue
        j += 1
    rumpf = text[i + 2:j - 2]
    felder, tiefe, stueck = {}, 0, ""
    teile = []
    for c in rumpf:          # an "|" auf oberster Ebene trennen
        if c in "{[":
            tiefe += 1
        elif c in "}]":
            tiefe -= 1
        if c == "|" and tiefe == 0:
            teile.append(stueck)
            stueck = ""
        else:
            stueck += c
    teile.append(stueck)
    for t in teile[1:]:
        if "=" in t:
            k, v = t.split("=", 1)
            felder[k.strip().lower()] = v.strip()
    return felder


def lies_deskthority(s):
    daten = json.loads((QUELLEN / "deskthority" / "seiten.json").read_text(encoding="utf-8"))
    q = quelle_anlegen(s, "deskthority", "Deskthority-Wiki: Tastaturseiten mit Infobox", f"abgerufen {daten['abgerufen']}")
    anzahl = 0
    for titel, seite in sorted(daten["seiten"].items()):
        f = _infobox(seite.get("text") or "")
        if not f:
            continue
        url = f"https://deskthority.net/wiki/{titel.replace(' ', '_')}"
        hersteller = _wiki_text(f.get("manufacturer", "")) or None
        ds = s.datensatz("deskthority", titel, f"{url}?oldid={seite.get('revid')}" if seite.get("revid") else url,
                         q["lizenz"], (seite.get("zeitstempel") or "")[:10] or daten["abgerufen"],
                         _wiki_text(f.get("name", "")) or titel, hersteller, url, [],
                         {k: _wiki_text(v) for k, v in f.items() if k in ("switch", "layouts", "interface",
                                                                          "introduced", "price", "pn", "keycaps")})
        for w in keycap_profile(_wiki_text(f.get("keycaps", ""))):
            s.angabe(ds, "keycap_profil", w, "quelle", f"keycaps: {_wiki_text(f.get('keycaps', ''))[:80]}")
        schalter = _wiki_text(f.get("switch", "")).lower()
        for muster, wert in SCHALTER_DT:
            if re.search(muster, schalter):
                s.angabe(ds, "schalter", wert, "quelle", f"switch: {schalter[:80]}")
        layouts = _wiki_text(f.get("layouts", ""))
        for gruppe in re.findall(r"((?:\d{2,3}\s*/\s*)*\d{2,3})\s*(?:-key|keys?)?\s*(?:ANSI|ISO|JIS|key)", layouts,
                                 re.I):
            for n in re.findall(r"\d{2,3}", gruppe):
                if 20 <= int(n) <= 160:
                    s.angabe(ds, "tasten", int(n), "quelle", f"layouts: {layouts[:80]}")
        schnitt = _wiki_text(f.get("interface", "")).lower()
        if re.search(r"bluetooth", schnitt):
            s.angabe(ds, "drahtlos", "ja", "quelle", f"interface: {schnitt[:60]}")
            s.angabe(ds, "drahtlos_technik", "bluetooth", "quelle", f"interface: {schnitt[:60]}")
        elif re.search(r"wireless|2\.4|rf\b|infrared|ir\b", schnitt):
            s.angabe(ds, "drahtlos", "ja", "quelle", f"interface: {schnitt[:60]}")
        elif re.search(r"usb|ps/2|at\b|xt\b|adb|serial|din", schnitt):
            s.angabe(ds, "drahtlos", "nein", "quelle", f"interface: {schnitt[:60]}")
            s.angabe(ds, "energie", "kabel", "quelle", f"interface: {schnitt[:60]}")
        jahr = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", _wiki_text(f.get("introduced", "")))
        if jahr:
            s.angabe(ds, "jahr", int(jahr.group(1)), "quelle", f"introduced: {f.get('introduced', '')[:40]}")
        if f.get("price"):
            s.angabe(ds, "preis", _wiki_text(f["price"])[:40], "quelle", "price")
        anzahl += 1
    return anzahl, []


# ----------------------------------------------------------------------------- Reddit (über Arctic Shift)
SW_REPO = re.compile(r"(zmk|qmk|kmk)[-_]?(config|keymap|userspace|module|studio)|keymap|dotfiles|^miryoku|kanata|keyd|"
                     r"karabiner|layout[s]?$|^zmk$|^qmk_firmware$|^vial|firmware$|^ergogen$|footprints?$|kle|"
                     r"keyboard-layout-editor|typing|trainer|config$", re.I)
TITEL_FAKTEN = [(r"\bsplit\b", "geteilt", "ja"), (r"wireless|bluetooth|\bble\b", "drahtlos", "ja"),
                (r"low[- ]?profile|\bchoc\b", "profil", "flach"), (r"\bchoc v?2\b", "schalter", "choc-v2"),
                (r"\bchoc(?! v?2)\b", "schalter", "choc-v1"), (r"trackball", "maus_art", "trackball"),
                (r"trackpad|touchpad", "maus_art", "trackpad"), (r"trackpoint", "maus_art", "trackpoint"),
                (r"trackball|trackpad|touchpad|trackpoint", "maus", "ja"), (r"ortholinear|\bortho\b", "versatz", "ortho"),
                (r"column[- ]?stagger|columnar", "versatz", "spalten"), (r"hand-?wired", "schalter_montage", "geloetet"),
                (r"hot-?swap", "schalter_montage", "hotswap"), (r"\bsplay", "spreizung", "ja"),
                (r"\bzmk\b", "firmware", "zmk"), (r"\bqmk\b", "firmware", "qmk"), (r"\bkmk\b", "firmware", "kmk"),
                (r"\bunibody\b|\bmonoblock\b", "geteilt", "einteilig-geteilt"), (r"tent", "zelt", "ja")]


def lies_reddit(s):
    q = quelle_anlegen(s, "reddit", "Reddit-Posts, die auf Tastatur-Hardware-Repositories verlinken", None)
    nach_repo = {}
    for datei in sorted((QUELLEN / "reddit").glob("*.jsonl")):
        sub = datei.stem
        for zeile in datei.read_text(encoding="utf-8").splitlines():
            if not zeile:
                continue
            p = json.loads(zeile)
            text = f"{p.get('url') or ''} {p.get('selftext') or ''}"
            for besitzer, name in re.findall(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", text):
                name = name.removesuffix(".git").rstrip(".")
                repo = f"{besitzer}/{name}"
                if SW_REPO.search(name) or besitzer.lower() in ("qmk", "zmkfirmware", "vial-kb", "ergogen"):
                    continue
                nach_repo.setdefault(repo.lower(), {"repo": repo, "posts": []})["posts"].append({
                    "url": f"https://www.reddit.com/r/{sub}/comments/{p['id']}/", "titel": p.get("title") or "",
                    "flair": p.get("link_flair_text"), "zeit": int(p.get("created_utc") or 0),
                    "punkte": p.get("score")})
    anzahl = 0
    for eintrag in sorted(nach_repo.values(), key=lambda e: e["repo"].lower()):
        posts = sorted(eintrag["posts"], key=lambda p: p["zeit"])
        # nur Projekt-Vorstellungen: mindestens ein Post ohne Hilfe-/Diskussions-Flair
        if all((p["flair"] or "").lower() in ("[help]", "[discussion]", "[request]") for p in posts):
            continue
        repo = eintrag["repo"]
        erster = posts[0]
        jahr = datetime.datetime.fromtimestamp(erster["zeit"], datetime.UTC).year if erster["zeit"] else None
        ds = s.datensatz("reddit", repo, erster["url"], q["lizenz"],
                         datetime.datetime.fromtimestamp(erster["zeit"], datetime.UTC).date().isoformat()
                         if erster["zeit"] else None, repo.split("/")[1], repo.split("/")[0],
                         f"https://github.com/{repo}", [p["url"] for p in posts[1:6]],
                         {"posts": len(posts), "titel": [p["titel"] for p in posts[:5]],
                          "flairs": sorted({p["flair"] for p in posts if p["flair"]})})
        if jahr:
            s.angabe(ds, "jahr", jahr, "abgeleitet", "erster Reddit-Post (frühestens)", erster["url"])
        for p in posts:
            t = p["titel"].lower()
            for muster, facette, wert in TITEL_FAKTEN:
                if re.search(muster, t):
                    s.angabe(ds, facette, wert, "quelle", f"Titel: {p['titel'][:100]}", p["url"])
            for n in re.findall(r"\b(\d{2,3})[- ]?keys?\b", t):
                if 10 <= int(n) <= 130:
                    s.angabe(ds, "tasten", int(n), "quelle", f"Titel: {p['titel'][:100]}", p["url"])
        anzahl += 1
    return anzahl, []


# ----------------------------------------------------------------------------- Online-Shops (Shopify)
SHOP_AUSSCHLUSS = re.compile(r"keycap|\bcaps\b|switch(?:es)?\b(?![^|]*keyboard)|desk ?mat|\bmat\b|cable|stabili|lube|puller|"
                             r"tester|sticker|gift ?card|artisan|wrist ?rest|palm|foam|o-?ring|spring|\btool|\bbag\b|sleeve|"
                             r"\bmouse\b|\bmice\b|adapter|\bbattery\b|screws?\b|\bfeet\b|tenting|\bstand\b|\bhub\b|dock|"
                             r"spacebar|\bmount\b|socket|diode|controller|nice!nano|\bmcu\b|plate\b|\bcase\b(?! kit)|bundle|"
                             r"t-?shirt|hoodie|poster|charger|\bknob\b(?! keyboard)|warranty|upgrade card|reservation|"
                             r"insurance|shipping|deposit|sample|replacement|spare|parts?\b", re.I)
SHOP_EINSCHLUSS = re.compile(r"keyboard|\bkit\b|\bpcb\b|macro ?pad|numpad|\bsplit\b|\d{2,3}[- ]?key|\bergo", re.I)
# Shops mit Schwerpunkt Ergo/Split/DIY: alle Tastaturen. Allgemeine Shops: nur Produkte mit ergonomischem Merkmal
# (Stufe 1 der Datenbank; normale Massenmarkt-Tastaturen sind Stufe 3 und werden nicht aufgenommen).
ERGO_SHOPS = {"keeb.io", "splitkb.com", "boardsource.xyz", "typeractive.xyz", "holykeebs.com", "littlekeyboards.com",
              "lowprokb.ca", "keebmaker.com", "dygma.com", "x-bows.com", "svalboard.com", "www.charachorder.com",
              "cyboard.digital", "shop.keyboard.io", "shop.goldtouch.com", "perixx.com", "mechboards.co.uk", "elimkeys.com"}
ERGO_TEXT = re.compile(r"\bsplit\b|ergonom|\balice\b|column|ortholinear|\bortho\b|thumb cluster|tenting|corne|sofle|"
                       r"lily ?58|kyria|\biris\b|ferris|sweep|dactyl|charybdis|skeletyl|totem|piantor|cheapino|reviung|"
                       r"planck|preonic|\b40%|\b3[0-9][- ]key|\b4[0-8][- ]key|keywell|one[- ]handed|chord", re.I)


def _titel_schluessel(titel):
    """Gleiche Produkte in Varianten (keebmaker: je Konfiguration ein Produkt) zusammenfassen."""
    t = titel.lower()
    t = re.sub(r"\b(custom|mystery|limited|edition|new|v\d+(\.\d+)*)\b", " ", t)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def lies_shops(s):
    import html as _html
    from basis import merkmale_aus_text
    q = quelle_anlegen(s, "shops", "Produktlisten von Tastatur-Shops (Shopify)", None)
    anzahl = 0
    for datei in sorted((QUELLEN / "shops").glob("*.json")):
        d = json.loads(datei.read_text(encoding="utf-8"))
        shop, zeitpunkt = d["shop"], d["abgerufen"]
        gesehen = {}
        for p in d["produkte"]:
            titel = p.get("title") or ""
            typ = p.get("product_type") or ""
            tags = p.get("tags") or []
            tags = tags if isinstance(tags, list) else [t.strip() for t in str(tags).split(",")]
            kopf = f"{titel} | {typ}"
            if SHOP_AUSSCHLUSS.search(kopf) or not SHOP_EINSCHLUSS.search(f"{kopf} | {' '.join(tags)}"):
                continue
            koerper = _html.unescape(re.sub(r"<[^>]+>", " ", p.get("body_html") or ""))
            if shop not in ERGO_SHOPS and not ERGO_TEXT.search(f"{kopf} | {' '.join(tags)} | {koerper[:3000]}"):
                continue
            schluessel = _titel_schluessel(titel)
            if schluessel in gesehen:
                gesehen[schluessel] += 1
                continue
            gesehen[schluessel] = 1
            optionen = {o.get("name", ""): o.get("values", []) for o in p.get("options") or []}
            preise = [float(v["price"]) for v in p.get("variants") or [] if v.get("price") not in (None, "")]
            url = f"https://{shop}/products/{p['handle']}"
            ds = s.datensatz("shops", f"{shop}/{p['handle']}", url, q["lizenz"], zeitpunkt, titel, p.get("vendor"),
                             url, [], {"shop": shop, "typ": typ, "tags": tags, "optionen": optionen,
                                       "preis_min": min(preise) if preise else None,
                                       "preis_max": max(preise) if preise else None,
                                       "erstellt": p.get("created_at"), "geaendert": p.get("updated_at")})
            text = " | ".join([titel, typ, " ".join(tags), " ".join(f"{k}: {', '.join(v)}" for k, v in optionen.items()),
                               koerper])
            for facette, wert, fund in merkmale_aus_text(text):
                s.angabe(ds, facette, wert, "quelle", f"Shop-Text: …{fund}…")
            if preise and min(preise) > 0:
                s.angabe(ds, "preis", f"{min(preise):.2f} (Shopwährung {shop})", "quelle", "Variantenpreis")
            if re.search(r"\bkit\b|diy|barebone", text, re.I):
                s.angabe(ds, "verfuegbarkeit", "kit", "quelle", "Shop-Text: kit/DIY/barebone")
            if re.search(r"pre-?built|assembled|fully built", text, re.I):
                s.angabe(ds, "verfuegbarkeit", "fertig", "quelle", "Shop-Text: prebuilt/assembled")
            for name, werte in optionen.items():
                if re.search(r"case|colou?r", name, re.I) and not re.search(r"keycap|cable|switch", name, re.I):
                    for w in werte:
                        s.angabe(ds, "gehaeusefarbe", w.strip().lower()[:30], "quelle", f"Variante {name}")
                if re.search(r"keycap", name, re.I):
                    for w in werte:
                        s.angabe(ds, "keycap_farbe", w.strip().lower()[:30], "quelle", f"Variante {name}")
                if re.search(r"layout|language", name, re.I):
                    for w in werte:
                        s.angabe(ds, "sprachlayout", w.strip().lower()[:30], "quelle", f"Variante {name}")
            anzahl += 1
    return anzahl, []


# ----------------------------------------------------------------------------- Shops ohne Schnittstelle (Produktseiten)
HERSTELLER_SEITEN = {"r-go-tools.de"}   # Herstellerseiten ohne eigenen Warenkorb
WARENKORB = re.compile(r"in den warenkorb|add to cart|add-to-cart|addtocart|jetzt kaufen|buy now", re.I)
TASTATUR_TITEL = re.compile(r"tastatur|keyboard|\bkeeb|split|corne|sofle|lily|piantor|kinesis|advantage|ergodox|moonlander|"
                            r"voyager|glove80|dygma|uhk|svalboard|keyboardio|r-go|ergo\b", re.I)
ZUBEHOER_TITEL = re.compile(r"tastenkappe|keycap|handballenauflage|palm|pads?\b|kabel|cable|adapter|ersatz|replacement|"
                            r"\bmaus\b|mouse|fußstütze|laptopständer|tasche|case\b|hülle|schalter\b|switch(?:es)?\b|"
                            r"tenting kit|kit für|software|treiber|driver", re.I)


def lies_shopseiten(s):
    import html as _html
    from basis import merkmale_aus_text
    q = quelle_anlegen(s, "shopseiten", "Produktseiten von Shops und Herstellern ohne Produkt-Schnittstelle", None)
    anzahl = 0
    for index_datei in sorted((QUELLEN / "shopseiten").glob("*/index.json")):
        site = index_datei.parent.name
        for url, eintrag in sorted(json.loads(index_datei.read_text(encoding="utf-8")).items()):
            h = (index_datei.parent / eintrag["datei"]).read_text(encoding="utf-8", errors="replace")
            titel = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', h) or \
                re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
            titel = _html.unescape(re.sub(r"<[^>]+>", " ", titel.group(1))).strip() if titel else ""
            titel = re.sub(r"\s*[|–-]\s*(bueroleben|keebart|zenlap|r-go tools).*$", "", titel, flags=re.I).strip()
            hersteller_seite = site in HERSTELLER_SEITEN
            if not titel or not (hersteller_seite or WARENKORB.search(h)) or not TASTATUR_TITEL.search(titel) \
                    or ZUBEHOER_TITEL.search(titel):
                continue
            inhalt = re.sub(r"(?s)<(script|style|noscript|svg|nav|header|footer|aside)[^>]*>.*?</\1>", " ", h)
            m = re.search(r"(?s)<main[^>]*>(.*?)</main>", inhalt)
            inhalt = m.group(1) if m else inhalt
            text = " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", inhalt)).split())
            preis = re.search(r'(?:product:price:amount|itemprop="price")[^>]*content="([0-9.,]+)"', h)
            ds = s.datensatz("shopseiten", url, url, q["lizenz"], eintrag["abgerufen"], titel, None, url, [],
                             {"site": site, "preis": preis.group(1) if preis else None})
            for facette, wert, fund in merkmale_aus_text(f"{titel} | {text[:20000]}"):
                s.angabe(ds, facette, wert, "quelle", f"Seitentext: …{fund}…")
            if preis:
                s.angabe(ds, "preis", f"{preis.group(1)} EUR", "quelle", "Preisangabe der Seite")
            s.angabe(ds, "verfuegbarkeit", "fertig", "abgeleitet",
                     "Herstellerseite" if hersteller_seite else "Produktseite mit Warenkorb")
            anzahl += 1
    return anzahl, []


# ----------------------------------------------------------------------------- Listen: Keebfolio, Aposymbiont, awesome-*
def lies_keebfolio(s):
    from basis import merkmale_aus_text
    wurzel = QUELLEN / "keebfolio"
    commit, datum = git_stand(wurzel)
    q = quelle_anlegen(s, "keebfolio", "Keebfolio: Open-Source-Tastaturen (Keycapsss/awesome-mechanical-keyboard)",
                       f"{commit} {datum}", commit)
    anzahl = 0
    for f in sorted((wurzel / "src" / "content" / "keyboards").glob("**/*.md")):
        m = re.match(r"---\n(.*?)\n---", f.read_text(encoding="utf-8"), re.S)
        d = yaml.safe_load(m.group(1)) if m else None
        if not d or not d.get("name"):
            continue
        rel = f.relative_to(wurzel).as_posix()
        ds = s.datensatz("keebfolio", rel, github_blob(q["url"], commit, rel), q["lizenz"], datum, str(d["name"]),
                         None, d.get("url"), [], {"kategorie": d.get("category"), "tags": d.get("tags")})
        kat, tags = d.get("category") or "", str(d.get("tags") or "")
        if kat == "split":
            s.angabe(ds, "geteilt", "ja", "quelle", "category: split")
        if kat == "ortholinear":
            s.angabe(ds, "versatz", "ortho", "quelle", "category: ortholinear")
        s.angabe(ds, "open_source_hardware", "ja", "abgeleitet", "Liste von Open-Source-Tastaturen")
        s.angabe(ds, "verfuegbarkeit", "selbstbau", "abgeleitet", "Liste von Open-Source-Tastaturen")
        for facette, wert, fund in merkmale_aus_text(tags):
            s.angabe(ds, facette, wert, "quelle", f"tags: {tags[:100]}")
        r = re.search(r"\b([2-6])x([4-8])\b", tags)
        if r:
            s.angabe(ds, "raster", f"{r.group(1)}x{r.group(2)}", "quelle", f"tags: {tags[:100]}")
        anzahl += 1
    return anzahl, []


APO_VERSATZ = {"ergo": "spalten", "ortho": "ortho", "traditional": "reihen", "dish": "mulde"}
APO_BEZUG = {"kit": "kit", "source": "selbstbau", "massproduced": "fertig", "unavailable": "eingestellt",
             "prebuilt": "fertig", "gb": "gruppenbestellung"}


def lies_aposymbiont(s):
    wurzel = QUELLEN / "aposymbiont"
    commit, datum = git_stand(wurzel)
    q = quelle_anlegen(s, "aposymbiont", "Aposymbiont Split Keyboards Gallery (auf Basis von diimdeep)",
                       f"{commit} {datum}", commit)
    anzahl = 0
    for datei in ("ergo.csv", "ortho.csv", "dish.csv", "traditional.csv", "other.csv"):
        with open(wurzel / datei, encoding="utf-8") as f:
            for zeile_nr, z in enumerate(csv.DictReader(f), start=2):
                if not z.get("Name"):
                    continue
                url = github_blob(q["url"], commit, datei) + f"#L{zeile_nr}"
                ds = s.datensatz("aposymbiont", f"{datei}#{z['Name']}", url, q["lizenz"], datum, z["Name"], None,
                                 z.get("Website") or None, [], {k: v for k, v in z.items() if k != "Image"})

                def a(f_, w, feld):
                    s.angabe(ds, f_, w, "quelle", f"{feld}: {z.get(feld)}")

                merkmale = (z.get("Features") or "").split()
                if "split" in merkmale:
                    a("geteilt", "ja", "Features")
                elif "single" in merkmale and z.get("Layout") in ("ergo", "dish", "traditional"):
                    a("geteilt", "einteilig-geteilt", "Features")
                if "wireless" in merkmale:
                    a("drahtlos", "ja", "Features")
                if "track" in merkmale:
                    a("maus", "ja", "Features")
                if "display" in merkmale:
                    a("display", "ja", "Features")
                for teil in (z.get("Layout") or "").split():
                    if teil in APO_VERSATZ:
                        a("versatz", APO_VERSATZ[teil], "Layout")
                for teil in (z.get("Availability") or "").split():
                    if teil in APO_BEZUG:
                        a("verfuegbarkeit", APO_BEZUG[teil], "Availability")
                for feld in ("MinKeys", "MaxKeys"):
                    if (z.get(feld) or "").isdigit() and int(z[feld]) > 1:
                        a("tasten", int(z[feld]), feld)
                anzahl += 1
    return anzahl, []


def lies_awesome_listen(s):
    """awesome-split-keyboards (Abschnitt je Tastatur) und awesome-dactyl (Aufzählung je Projekt): nur Name und Link."""
    anzahl = 0
    for qid, beschreibung in (("awesome-split", "awesome-split-keyboards (diimdeep)"),
                              ("awesome-dactyl", "awesome-dactyl (PotHix)")):
        wurzel = QUELLEN / qid
        if not wurzel.exists():
            continue
        commit, datum = git_stand(wurzel)
        q = quelle_anlegen(s, qid, beschreibung, f"{commit} {datum}", commit)
        zeilen = (wurzel / "README.md").read_text(encoding="utf-8").splitlines()
        if qid == "awesome-split":
            abschnitt = None
            for nr, z in enumerate(zeilen, 1):
                m = re.match(r"^## (.+)$", z)
                if m:
                    abschnitt = (m.group(1).strip(), nr, [])
                    if re.search(r"build your own|diy|plates|switch|keycap|typing|contribut|license|community|ergonomics|information|more split|shopping|resources|related", abschnitt[0], re.I):
                        abschnitt = None
                        continue
                    ds_url = github_blob(q["url"], commit, "README.md") + f"#L{nr}"
                    links = []
                    for z2 in zeilen[nr:nr + 15]:
                        if z2.startswith("## "):
                            break
                        links += re.findall(r"https?://[^\s)\]\"'>]+", z2)
                    links = [l for l in links if not re.search(r"\.(png|jpe?g|gif)$", l, re.I)]
                    s.datensatz(qid, abschnitt[0], ds_url, q["lizenz"], datum, abschnitt[0], None,
                                links[0] if links else None, links[1:6], {})
                    anzahl += 1
        else:
            for nr, z in enumerate(zeilen, 1):
                m = re.match(r"^\* \[([^\]:]+)(?::[^\]]*)?\]\((https?://[^)]+)\)", z)
                if m and not re.search(r"video|tutorial|guide|build log", m.group(1), re.I):
                    ds = s.datensatz(qid, m.group(1).strip(), github_blob(q["url"], commit, "README.md") + f"#L{nr}",
                                     q["lizenz"], datum, m.group(1).strip(), None, m.group(2), [], {})
                    s.angabe(ds, "versatz", "mulde", "abgeleitet", "Liste von Dactyl-ähnlichen (gewölbten) Tastaturen")
                    anzahl += 1
    return anzahl, []
