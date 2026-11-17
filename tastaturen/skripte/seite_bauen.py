"""Baut den Entwurf der Online-Seite (englisch) aus export/web/*.json nach tastaturen/web/dist/.

Ziele: mobile first, auch über ein 56k-Modem schnell.
- index.html enthält CSS, Skript, Filterleiste mit Zählungen und die ersten Treffer vorgerendert. Die Seite ist sofort
  lesbar und ohne JavaScript benutzbar.
- idx.<hash>.json ist der kompakte Index für die Facettensuche (Spalten als Base64-Zeichenketten). Er wird nach dem
  ersten Bild geladen; erst Filter brauchen ihn.
- k/<slug>.html je Gerät: eigene Seite mit Tastenbild (SVG), allen Angaben, Links und Fundstellen samt Lizenz.
  Die Liste öffnet sie als Dialog, ohne JavaScript als normale Seite.
- Alle Dateien liegen zusätzlich vorkomprimiert als .gz daneben.

Aufruf: python3 tastaturen/skripte/seite_bauen.py [--noindex]  (danach: python3 tastaturen/web/vorschau.py)
--noindex setzt auf jeder Seite <meta name=robots content="noindex,nofollow"> (Testauftritt).
"""

import gzip
import hashlib
import html
import json
import math
import re
import shutil
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ORDNER = Path(__file__).resolve().parent.parent
WEB, EXP = ORDNER / "web", ORDNER / "export" / "web"
DIST = WEB / "dist"
ESBUILD = Path.home() / "keyboard" / "werkzeuge" / "esbuild"

TITEL = "Keyboard Index"          # Arbeitstitel
AUTOR = "Sören Gasch"
SSR_ZEILEN = 30                   # vorgerenderte Treffer in index.html
LISTE_OBEN = 8                    # Werte, die lange Listen anfangs zeigen
MIN_GERAETE = 8                   # Facetten mit weniger bekannten Werten erscheinen nicht als Filter

# Reihenfolge nach Bedeutung: erst die allgemeinen Merkmale, dann die speziellen (NN/g)
GRUPPEN = [
    ("Shape", ["split", "keys", "keys_per_half", "thumb_keys", "stagger", "splay", "tenting", "positioning",
               "number_row", "numpad", "form_factor", "layout_standard", "grid"]),
    ("Switches & keycaps", ["profile", "switch_interface", "switch_mounting", "keycap_profile", "keycap_material",
                            "legends"]),
    ("Pointing & extras", ["pointing_device", "pointing_device_type", "rotary_encoder", "display", "backlit",
                           "backlight_color", "wrist_rest"]),
    ("Connection & power", ["wireless", "wireless_technology", "connection", "power", "half_link", "battery_mah"]),
    ("Firmware & software", ["firmware", "os", "nkro", "polling_rate_hz"]),
    ("Build & buying", ["availability", "open_source_hardware", "hardware_license", "maker", "material",
                        "mounting_style", "language_layout", "year", "weight_g"]),
    ("Data", ["has_layout"]),
]
OFFEN = {"split", "keys", "stagger"}
PRESETS = {
    "keys": [(0, 36, "≤ 36"), (37, 44, "37–44"), (45, 60, "45–60"), (61, 75, "61–75"), (76, 90, "76–90"),
             (91, 999, "91+")],
    "keys_per_half": [(0, 18, "≤ 18"), (19, 22, "19–22"), (23, 30, "23–30"), (31, 40, "31–40"), (41, 99, "41+")],
    "thumb_keys": [(0, 2, "≤ 2"), (3, 3, "3"), (4, 4, "4"), (5, 6, "5–6"), (7, 99, "7+")],
    "year": [(0, 2015, "≤ 2015"), (2016, 2019, "2016–19"), (2020, 2022, "2020–22"), (2023, 2024, "2023–24"),
             (2025, 2100, "2025+")],
    "weight_g": [(0, 500, "≤ 500 g"), (501, 1000, "501–1000 g"), (1001, 99999, "> 1 kg")],
    "battery_mah": [(0, 500, "≤ 500"), (501, 2000, "501–2000"), (2001, 99999, "> 2000")],
    "polling_rate_hz": [(0, 1000, "≤ 1000"), (1001, 4000, "2000–4000"), (4001, 99999, "8000+")],
}
# Schnellfilter oben (Baymard: wichtige Filter hervorheben); mehrere Werte = alle setzen
SCHNELL = [("Split", "split", "yes"), ("Column stagger", "stagger", "column"),
           ("Ortholinear", "stagger", "ortholinear"), ("Wireless", "wireless", "yes optional"),
           ("Low profile", "profile", "low-profile"), ("Hot-swap", "switch_mounting", "hot-swap"),
           ("Pointing device", "pointing_device", "yes optional"), ("Buy prebuilt", "availability", "prebuilt"),
           ("Open source", "open_source_hardware", "yes"), ("Layout preview", "has_layout", "yes")]
