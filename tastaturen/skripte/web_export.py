"""Exportiert die Datenbank für die geplante Online-Seite (Facettensuche) und als CSV-Übersichten.

export/web/geraete.json     ein Eintrag je Gerät: Name, Hersteller, Facetten, Konflikte, Fundstellen mit Lizenz, Links
export/web/layouts.json     Hauptlayout je Gerät: Tasten als [x, y, w, h, r, rx, ry] (KLE-Konvention, Tasten-Einheiten)
export/web/facetten.json    Vokabular aus tastaturen/facetten.json mit Anzahl Geräte je Wert
export/web/quellen.json     alle Quellen mit Stand, Lizenz, Lizenztext, Nutzung und Nennung
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


def exportieren(db, erzeugt_am):
    web = EXPORT / "web"
    quellen = [dict(zip(["id", "name", "url", "stand", "lizenz", "lizenz_url", "nutzung", "nennung", "beschreibung"],
                        z)) for z in db.execute("SELECT id, name, url, stand, lizenz, lizenz_url, nutzung, nennung, "
                                                "beschreibung FROM quelle")]
    ds_info = {}
    for z in db.execute("SELECT id, quelle, quell_id, quell_url, lizenz, abgerufen, name, url FROM datensatz"):
        ds_info[z[0]] = {"quelle": z[1], "quell_id": z[2], "fundstelle": z[3], "lizenz": z[4], "abgerufen": z[5],
                         "name": z[6], "url": z[7]}
    zuordnung = defaultdict(list)
    for gid, ds, regel in db.execute("SELECT geraet_id, datensatz_id, regel FROM geraet_datensatz"):
        zuordnung[gid].append((ds, regel))

    geraete, layout_ids = [], set()
    for gid, slug, name, hersteller, fac, konf, lid in db.execute(
            "SELECT id, slug, name, hersteller, facetten, konflikte, haupt_layout FROM geraet ORDER BY slug"):
        eintraege = []
        for ds, regel in zuordnung[gid]:
            i = ds_info[ds]
            eintraege.append({"quelle": i["quelle"], "name": i["name"], "fundstelle": i["fundstelle"],
                              "lizenz": i["lizenz"], "abgerufen": i["abgerufen"], "zuordnung": regel})
        links = sorted({ds_info[ds]["url"] for ds, _ in zuordnung[gid] if ds_info[ds]["url"]})
        geraete.append({"id": slug, "name": name, "hersteller": hersteller, "facetten": json.loads(fac),
                        "konflikte": json.loads(konf), "quellen": eintraege, "links": links, "layout": lid})
        if lid:
            layout_ids.add(lid)

    layouts = {}
    for lid in sorted(layout_ids):
        name, = db.execute("SELECT name FROM layout WHERE id = ?", (lid,)).fetchone()
        tasten = [[round(v, 4) for v in z] for z in
                  db.execute("SELECT x, y, w, h, r, rx, ry FROM taste WHERE layout_id = ? ORDER BY idx", (lid,))]
        layouts[str(lid)] = {"name": name, "tasten": tasten}

    vokabular = json.loads((ORDNER / "facetten.json").read_text(encoding="utf-8"))
    zaehler = defaultdict(Counter)
    for g in geraete:
        for f, w in g["facetten"].items():
            if isinstance(w, list):
                zaehler[f].update(w)
            elif isinstance(w, dict):
                zaehler[f].update(range(w["min"], w["max"] + 1))
            else:
                zaehler[f][w] += 1
    for f in vokabular["facetten"]:
        f["anzahl_geraete"] = sum(1 for g in geraete if f["id"] in g["facetten"])
        f["haeufigkeit"] = {str(k): v for k, v in sorted(zaehler[f["id"]].items(), key=lambda kv: str(kv[0]))}

    kopf = {"erzeugt_von": "tastaturen/skripte/datenbank_bauen.py", "erzeugt_am": erzeugt_am,
            "hinweis": "Jede Angabe stammt aus den unter 'quellen' genannten Fundstellen; Lizenz je Fundstelle."}
    schreibe_json(web / "geraete.json", {"kopf": kopf, "geraete": geraete})
    schreibe_json(web / "layouts.json", {"kopf": kopf, "einheit": "Tasten-Einheit (1u)", "layouts": layouts})
    schreibe_json(web / "facetten.json", {"kopf": kopf, **vokabular})
    schreibe_json(web / "quellen.json", {"kopf": kopf, "quellen": quellen})

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
