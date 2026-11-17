"""Leser für KBD.news (Keyboard Builders' Digest).

Je Artikel über eine Tastatur entsteht ein Datensatz. Übernommen werden Titel, Datum, Rubrik, Tags, die Zeilen der
Specs-Liste (nur zum Ableiten von Facetten, nicht zur Veröffentlichung) und die Links unter "Resources". Texte und
Bilder werden nicht übernommen.

Als Tastatur-Artikel gilt: Rubrik Projects, Review oder Keyboard Spotting, oder ein Tag, der eine Bauform beschreibt.
"""

import datetime
import html
import re

from basis import QUELLEN, keycap_profile

RUBRIKEN = {"Projects", "Review", "Keyboard Spotting", "Market"}
BAUFORM_TAGS = {"split", "monoblock", "unibody", "ortho", "ortholinear", "columnar", "keywell", "Alice", "macropad",
                "40%", "60%", "65%", "75%", "TKL", "1800", "full-size", "thumb cluster"}

TAGS = {
    "split": [("geteilt", "ja")], "monoblock": [("geteilt", "einteilig-geteilt")],
    "unibody": [("geteilt", "einteilig-geteilt")], "wireless": [("drahtlos", "ja")],
    "Bluetooth": [("drahtlos", "ja"), ("drahtlos_technik", "bluetooth")],
    "low profile": [("profil", "flach")], "low-profile": [("profil", "flach")],
    "ortho": [("versatz", "ortho")], "ortholinear": [("versatz", "ortho")], "columnar": [("versatz", "spalten")],
    "keywell": [("versatz", "mulde")], "Alice": [("versatz", "alice")],
    "Hall effect": [("schalter", "magnetisch")], "magnetic": [("schalter", "magnetisch")],
    "hotswap": [("schalter_montage", "hotswap")], "hot-swap": [("schalter_montage", "hotswap")],
    "handwired": [("schalter_montage", "geloetet")],
    "trackball": [("maus", "ja"), ("maus_art", "trackball")], "trackpad": [("maus", "ja"), ("maus_art", "trackpad")],
    "trackpoint": [("maus", "ja"), ("maus_art", "trackpoint")], "joystick": [("maus", "ja"), ("maus_art", "joystick")],
    "rotary encoder": [("drehgeber", "ja")], "encoder": [("drehgeber", "ja")],
    "display": [("display", "ja")], "OLED": [("display", "ja")], "tenting": [("zelt", "ja")],
    "solar": [("energie", "solar")], "open source": [("open_source_hardware", "ja")],
    "open-source": [("open_source_hardware", "ja")], "ZMK": [("firmware", "zmk")], "QMK": [("firmware", "qmk")],
    "KMK": [("firmware", "kmk")], "RMK": [("firmware", "rmk")], "Vial": [("firmware", "vial")],
    "Choc": [("schalter", "choc-v1")], "MX": [("schalter", "mx")], "Alps": [("schalter", "alps")],
    "Topre": [("schalter", "topre")], "kit": [("verfuegbarkeit", "kit")], "group buy": [("verfuegbarkeit",
                                                                                         "gruppenbestellung")],
    "prebuilt": [("verfuegbarkeit", "fertig")], "prototype": [("verfuegbarkeit", "prototyp")],
    "splay": [("spreizung", "ja")], "splayed": [("spreizung", "ja")]}

