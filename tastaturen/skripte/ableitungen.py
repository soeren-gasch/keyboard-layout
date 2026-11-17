"""Abgeleitete Angaben, die keine Quelle ausdrücklich nennt, aber aus belegten Daten folgen.

Läuft nach allen Lesern und vor dem Zusammenführen. Jede Ableitung wird als Angabe mit methode = 'abgeleitet' am
Datensatz gespeichert, aus dem sie folgt, samt Regel als Beleg. Beim Verdichten verliert eine abgeleitete Angabe
immer gegen eine belegte (zusammenfuehren.verdichten).

Geteilt = nein („One piece“). Quellen nennen fast nie ausdrücklich, dass eine Tastatur nicht geteilt ist; ohne diese
Regeln stünden rund 6.600 Geräte auf „unbekannt“, meist gewöhnliche 60-%-, 65-%- oder Numpad-Boards.
  1. Firmware-Definition (QMK, Vial, ZMK, VIA) ohne Split-Angabe, und jedes Layout des Datensatzes
     - hat keine Lücke zwischen zwei Hälften (basis.ableiten, geteilt_geometrisch = 0),
     - hat keine gedrehten Tasten,
     - ist reihenversetzt oder ortholinear (oder hat höchstens 24 Tasten, Makropad),
     - hat in weniger als der Hälfte der Reihen eine Lücke >= 0,4 u im mittleren Drittel (sonst evtl. Unibody mit
       getrenntem Tastenfeld);
     und der Name klingt nicht nach Split/Ergo.
     Geprüft am 17.11.2026 gegen 2.173 Geräte mit belegter Split-Angabe: 18 (0,8 %) hätten fälschlich „nein“ bekommen,
     fast alle Unibodys mit getrenntem Tastenfeld.
  2. Deskthority-Infobox: `layouts` nennt nur Standardanordnungen (ANSI, ISO, JIS, Asian 101, F AT …).
     Ergonomische Tastaturen stehen dort als „Modified …“, „Custom“ oder „Proprietary“.
"""

import json
import re
from collections import defaultdict

SPLIT_NAME = re.compile(r"split(?![ _-]?(space|backspace|bar|shift|enter))|ergo|natural|dactyl|alice|atreus|unibody|"
                        r"wedge|arisu|tent|kinesis|maltron|comfort|adjustable|wing|butterfly", re.I)
STANDARD_LAYOUTS = re.compile(
    r"^(\d{2,3}[- ]key |\d{2,3}/\d{2,3}-key |60% |65% |75% |TKL |full[- ]size )?(ANSI|ISO|JIS|Asian 10[12]|F AT|F XT|"
    r"Japanese|OADG ?106)( ?(,|/|or|and) ?(\d{2,3}[- ]key )?(ANSI|ISO|JIS|Asian 10[12]|Japanese))*$", re.I)
FIRMWARE = ("qmk", "vial", "zmk", "via")


def mittel_luecke(tasten):
    """Anteil der Reihen (mit mindestens 4 Tasten), die zwischen 30 % und 70 % der Breite eine Lücke >= 0,4 u haben."""
    if not tasten:
        return 0.0
    x0 = min(x for x, _, _, _ in tasten)
    x1 = max(x + w for x, _, w, _ in tasten)
    breite = x1 - x0
    reihen = defaultdict(list)
    for x, y, w, h in tasten:
        reihen[round((y + h / 2) * 2) / 2].append((x, w))
    n = treffer = 0
    for r in reihen.values():
        if len(r) < 4:
            continue
        n += 1
        r.sort()
        for (a, wa), (b, _) in zip(r, r[1:]):
            if b - (a + wa) >= 0.4 and x0 + 0.3 * breite <= (a + wa + b) / 2 <= x0 + 0.7 * breite:
                treffer += 1
                break
    return treffer / n if n else 0.0


def geteilt_ableiten(db):
    eigen = {ds for (ds,) in db.execute("SELECT DISTINCT datensatz_id FROM angabe WHERE facette = 'geteilt'")}
    layouts = defaultdict(list)
    for lid, ds, geo, rot, versatz, n in db.execute(
            "SELECT id, datensatz_id, geteilt_geometrisch, rotiert, versatz, tasten FROM layout"):
        layouts[ds].append((lid, geo, rot, versatz, n))
    tasten = defaultdict(list)
    for lid, x, y, w, h in db.execute("SELECT layout_id, x, y, w, h FROM taste WHERE r = 0 OR r IS NULL"):
        tasten[lid].append((x, y, w, h))
    neu = []
    for ds, quelle, name, roh in db.execute("SELECT id, quelle, name, roh FROM datensatz"):
        if ds in eigen or SPLIT_NAME.search(name or ""):
            continue
        if quelle in FIRMWARE and layouts.get(ds):
            ok = all(geo == 0 and not rot and (versatz in ("reihen", "ortho") or (versatz is None and n <= 24))
                     and mittel_luecke(tasten[lid]) < 0.5 for lid, geo, rot, versatz, n in layouts[ds])
            if ok:
                art = "split.enabled fehlt" if quelle in ("qmk", "vial") else \
                    "keine Hälften (siblings)" if quelle == "zmk" else "nur KLE-Layout"
                neu.append((ds, "geteilt", "nein", "abgeleitet",
                            f"Firmware-Definition ohne Split-Angabe ({art}); alle {len(layouts[ds])} Layouts ohne Lücke "
                            f"zwischen Hälften, ohne gedrehte Tasten, reihenversetzt/ortholinear", None))
        elif quelle == "deskthority":
            r = json.loads(roh or "{}")
            v = str((r.get("infobox") or r).get("layouts", "")).strip()
            if v and STANDARD_LAYOUTS.match(v):
                neu.append((ds, "geteilt", "nein", "abgeleitet", f"Deskthority layouts: {v} (Standardanordnung)", None))
    db.executemany("INSERT INTO angabe VALUES (?,?,?,?,?,?)", neu)
    return len(neu)
