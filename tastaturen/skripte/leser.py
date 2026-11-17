"""Leser je Quelle. Jeder Leser legt die Quelle an, schreibt je Tastatur einen Datensatz mit genauer Fundstelle und
übersetzt die Angaben der Quelle in Facetten (tastaturen/facetten.json). Jede Facetten-Angabe nennt ihren Beleg."""

import csv
import datetime
import html
import json
import re

import yaml

from basis import QUELLEN, ORDNER, git_stand, github_blob, json_tolerant, manifest, tief_mischen

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
        roh = {k: daten[k] for k in ("community_layouts", "layout_aliases", "features", "processor") if k in daten}
        ds = s.datensatz(qid, rel.as_posix(), urls[-1] if urls else None, q["lizenz"], datum,
                         daten.get("keyboard_name") or rel.parts[-1], daten.get("manufacturer"),
                         daten.get("url") or None, urls[:-1], roh)
        s.angabe(ds, "firmware", "qmk" if qid == "qmk" else "vial", "quelle", f"{qid}-Repository")
        if qid == "vial":
            s.angabe(ds, "firmware", "qmk", "abgeleitet", "Vial ist ein QMK-Fork")
        if (daten.get("split") or {}).get("enabled"):
            s.angabe(ds, "geteilt", "ja", "quelle", "split.enabled = true")
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
        ds = s.datensatz("manuell", t["name"], belege[0] if belege else t.get("url"), q["lizenz"], daten.get("stand"),
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
                         "unbekannt (keine Lizenz im Repository erkannt)", abruf, r.get("name"),
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