SPLIT_KURZ = {"yes": "Split", "snap-together": "Snap-together split", "unibody-split": "Unibody split",
              "no": "One piece"}
# kurze Beschriftungen für Filter und Chips; die Detailseiten zeigen die ausführlichen aus facets.json
FACETTE_KURZ = {"split": "Split", "keys": "Keys", "grid": "Grid per hand", "thumb_keys": "Thumb keys per hand",
                "stagger": "Stagger", "splay": "Splayed columns", "pointing_device": "Pointing device",
                "pointing_device_type": "Pointing type", "switch_interface": "Switches", "keycap_profile": "Keycap profile",
                "wireless_technology": "Wireless tech", "open_source_hardware": "Open-source hardware", "maker": "Maker",
                "nkro": "NKRO", "material": "Case material", "polling_rate_hz": "Polling rate (Hz)",
                "battery_mah": "Battery (mAh)", "weight_g": "Weight (g)", "language_layout": "Language layouts",
                "os": "OS", "half_link": "Link between halves", "has_layout": "Layout preview"}
WERT_KURZ = {"split": {"unibody-split": "Unibody split"}, "wrist_rest": {"included-separate": "Included"},
             "keycap_profile": {"other-low-profile": "Other low-profile", "proprietary": "Maker-specific"},
             "form_factor": {"30": "≤ 30%"}, "material": {"leather": "Leather"},
             "switch_interface": {"mx": "MX", "choc-v1": "Choc v1", "choc-v2": "Choc v2", "gateron-lp": "Gateron LP",
                                  "alps": "Alps", "topre": "Topre/EC", "hall-effect": "Hall effect",
                                  "membrane": "Rubber dome"}}


def kurz(text):
    """'yes, two separate halves' -> 'Yes'; 'wired (USB)' -> 'Wired'"""
    t = re.split(r" \(|, ", str(text))[0]
    return t[:1].upper() + t[1:]


SORTIERUNG = [("rel", "Best documented"), ("name", "Name"), ("keys", "Fewest keys"), ("keys-desc", "Most keys"),
              ("year", "Newest")]
QUELLE_NAME = {}
# Index-Stufe A (zuerst geladen): Tastaturen mit mehreren Quellen oder aus kuratierten Ergo-Listen.
# Stufe B: nur aus einer einzigen sonstigen Quelle bekannt (Firmware-Repos, Wikis, Shops, News, GitHub …).
KURATIERT = {"yal", "splitkbcompare", "golem", "manuell", "aposymbiont", "keebfolio", "awesome-split", "awesome-dactyl"}

e = html.escape


def gz(pfad):
    daten = pfad.read_bytes()
    pfad.with_name(pfad.name + ".gz").write_bytes(gzip.compress(daten, 9, mtime=0))


