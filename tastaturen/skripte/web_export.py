"""Exportiert die Datenbank für die geplante Online-Seite (Facettensuche) und als CSV-Übersichten.

export/web/devices.json     (englisch) ein Eintrag je Gerät: Name, Hersteller, Facetten, Konflikte, Fundstellen mit
                            Lizenz, Links
export/web/layouts.json     Hauptlayout je Gerät: Tasten als [x, y, w, h, r, rx, ry] (KLE-Konvention, Tasten-Einheiten)
export/web/facets.json      Filter-Vokabular (englisch) mit Anzahl Geräte je Wert
export/web/sources.json     alle Quellen mit Stand, Lizenz, Lizenztext, Nutzung und Nennung (englisch)
export/geraete.csv          Übersicht je Gerät (diff-bar)
export/datensaetze.csv      Übersicht je Datensatz mit Fundstelle und Lizenz
export/layouts.csv          Übersicht je Layout
Nicht exportiert werden Rohdaten der Quellen (Spalte datensatz.roh), insbesondere keine Texte aus golem.hu oder
KBD.news.
"""

import csv
import json
from collections import Counter, defaultdict

from basis import EXPORT, ORDNER


def schreibe_json(pfad, daten):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(daten, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


REGELN_EN = {"anker": "anchor", "familie": "qmk-family", "manuell": "manual"}


def regel_en(r):
    if r in REGELN_EN:
        return REGELN_EN[r]
    art, _, rest = r.partition(" ")
    return {"repo": "repository", "name": "name"}.get(art, art) + (f" {rest}" if rest else "")


def exportieren(db, erzeugt_am):
    """Web-Export auf Englisch: Schlüssel und Werte aus facetten.json ('key'), Quellenbeschreibungen aus quellen.json
    ('*_en'). Die interne Datenbank bleibt deutsch."""
    web = EXPORT / "web"
    vokabular = json.loads((ORDNER / "facetten.json").read_text(encoding="utf-8"))
    fkey = {f["id"]: f["key"] for f in vokabular["facetten"]}
    vkey = {f["id"]: {w["id"]: w["key"] for w in f["werte"]} if isinstance(f.get("werte"), list) else {}
            for f in vokabular["facetten"]}
    manifest = json.loads((ORDNER / "quellen.json").read_text(encoding="utf-8"))["quellen"]

    def wert_en(f, w):
        if isinstance(w, list):
            return [vkey[f].get(x, x) for x in w]
        if isinstance(w, dict):
            return w
        return vkey[f].get(w, w)

    def facetten_en(fac):
        return {fkey.get(f, f): wert_en(f, w) for f, w in fac.items()}

    quellen = []
    for z in db.execute("SELECT id, name, url, stand, lizenz, lizenz_url, nennung FROM quelle"):
        q = manifest.get(z[0], {})
        quellen.append({"id": z[0], "name": z[1], "url": z[2], "version": z[3], "license": z[4], "license_url": z[5],
                        "attribution": z[6], "description": q.get("beschreibung_en"), "usage": q.get("nutzung_en")})
    ds_info = {}
    for z in db.execute("SELECT id, quelle, quell_id, quell_url, lizenz, abgerufen, name, url FROM datensatz"):
        ds_info[z[0]] = {"quelle": z[1], "quell_id": z[2], "fundstelle": z[3], "lizenz": z[4], "abgerufen": z[5],
                         "name": z[6], "url": z[7]}
    zuordnung = defaultdict(list)
    for gid, ds, regel in db.execute("SELECT geraet_id, datensatz_id, regel FROM geraet_datensatz"):
        zuordnung[gid].append((ds, regel))

    geraete, layout_ids, geraete_intern = [], set(), []
    for gid, slug, name, hersteller, fac, konf, abg, lid in db.execute(
            "SELECT id, slug, name, hersteller, facetten, konflikte, abgeleitet, haupt_layout FROM geraet ORDER BY slug"):
        eintraege = []
        for ds, regel in zuordnung[gid]:
            i = ds_info[ds]
            eintraege.append({"source": i["quelle"], "name": i["name"], "location": i["fundstelle"],
                              "license": i["lizenz"], "retrieved": i["abgerufen"], "matched_by": regel_en(regel)})
        links = sorted({ds_info[ds]["url"] for ds, _ in zuordnung[gid] if ds_info[ds]["url"]})
        fac, konf = json.loads(fac), json.loads(konf)
        geraete_intern.append({"id": slug, "name": name, "hersteller": hersteller, "facetten": fac,
                               "konflikte": konf, "quellen": [{"quelle": e["source"]} for e in eintraege]})
        geraete.append({"id": slug, "name": name, "maker": hersteller, "facets": facetten_en(fac),
                        "conflicts": facetten_en(konf), "derived": [fkey.get(f, f) for f in json.loads(abg or "[]")],
                        "sources": eintraege, "links": links, "layout": lid})
        if lid:
            layout_ids.add(lid)

    layouts = {}
    for lid in sorted(layout_ids):
        name, = db.execute("SELECT name FROM layout WHERE id = ?", (lid,)).fetchone()
        tasten = [[round(v, 4) for v in z] for z in
                  db.execute("SELECT x, y, w, h, r, rx, ry FROM taste WHERE layout_id = ? ORDER BY idx", (lid,))]
        layouts[str(lid)] = {"name": name, "keys": tasten}

    zaehler = defaultdict(Counter)
    for g in geraete_intern:
        for f, w in g["facetten"].items():
            if isinstance(w, list):
                zaehler[f].update(w)
            elif isinstance(w, dict):
                zaehler[f].update(range(w["min"], w["max"] + 1))
            else:
                zaehler[f][w] += 1
    typen = {"auswahl": "single", "mehrfach": "multi", "ganzzahl": "range", "jahr": "year", "text": "text"}
    facetten_web = []
    for f in vokabular["facetten"]:
        eintrag = {"key": f["key"], "label": f["en"], "type": typen[f["typ"]],
                   "devices": sum(1 for g in geraete_intern if f["id"] in g["facetten"])}
        if isinstance(f.get("werte"), list):
            eintrag["values"] = [{"key": w["key"], "label": w["en"], "devices": zaehler[f["id"]].get(w["id"], 0)}
                                 for w in f["werte"]]
        else:
            eintrag["counts"] = {str(k): v for k, v in sorted(zaehler[f["id"]].items(), key=lambda kv: str(kv[0]))}
        facetten_web.append(eintrag)

    kopf = {"generator": "tastaturen/skripte/datenbank_bauen.py", "generated": erzeugt_am,
            "note": "Every value comes from the locations listed under 'sources'; license per location. "
                    "A missing facet means unknown, not 'no'."}
    schreibe_json(web / "devices.json", {"meta": kopf, "devices": geraete})
    schreibe_json(web / "layouts.json", {"meta": kopf, "unit": "key unit (1u = 19.05 mm)",
                                         "key_format": ["x", "y", "w", "h", "r", "rx", "ry"], "layouts": layouts})
    schreibe_json(web / "facets.json", {"meta": kopf, "facets": facetten_web})
    schreibe_json(web / "sources.json", {"meta": kopf, "sources": quellen})
    geraete = geraete_intern

    # CSV-Übersichten
    with open(EXPORT / "geraete.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        spalten = ["geteilt", "tasten", "raster", "daumentasten", "versatz", "schalter", "drahtlos", "maus",
                   "firmware", "verfuegbarkeit", "jahr"]
        w.writerow(["id", "name", "hersteller", "quellen"] + spalten + ["konflikte"])
        for g in geraete:
            fac = g["facetten"]

            def fmt(v):
                if isinstance(v, dict):
                    return f"{v['min']}" if v["min"] == v["max"] else f"{v['min']}-{v['max']}"
                return "|".join(v) if isinstance(v, list) else ("" if v is None else v)

            w.writerow([g["id"], g["name"], g["hersteller"] or "", "|".join(sorted({q["quelle"] for q in g["quellen"]}))]
                       + [fmt(fac.get(s)) for s in spalten] + ["|".join(sorted(g["konflikte"]))])
    abfragen = {
        "datensaetze.csv": "SELECT d.id, d.quelle, d.quell_id, d.name, d.hersteller, d.quell_url, d.lizenz, d.abgerufen, "
                           "g.slug AS geraet FROM datensatz d LEFT JOIN geraet_datensatz gd ON gd.datensatz_id = d.id "
                           "LEFT JOIN geraet g ON g.id = gd.geraet_id ORDER BY d.quelle, d.quell_id",
        "layouts.csv": "SELECT l.id, d.quelle, d.quell_id, d.name AS tastatur, l.name, l.tasten, l.geteilt_geometrisch, "
                       "l.tasten_links, l.tasten_rechts, l.raster_links, l.raster_rechts, l.raster_quelle, l.versatz, "
                       "l.breite, l.hoehe, l.rotiert FROM layout l JOIN datensatz d ON d.id = l.datensatz_id "
                       "ORDER BY d.quelle, d.quell_id, l.name"}
    for datei, sql in abfragen.items():
        cur = db.execute(sql)
        with open(EXPORT / datei, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow([d[0] for d in cur.description])
            w.writerows(cur)
    return len(geraete), len(layouts)