# (Muster, Facette, Wert) für Zeilen der Specs-Liste; "optional" in der Zeile macht ja -> optional
SPECS = [
    (r"\bcolumn(ar|-stagger| stagger)", "versatz", "spalten"), (r"\bortholinear|\bortho\b", "versatz", "ortho"),
    (r"\brow[- ]stagger", "versatz", "reihen"), (r"\bkeywell", "versatz", "mulde"),
    (r"\bsplit\b", "geteilt", "ja"), (r"\b(unibody|monoblock)\b", "geteilt", "einteilig-geteilt"),
    (r"\bchoc v?1\b|\bchoc v1\b|kailh choc(?! v?2)", "schalter", "choc-v1"), (r"\bchoc v?2\b", "schalter", "choc-v2"),
    (r"\bmx\b|cherry mx|mx-style|mx compatible", "schalter", "mx"), (r"gateron (low[- ]profile|ks-?33)", "schalter",
                                                                    "gateron-lp"),
    (r"\balps\b", "schalter", "alps"), (r"hall[- ]effect|magnetic switch", "schalter", "magnetisch"),
    (r"\btopre\b", "schalter", "topre"), (r"hot[- ]?swap", "schalter_montage", "hotswap"),
    (r"\bsolder(ed)?\b", "schalter_montage", "geloetet"),
    (r"\bwireless\b|\bbluetooth\b|\bble\b|nice!nano", "drahtlos", "ja"),
    (r"\bbluetooth\b|\bble\b|nice!nano", "drahtlos_technik", "bluetooth"),
    (r"2\.4 ?ghz|dongle", "drahtlos_technik", "funk-2-4"), (r"\bwired\b(?!ly)", "energie", "kabel"),
    (r"\baaa\b", "energie", "aaa"), (r"\baa\b(?! battery holder)", "energie", "aa"),
    (r"li-?po|lithium|built-in battery|internal battery", "energie", "akku-fest"),
    (r"trackball", "maus_art", "trackball"), (r"trackpad|touchpad|cirque", "maus_art", "trackpad"),
    (r"trackpoint|pointing stick", "maus_art", "trackpoint"), (r"joystick", "maus_art", "joystick"),
    (r"trackball|trackpad|touchpad|cirque|trackpoint|pointing stick|joystick", "maus", "ja"),
    (r"encoder", "drehgeber", "ja"), (r"\boled\b|display|nice!view|e-?ink|screen", "display", "ja"),
    (r"tenting|tent\b", "zelt", "ja"), (r"\bsplay", "spreizung", "ja"), (r"low[- ]profile", "profil", "flach"),
    (r"\bzmk\b", "firmware", "zmk"), (r"\bqmk\b", "firmware", "qmk"), (r"\bkmk\b", "firmware", "kmk"),
    (r"\brmk\b", "firmware", "rmk"), (r"\bvial\b", "firmware", "vial"), (r"\bvia\b", "firmware", "via"),
    (r"open[- ]source", "open_source_hardware", "ja"), (r"\bkit\b", "verfuegbarkeit", "kit"),
    (r"prebuilt|pre-built|assembled", "verfuegbarkeit", "fertig")]

MONATE = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"], 1)}


def text(h):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))).strip()


def artikel_lesen(h, nr):
    titel = re.search(r"<h2 class=focim>(.*?)</h2>", h, re.S)
    rubrik = re.search(r"<h5>.*?<a href=\"column/([^\"]*)\">([^<]*)</a>", h, re.S)
    datum = re.search(r"Published (\w+) (\d{1,2}), (\d{4})", h)
    lead = re.search(r'<p class="cikklead">(.*?)</p>', h, re.S)
    tags_block = re.search(r'<div id="tag">(.*?)</div>', h, re.S)
    slug = re.search(rf'href="/?([A-Za-z0-9_-]+-{nr})\.html', h)
    a = {"nr": nr, "titel": text(titel.group(1)) if titel else None,
         "rubrik": rubrik.group(2) if rubrik else None,
         "datum": datetime.date(int(datum.group(3)), MONATE.get(datum.group(1), 1), int(datum.group(2))).isoformat()
         if datum and datum.group(1) in MONATE else None,
         "tags": [html.unescape(t) for t in re.findall(r">([^<]+)</a>", tags_block.group(1))] if tags_block else [],
         "url": f"https://kbd.news/{slug.group(1)}.html" if slug else f"https://kbd.news/x-{nr}.html",
         "lead": text(lead.group(1)) if lead else None}
    designer = re.findall(r"by <i>([^<]+)</i>", lead.group(1)) if lead else []
    a["designer"] = html.unescape(designer[-1]) if designer else None

    def abschnitt(name):
        m = re.search(rf'id="{name}"[^>]*></a><h2>[^<]*</h2>(.*?)(?=<a id="[a-z]+" href=|<div class="acinfo"|$)', h,
                      re.S)
        return m.group(1) if m else ""

    a["specs"] = [text(li) for li in re.findall(r"<li>(.*?)(?=<li>|</ul>)", abschnitt("specs"), re.S)]
    a["links"] = re.findall(r'href="(https?://[^"]+)"', abschnitt("resources"))
    return a