def minify(text, loader):
    try:
        r = subprocess.run(["bash", "-lc", f"npx --no-install esbuild --minify --loader={loader}"], cwd=ESBUILD,
                           input=text, capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            return r.stdout.strip()
        print("esbuild:", r.stderr[:300])
    except (OSError, subprocess.TimeoutExpired) as fehler:
        print("esbuild nicht verfügbar:", fehler)
    return text


B64 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"


def spalte(werte):
    """Ganzzahlen >= 0 als Base64-Zeichenkette fester Breite."""
    w = max(1, math.ceil(math.log(max(werte) + 1, 64))) if max(werte) > 0 else 1
    while 64 ** w <= max(werte):
        w += 1
    out = []
    for v in werte:
        z = []
        for _ in range(w):
            z.append(B64[v % 64])
            v //= 64
        out.append("".join(reversed(z)))
    return "".join(out), w


def bereich(v):
    if isinstance(v, dict):
        return v["min"], v["max"]
    if isinstance(v, (int, float)):
        return int(v), int(v)
    return None


def text_en(s):
    return re.sub(r"\(Shopwährung ([^)]+)\)", r"(shop currency, \1)", str(s))


def laden():
    voc = {f["key"]: f for f in json.loads((EXP / "facets.json").read_text())["facets"]}
    geraete = json.loads((EXP / "devices.json").read_text())["devices"]
    layouts = json.loads((EXP / "layouts.json").read_text())["layouts"]
    quellen = json.loads((EXP / "sources.json").read_text())["sources"]
    for g in geraete:
        g["facets"]["maker"] = g["maker"] or None
        g["facets"]["has_layout"] = "yes" if g["layout"] else "no"
        g["nq"] = len({q["source"] for q in g["sources"]})
    for g in geraete:
        g["stufe_a"] = g["nq"] >= 2 or bool({q["source"] for q in g["sources"]} & KURATIERT)
    geraete.sort(key=lambda g: (not g["stufe_a"], -g["nq"], g["name"].lower()))
    voc["maker"] = {"key": "maker", "label": "Maker", "type": "single"}
    voc["has_layout"] = {"key": "has_layout", "label": "Layout preview", "type": "single",
                         "values": [{"key": "yes", "label": "Available"}, {"key": "no", "label": "Not available"}]}
    for k, f in voc.items():
        f["kurz"] = FACETTE_KURZ.get(k, f["label"])
        for v in f.get("values", []):
            v["kurz"] = WERT_KURZ.get(k, {}).get(v["key"]) or kurz(v["label"])
    return voc, geraete, layouts, quellen


def facetten_bauen(voc, geraete):
    """Je Filter-Facette: Typ, Werte (Vokabular-Reihenfolge oder nach Häufigkeit), Zählungen, Spalten für den Index."""
    F = []
    for gruppe, schluessel in GRUPPEN:
        for k in schluessel:
            f = voc.get(k)
            if not f or f["type"] == "text":
                continue
            werte_dev = [g["facets"].get(k) for g in geraete]
            bekannt = sum(1 for w in werte_dev if w not in (None, [], ""))
            if bekannt < MIN_GERAETE:
                continue
            if f["type"] in ("range", "year"):
                br = [bereich(w) if w is not None else None for w in werte_dev]
                F.append({"k": k, "t": "r", "label": f["kurz"], "gruppe": gruppe, "bekannt": bekannt, "br": br,
                          "pre": PRESETS.get(k), "min": min(b[0] for b in br if b), "max": max(b[1] for b in br if b)})
                continue
            listen = [tuple(w) if isinstance(w, list) else ((w,) if w not in (None, "") else ()) for w in werte_dev]
            zaehl = Counter(v for t in listen for v in t)
            if f.get("values"):
                werte = [x["key"] for x in f["values"]] + sorted(v for v in zaehl if v not in
                                                                   {x["key"] for x in f["values"]})
                labels = {x["key"]: x["kurz"] for x in f["values"]}
            else:
                werte = sorted(zaehl, key=lambda v: (-zaehl[v], str(v).lower()))
                labels = {}
            F.append({"k": k, "t": "c", "label": f["kurz"], "gruppe": gruppe, "bekannt": bekannt, "werte": werte,
                      "labels": labels, "zaehl": zaehl, "unbekannt": len(geraete) - bekannt, "listen": listen})
    return F


def kodieren(F, geraete, a, b):
    """Index für die Geräte a..b-1: Namen, abweichende Slugs, Quellenzahl, je Facette eine Spalte. Wertelisten nur
    mit den hier vorkommenden Werten (in der globalen Reihenfolge); das Skript vereinigt die Stufen."""
    teil = geraete[a:b]
    idx = {"n": len(teil), "name": [g["name"] for g in teil],
           "sx": {str(i): g["id"] for i, g in enumerate(teil) if slug_js(g["name"]) != g["id"]},
           "src": spalte([min(g["nq"], 63) for g in teil])[0], "f": {}}
    for f in F:
        if f["t"] == "r":
            br = f["br"][a:b]
            if not any(br):
                continue
            o = min(x[0] for x in br if x)
            lo = [x[0] - o + 1 if x else 0 for x in br]
            d = [x[1] - x[0] if x else 0 for x in br]
            c_lo, w = spalte(lo)
            c_d, wd = spalte(d)
            idx["f"][f["k"]] = {"t": "r", "w": w, "lo": c_lo, "wd": wd, "d": c_d, "o": o}
            continue
        listen = f["listen"][a:b]
        benutzt = {v for t in listen for v in t}
        werte = [v for v in f["werte"] if v in benutzt]
        vi = {v: i for i, v in enumerate(werte)}
        if all(len(t) <= 1 for t in listen):
            # einwertig: Code = Wertindex + 1, keine Kombinationstabelle
            c, w = spalte([vi[t[0]] + 1 if t else 0 for t in listen])
            idx["f"][f["k"]] = {"t": "c", "v": werte, "w": w, "c": c}
            continue
        kombis, codes = {(): 0}, []
        for t in listen:
            t = tuple(sorted(vi[v] for v in t))
            codes.append(kombis.setdefault(t, len(kombis)))
        c, w = spalte(codes)
        idx["f"][f["k"]] = {"t": "c", "v": werte, "w": w, "c": c, "k": [list(t) for t in kombis]}
    return idx


def slug_js(name):
    """Wie slug() in app.js; Namen mit Nicht-ASCII-Zeichen gelten immer als Ausnahme (Kleinschreibung kann abweichen)."""
    if not name.isascii():
        return None
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "tastatur"


def zusammenfassung(g, F):
    """Kurzbeschreibung einer Trefferzeile; muss summ() in app.js entsprechen."""
    lab = {f["k"]: f.get("labels", {}) for f in F}
    fac, p = g["facets"], []
    sp = fac.get("split")
    if sp:
        p.append(SPLIT_KURZ.get(sp, lab["split"].get(sp, sp)))
    b = bereich(fac.get("keys")) if fac.get("keys") is not None else None
    if b:
        p.append(f"{b[0] if b[0] == b[1] else f'{b[0]}–{b[1]}'} keys")

    def liste(k):
        w = fac.get(k)
        w = w if isinstance(w, list) else ([w] if w else [])
        return [lab.get(k, {}).get(x, x) for x in w]

    # Reihenfolge wie im Index (Werte-Index), damit Liste und Skript dasselbe zeigen
    def geordnet(k):
        f = next((x for x in F if x["k"] == k), None)
        w = fac.get(k)
        w = w if isinstance(w, list) else ([w] if w else [])
        if f:
            w = sorted(w, key=lambda v: f["werte"].index(v) if v in f["werte"] else 999)
        return [lab.get(k, {}).get(x, x) for x in w]

    if geordnet("stagger"):
        p.append(geordnet("stagger")[0])
    if geordnet("switch_interface"):
        p.append("/".join(geordnet("switch_interface")[:2]))
    if fac.get("wireless") == "yes":
        p.append("Wireless")
    elif fac.get("wireless") == "optional":
        p.append("Wireless optional")
    if geordnet("pointing_device_type"):
        p.append("/".join(geordnet("pointing_device_type")))
    elif fac.get("pointing_device") in ("yes", "optional"):
        p.append("Pointing device")
    if geordnet("firmware"):
        p.append("/".join(geordnet("firmware")[:3]))
    del liste
    return " · ".join(p)


def zeile(g, F):
    m = f" <span>{e(g['maker'])}</span>" if g["maker"] else ""
    return (f'<li><a href="k/{g["id"]}.html" data-s="{g["id"]}"><b>{e(g["name"])}</b>{m}</a>'
            f'<div class=sp>{e(zusammenfassung(g, F))}</div><span class=sc title="Number of sources">'
            f'{min(g["nq"], 63)} src</span></li>')


def fmt(n):
    return f"{n:,}"


def facette_html(f, n):
    k, auf = f["k"], " open" if f["k"] in OFFEN else ""
    kopf = f'<details class=fac data-f="{k}"{auf}><summary>{e(f["label"])} <small></small></summary><div class=fb>'
    fuss = f'<p class=fn>Known for {fmt(f["bekannt"])} of {fmt(n)}.</p></div></details>'
    if f["t"] == "r":
        pre = f.get("pre") or []
        teile = [f'<div class=rg><label>Min<input type=number inputmode=numeric name="{k}" data-b=lo '
                 f'placeholder="{f["min"]}"></label><span>–</span><label>Max<input type=number inputmode=numeric '
                 f'name="{k}" data-b=hi placeholder="{f["max"]}"></label></div>']
        if pre:
            knoepfe = []
            for i, (lo, hi, label) in enumerate(pre):
                anz = sum(1 for b in f["br"] if b and b[1] >= lo and b[0] <= hi)
                knoepfe.append(f'<button type=button class=pill data-f="{k}" data-r={i} aria-pressed=false'
                               f'{" disabled" if not anz else ""}>{e(label)} <i>{fmt(anz)}</i></button>')
            teile.append("<div class=pl>" + "".join(knoepfe) + "</div>")
        teile.append(f'<label class=ck><input type=checkbox name="{k}" value="?"> Include unknown '
                     f'<i>{fmt(n - f["bekannt"])}</i></label>')
        return kopf + "".join(teile) + fuss
    werte, z, lab = f["werte"], f["zaehl"], f["labels"]
    kurz = len(werte) <= 5 and all(len(lab.get(v, v)) <= 16 for v in werte)
    if kurz:
        pills = [f'<label class=pill><input type=checkbox name="{k}" value="{e(v)}"{" disabled" if not z[v] else ""}>'
                 f'<span>{e(lab.get(v, v))} <i>{fmt(z[v])}</i></span></label>' for v in werte]
        pills.append(f'<label class="pill unk"><input type=checkbox name="{k}" value="?"><span>Unknown '
                     f'<i>{fmt(f["unbekannt"])}</i></span></label>')
        return kopf + "<div class=pl>" + "".join(pills) + "</div>" + fuss
    reihe = werte if len(werte) <= LISTE_OBEN else sorted(werte, key=lambda v: -z[v])[:LISTE_OBEN]
    teile = []
    if len(werte) > 15:
        teile.append(f'<input class=fq data-f="{k}" type=search placeholder="Find {e(f["label"].lower())}" '
                     f'aria-label="Find {e(f["label"].lower())}">')
    li = [f'<li><label{" class=off" if not z[v] else ""}><input type=checkbox name="{k}" value="{e(v)}"'
          f'{" disabled" if not z[v] else ""}><span>{e(lab.get(v, v))}</span><i>{fmt(z[v])}</i></label></li>'
          for v in reihe]
    li.append(f'<li><label class=unk><input type=checkbox name="{k}" value="?"><span>Unknown</span>'
              f'<i>{fmt(f["unbekannt"])}</i></label></li>')
    teile.append("<ul class=vl>" + "".join(li) + "</ul>")
    if len(werte) > LISTE_OBEN:
        teile.append(f'<button type=button class=sa data-f="{k}">Show all {fmt(len(werte))}</button>')
    return kopf + "".join(teile) + fuss


THEME_JS = ("<script>try{var t=localStorage.getItem('theme');if(t)document.documentElement.dataset.theme=t}"
            "catch(e){}</script>")
# Klicks, bevor das Skript am Seitenende angekommen ist (56k: gut eine Sekunde), merken und danach abspielen
FRUEH_JS = ("<script>window.Q=[];document.addEventListener('click',function(e){if(window.KB)return;"
            "var t=e.target.closest&&e.target.closest('.qf button,#fb,#mo,#fp button,#fp input[type=checkbox],#ls a[data-s]');"
            "if(t){e.preventDefault();if(Q.indexOf(t)<0)Q.push(t);t.style.opacity=.5}},true)</script>")


def fusszeile(pfad=""):
    return (f'<footer><p>Compiled by {e(AUTOR)} · <strong>Draft, not published yet</strong> · '
            f'<a href="{pfad}about.html">About</a> · <a href="{pfad}sources.html">Sources &amp; licenses</a></p>'
            f'<p>Every value links to the record it comes from. A missing value means unknown, not “no”.</p>'
            f'</footer>')


def seite(titel, inhalt, pfad="", beschreibung=""):
    meta = f'<meta name=description content="{e(beschreibung)}">' if beschreibung else ""
    return (f'<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport '
            f'content="width=device-width,initial-scale=1"><title>{e(titel)}</title>{meta}'
            f'<meta name=color-scheme content="light dark">{THEME_JS}<link rel=stylesheet href="{pfad}s.css">'
            f'<link rel=icon href="data:,"></head><body><header class=top><div class=tb>'
            f'<a class=brand href="{pfad}./">⌨ {TITEL}</a></div></header><main class=page>{inhalt}</main>'
            f'{fusszeile(pfad)}</body></html>')


def svg(lay):
    tasten = lay["keys"]
    pkt = []
    for x, y, w, h, r, rx, ry in tasten:
        a = math.radians(r or 0)
        for px, py in ((x, y), (x + w, y), (x, y + h), (x + w, y + h)):
            dx, dy = px - rx, py - ry
            pkt.append((rx + dx * math.cos(a) - dy * math.sin(a), ry + dx * math.sin(a) + dy * math.cos(a)))
    x0, y0 = min(p[0] for p in pkt), min(p[1] for p in pkt)
    x1, y1 = max(p[0] for p in pkt), max(p[1] for p in pkt)
    f = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")  # noqa: E731
    rects = []
    for x, y, w, h, r, rx, ry in tasten:
        t = f' transform="rotate({f(r)} {f(rx)} {f(ry)})"' if r else ""
        rects.append(f'<rect x="{f(x + .05)}" y="{f(y + .05)}" width="{f(w - .1)}" height="{f(h - .1)}" rx=".12"{t}/>')
    return (f'<svg viewBox="{f(x0 - .1)} {f(y0 - .1)} {f(x1 - x0 + .2)} {f(y1 - y0 + .2)}" role=img '
            f'aria-label="Key layout with {len(tasten)} keys">' + "".join(rects) + "</svg>")


def wert_text(f, v, voc):
    if v is None:
        return ""
    labels = {x["key"]: x["label"] for x in voc.get(f, {}).get("values", [])}
    if isinstance(v, dict):
        return str(v["min"]) if v["min"] == v["max"] else f"{v['min']}–{v['max']}"
    if isinstance(v, list):
        return ", ".join(labels.get(x, str(x)) for x in v)
    return text_en(labels.get(v, v))


def detailseite(g, voc, layouts, lay_info, n_quellen):
    teile = [f'<article><h1>{e(g["name"])}</h1><p class=mk>{e(g["maker"] or "Maker unknown")} · '
             f'{n_quellen} source{"s" if n_quellen != 1 else ""}</p>']
    if g["layout"] and str(g["layout"]) in layouts:
        lay = layouts[str(g["layout"])]
        info = lay_info.get(g["layout"])
        herkunft = ""
        if info:
            herkunft = (f' Positions from <a href="{e(info[2])}">{e(QUELLE_NAME.get(info[0], info[0]))}</a>, '
                        f'license {e(info[1] or "unknown")}.')
        teile.append(f'<figure class=lay>{svg(lay)}<figcaption>Layout “{e(lay["name"])}”, {len(lay["keys"])} keys.'
                     f'{herkunft}</figcaption></figure>')
    teile.append("<h2>Specs</h2><dl class=spec>")
    reihenfolge = [k for _, ks in GRUPPEN for k in ks] + sorted(voc)
    gesehen = set()
    for k in reihenfolge:
        if k in gesehen or k in ("maker", "has_layout") or k not in g["facets"]:
            continue
        gesehen.add(k)
        v = wert_text(k, g["facets"][k], voc)
        if not v:
            continue
        kf = g["conflicts"].get(k)
        konflikt = f'<br><span class=cf>Other sources say: {e(wert_text(k, kf, voc))}</span>' if kf else ""
        teile.append(f"<dt>{e(voc.get(k, {}).get('kurz', k))}</dt><dd>{e(v)}{konflikt}</dd>")
    teile.append("</dl>")
    if g["links"]:
        teile.append("<h2>Links</h2><ul class=links>" + "".join(
            f'<li><a href="{e(u)}" rel="nofollow noopener">{e(urlparse(u).netloc + urlparse(u).path.rstrip("/"))}</a></li>'
            for u in g["links"][:20]) + "</ul>")
    teile.append("<h2>Sources</h2><div class=tw><table><thead><tr><th>Source</th><th>Record</th><th>License</th>"
                 "<th>Retrieved</th></tr></thead><tbody>")
    for q in g["sources"]:
        ort = q["location"] or ""
        kurz = re.sub(r"^https?://(www\.)?", "", ort)
        kurz = kurz if len(kurz) <= 60 else kurz[:28] + "…" + kurz[-28:]
        teile.append(f'<tr><td><a href="../sources.html#{e(q["source"])}">{e(QUELLE_NAME.get(q["source"], q["source"]))}'
                     f'</a></td><td><a href="{e(ort)}" rel=nofollow>{e(kurz)}</a></td><td>{e(q["license"] or "unknown")}'
                     f'</td><td>{e(q["retrieved"] or "")}</td></tr>')
    teile.append("</tbody></table></div><p class=note>Records are merged by firmware family, repository and name. "
                 "Values come only from these records; a missing value means unknown.</p></article>")
    return "".join(teile)


def main():
    global THEME_JS
    if "--noindex" in sys.argv:
        # Testauftritt: Suchmaschinen sollen nichts aufnehmen
        THEME_JS = '<meta name=robots content="noindex,nofollow">' + THEME_JS
    voc, geraete, layouts, quellen = laden()
    for q in quellen:
        QUELLE_NAME[q["id"]] = q["name"]
    F = facetten_bauen(voc, geraete)
    n = len(geraete)
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "k").mkdir(parents=True)

    # Index in zwei Stufen
    na = sum(1 for g in geraete if g["stufe_a"])
    dateien, roh = [], []
    for a, b in ((0, na), (na, n)):
        text = json.dumps(kodieren(F, geraete, a, b), ensure_ascii=False, separators=(",", ":"))
        h = hashlib.sha256(text.encode()).hexdigest()[:10]
        (DIST / f"idx.{h}.json").write_text(text, encoding="utf-8")
        dateien.append(f"idx.{h}.json")
        roh.append(len(text.encode()))

    # Konfiguration für das Skript: Facetten, Bereichsvorgaben, Beschriftungen
    cfg = {"idx": dateien, "raw": roh, "na": na, "n": n,
           "F": [{"k": f["k"], "t": f["t"], **({"pre": [[lo, hi] for lo, hi, _ in f["pre"]]} if f.get("pre") else {})}
                 for f in F],
           "L": {f["k"]: f["labels"] for f in F if f["t"] == "c" and f["labels"]},
           "FL": {f["k"]: f["label"] for f in F}, "SL": SPLIT_KURZ}
    css = minify((WEB / "style.css").read_text(encoding="utf-8"), "css")
    js = minify((WEB / "app.js").read_text(encoding="utf-8"), "js")
    (DIST / "s.css").write_text(css, encoding="utf-8")

    fac_html, gruppe = [], None
    for f in F:
        if f["gruppe"] != gruppe:
            gruppe = f["gruppe"]
            fac_html.append(f"<h3 class=grp>{e(gruppe)}</h3>")
        fac_html.append(facette_html(f, n))
    zaehl = {f["k"]: f.get("zaehl", Counter()) for f in F}
    schnell = "".join(
        f'<button type=button class=pill data-f="{k}" data-v="{v}" aria-pressed=false>{e(t)} '
        f'<i>{fmt(sum(1 for g in geraete if (lambda w: bool(set(w if isinstance(w, list) else [w]) & set(v.split())))(g["facets"].get(k))))}'
        f'</i></button>' for t, k, v in SCHNELL if k in zaehl)
    sortierung = "".join(f'<option value="{k}">{e(t)}</option>' for k, t in SORTIERUNG)
    zeilen = "".join(zeile(g, F) for g in geraete[:SSR_ZEILEN])
    mehr = n - SSR_ZEILEN
    index = (
        f'<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport '
        f'content="width=device-width,initial-scale=1"><title>{TITEL}: split, ergonomic and DIY keyboards</title>'
        f'<meta name=description content="Find split, ergonomic, ortholinear and DIY keyboards. {fmt(n)} keyboards '
        f'from {len(quellen)} sources, every value with its source and license.">'
        f'<meta name=color-scheme content="light dark">{THEME_JS}{FRUEH_JS}<style>{css}</style><link rel=icon href="data:,">'
        f'</head><body><a class=skip href="#fp">Skip to filters</a>'
        f'<header class=top><div class=tb><a class=brand href="./">⌨ {TITEL}</a>'
        f'<button id=th class=btn type=button aria-label="Color theme: auto">◐ Auto</button></div>'
        f'<div class=sr role=search><input id=q type=search placeholder="Search {fmt(n)} keyboards" '
        f'aria-label="Search keyboards by name or maker" autocomplete=off spellcheck=false enterkeyhint=search>'
        f'<button id=fb class=btn type=button aria-controls=fp aria-expanded=false>Filters<b></b></button></div></header>'
        f'<div class=wrap>'
        f'<main id=res><div class=qf role=group aria-label="Quick filters">{schnell}</div>'
        f'<div class=bar><p id=cnt aria-live=polite><b>{fmt(n)}</b> keyboards</p><label class=so>Sort '
        f'<select id=so>{sortierung}</select></label></div><div id=ap></div><ol id=ls>{zeilen}</ol>'
        f'<button id=mo class=btn type=button>Show 50 more</button>'
        f'<noscript><p class=note>Without JavaScript only the {SSR_ZEILEN} keyboards with the most sources are '
        f'listed; {fmt(mehr)} more need the filter script.</p></noscript></main>'
        f'<aside id=fp aria-label=Filters><div class=fph><h2>Filters</h2>'
        f'<button id=fx class=btn type=button aria-label="Close filters">✕</button></div><div class=fpb>'
        f'{"".join(fac_html)}</div><div class=fpf><button id=fc class=btn type=button>Clear</button>'
        f'<button id=fs class="btn pri" type=button>Show {fmt(n)} keyboards</button></div></aside>'
        f'</div>{fusszeile()}'
        f'<dialog id=dv aria-label="Keyboard details"><div class=dvh><button id=dx class=btn type=button>← Back'
        f'</button><a id=dl href="#">Open as page</a></div><div id=dvb></div></dialog>'
        f'<script type=application/json id=cfg>{json.dumps(cfg, ensure_ascii=False, separators=(",", ":"))}</script>'
        f'<script>{js}</script></body></html>')
    (DIST / "index.html").write_text(index, encoding="utf-8")

    # Detailseiten
    db = sqlite3.connect(ORDNER / "tastaturen.sqlite")
    lay_info = {lid: (q, liz, url) for lid, q, liz, url in db.execute(
        "SELECT l.id, d.quelle, d.lizenz, d.quell_url FROM layout l JOIN datensatz d ON d.id = l.datensatz_id")}
    for g in geraete:
        inhalt = detailseite(g, voc, layouts, lay_info, g["nq"])
        (DIST / "k" / f"{g['id']}.html").write_text(
            seite(f"{g['name']} – {TITEL}", inhalt, "../", f"{g['name']}: specs, key layout and sources."),
            encoding="utf-8")

    # Quellen und Über
    zeilen_q = "".join(
        f'<tr id="{e(q["id"])}"><td><a href="{e(q["url"] or "")}">{e(q["name"])}</a><br><span class=note>'
        f'{e(q.get("description") or "")}</span></td><td>{e(q["license"] or "unknown")}</td>'
        f'<td>{e(q.get("usage") or "")}</td><td><code>{e(str(q["version"] or ""))[:40]}</code></td></tr>'
        for q in quellen)
    (DIST / "sources.html").write_text(seite(
        f"Sources and licenses – {TITEL}",
        f'<article><h1>Sources and licenses</h1><p>{len(quellen)} sources. Each record keeps its location, license '
        f'and retrieval date; the keyboard pages list them. Texts and images are not copied, only facts and links.</p>'
        f'<div class=tw><table><thead><tr><th>Source</th><th>License</th><th>What is used</th><th>Version</th>'
        f'</tr></thead><tbody>{zeilen_q}</tbody></table></div></article>'), encoding="utf-8")
    (DIST / "about.html").write_text(seite(
        f"About – {TITEL}",
        f'<article><h1>About</h1><p>{TITEL} lists physical keyboards, with a focus on split, ergonomic, '
        f'ortholinear and DIY designs. It merges {len(quellen)} sources: firmware repositories (QMK, ZMK, Vial, VIA), '
        f'curated lists, wikis, shops, maker pages, Reddit and Ergogen configurations.</p>'
        f'<h2>How the data works</h2><ul class=links><li>Every value comes from a record that is linked on the '
        f'keyboard page, with license and retrieval date.</li><li>Records of the same keyboard are merged by firmware '
        f'family, project repository and name. If sources disagree, the page shows both.</li><li>A missing value means '
        f'unknown, not “no”. Filters can include unknown values.</li><li>Key positions come from firmware definitions '
        f'and Ergogen configurations; 1 u = 19.05 mm.</li></ul>'
        f'<h2>Status</h2><p>This is a draft. Licensing of the compiled data and permissions of some sources are '
        f'still being clarified. Built {date.today().isoformat()} from {fmt(n)} keyboards.</p>'
        f'<h2>Publisher</h2><p>{e(AUTOR)}</p></article>'), encoding="utf-8")

    for p in DIST.rglob("*"):
        if p.is_file() and p.suffix in (".html", ".json", ".css"):
            gz(p)
    groesse = lambda p: (p.stat().st_size, p.with_name(p.name + ".gz").stat().st_size)  # noqa: E731
    print(f"Stufe A: {na} Geräte, Stufe B: {n - na}")
    for name in ["index.html", "s.css"] + dateien:
        roh, kompr = groesse(DIST / name)
        print(f"{name:24} {roh / 1024:8.1f} KB  gzip {kompr / 1024:7.1f} KB")
    det = [groesse(p) for p in (DIST / "k").glob("*.html")]
    print(f"Detailseiten: {len(det)}, Median gzip {sorted(d[1] for d in det)[len(det) // 2] / 1024:.1f} KB, "
          f"max {max(d[1] for d in det) / 1024:.1f} KB")
    print(f"Filter-Facetten: {len(F)}; Geräte: {n}")


if __name__ == "__main__":
    main()
