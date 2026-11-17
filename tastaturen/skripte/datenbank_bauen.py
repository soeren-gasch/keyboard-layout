"""Baut die Tastatur-Datenbank aus den geladenen Quellen.

Aufruf (aus dem Repo-Wurzelverzeichnis), nachdem `tastaturen/skripte/quellen_laden.py` gelaufen ist:
    python3 tastaturen/skripte/datenbank_bauen.py

Eingang:  ~/keyboard/tastatur-quellen/<quelle>/ (Stand je Quelle in tastaturen/quellen.json),
          tastaturen/manuell.json, tastaturen/facetten.json, tastaturen/zusammenfuehrung.json
Ausgang:  tastaturen/tastaturen.sqlite (Schema in skripte/basis.py), tastaturen/export/

Ablauf: Leser je Quelle (Datensätze, Facetten-Angaben mit Beleg, Layouts) -> Zusammenführen zu Geräten -> Export.
"""

import datetime
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from basis import DB, QUELLEN, REPO, SCHEMA, Schreiber  # noqa: E402
import kbdnews  # noqa: E402
import leser  # noqa: E402
from web_export import exportieren  # noqa: E402
from zusammenfuehren import zusammenfuehren  # noqa: E402


def main():
    if DB.exists():
        DB.unlink()
    db = sqlite3.connect(DB)
    db.executescript(SCHEMA)
    s = Schreiber(db)
    bericht = {}
    schritte = [("qmk", leser.lies_qmk), ("vial", leser.lies_vial), ("zmk", leser.lies_zmk),
                ("splitkbcompare", leser.lies_splitkbcompare), ("golem", leser.lies_golem),
                ("kbdnews", lambda s: kbdnews.lies_kbdnews(s, leser.quelle_anlegen)),
                ("yal", leser.lies_yal), ("github", leser.lies_github), ("ergogen", leser.lies_ergogen), ("via", leser.lies_via), ("deskthority", leser.lies_deskthority), ("reddit", leser.lies_reddit), ("shops", leser.lies_shops), ("shopseiten", leser.lies_shopseiten), ("keebfolio", leser.lies_keebfolio),
                ("aposymbiont", leser.lies_aposymbiont), ("awesome-listen", leser.lies_awesome_listen), ("keymapdb", leser.lies_keymapdb), ("manuell", leser.lies_manuell)]
    for name, lies in schritte:
        if name not in ("manuell", "ergogen", "awesome-listen") and not (QUELLEN / name).exists():
            print(f"{name}: Quelle nicht geladen, übersprungen")
            continue
        n, fehler = lies(s)
        bericht[name] = {"datensaetze": n, "fehler": len(fehler)}
        for f in fehler[:5]:
            print(f"  {name}: übersprungen {f[0]}: {f[1]}")
        print(f"{name}: {n} Datensätze, {len(fehler)} Fehler")
    bericht["geraete"] = zusammenfuehren(db)
    heute = datetime.date.today().isoformat()
    for k, v in (("erzeugt_von", "tastaturen/skripte/datenbank_bauen.py"), ("erzeugt_am", heute),
                 ("bericht", json.dumps(bericht, ensure_ascii=False))):
        db.execute("INSERT INTO meta VALUES (?, ?)", (k, v))
    db.commit()
    geraete, layouts = exportieren(db, heute)
    print(f"Geräte: {bericht['geraete']}, exportiert: {geraete} Geräte, {layouts} Hauptlayouts")
    for q, n, a in db.execute("SELECT d.quelle, COUNT(DISTINCT d.id), COUNT(a.facette) FROM datensatz d "
                              "LEFT JOIN angabe a ON a.datensatz_id = d.id GROUP BY d.quelle"):
        print(f"  {q:15} {n:5} Datensätze {a:7} Angaben")
    db.execute("VACUUM")
    db.close()
    print(f"{DB.relative_to(REPO)}: {DB.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