def ist_tastatur(a):
    return a["rubrik"] in RUBRIKEN or bool(set(a["tags"]) & BAUFORM_TAGS) or \
        any(re.search(r"\d{2,3}[- ]keys?\b", z) for z in a["specs"])


def name_aus_titel(titel):
    return re.sub(r"\s+(review|keyboard|build log|build|v\d+)$", "", titel or "", flags=re.I).strip() or titel


def lies_kbdnews(s, quelle_anlegen):
    ordner = QUELLEN / "kbdnews" / "artikel"
    dateien = sorted(ordner.glob("*.html"), key=lambda p: int(p.stem))
    stand = datetime.date.fromtimestamp(max(f.stat().st_mtime for f in dateien)).isoformat() if dateien else None
    q = quelle_anlegen(s, "kbdnews", "Artikel des Keyboard Builders' Digest seit 2020", f"abgerufen bis {stand}")
    anzahl = 0
    for f in dateien:
        a = artikel_lesen(f.read_text(encoding="utf-8", errors="replace"), int(f.stem))
        if not a["titel"] or not ist_tastatur(a):
            continue
        ds = s.datensatz("kbdnews", str(a["nr"]), a["url"], q["lizenz"], stand, name_aus_titel(a["titel"]),
                         a["designer"], a["links"][0] if a["links"] else None, a["links"],
                         {"titel": a["titel"], "rubrik": a["rubrik"], "datum": a["datum"], "tags": a["tags"],
                          "specs": a["specs"]})
        if a["datum"]:
            s.angabe(ds, "jahr", int(a["datum"][:4]), "abgeleitet", f"Artikel vom {a['datum']} (frühestens)")
        for tag in a["tags"]:
            for facette, wert in TAGS.get(tag, []):
                s.angabe(ds, facette, wert, "quelle", f"Tag: {tag}")
        for zeile in a["specs"]:
            z = zeile.lower()
            for muster, facette, wert in SPECS:
                if re.search(muster, z):
                    w = "optional" if wert == "ja" and "optional" in z and facette in (
                        "drehgeber", "display", "zelt", "maus", "drahtlos") else wert
                    s.angabe(ds, facette, w, "quelle", f"Specs: {zeile[:120]}")
            for von, bis in re.findall(r"(\d{2,3})\s*(?:-|–|to)\s*(\d{2,3})\s*keys?\b", z):
                s.angabe(ds, "tasten", int(von), "quelle", f"Specs: {zeile[:120]}")
                s.angabe(ds, "tasten", int(bis), "quelle", f"Specs: {zeile[:120]}")
            if not re.search(r"\d{2,3}\s*(?:-|–|to)\s*\d{2,3}\s*keys?", z):
                for n in re.findall(r"\b(\d{2,3})[- ]keys?\b", z):
                    s.angabe(ds, "tasten", int(n), "quelle", f"Specs: {zeile[:120]}")
            if "keycap" in z or "profile" in z or " caps" in z:
                for w in keycap_profile(z):
                    s.angabe(ds, "keycap_profil", w, "quelle", f"Specs: {zeile[:120]}")
            m = re.search(r"\b([2-6])\s*x\s*([4-8])\b", z)
            if m:
                s.angabe(ds, "raster", f"{m.group(1)}x{m.group(2)}", "quelle", f"Specs: {zeile[:120]}")
            m = re.search(r"\b(\d)[- ]key thumb|\b(\d) thumb keys", z)
            if m:
                s.angabe(ds, "daumentasten", int(m.group(1) or m.group(2)), "quelle", f"Specs: {zeile[:120]}")
        if not a["specs"]:
            for n in re.findall(r"\b(\d{2,3})-key\b", a["titel"] + " " + (a["lead"] or "")):
                s.angabe(ds, "tasten", int(n), "quelle", "Titel bzw. Vorspann")
        anzahl += 1
    return anzahl, []
