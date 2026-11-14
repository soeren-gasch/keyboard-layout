"""Zählt Uni-, Bi- und Trigramme je Quelle.

Aufruf (aus dem Repo-Wurzelverzeichnis):
    python3 korpora/skripte/zaehlen.py                    # alle Quellen
    python3 korpora/skripte/zaehlen.py de-leipzig-news-2024 --prozesse 6
    python3 korpora/skripte/zaehlen.py --text-aus ~/keyboard/aufbereitet
    python3 korpora/skripte/zaehlen.py --ausgabe /tmp/probe        # Probelauf, z. B. auf den Dummy-Dateien

Ausgabe je Quelle unter korpora/ngramme/<quelle>/:
    1-grams.txt, 2-grams.txt, 3-grams.txt   Format "Anzahl N-Gramm", absteigend sortiert
    meta.json                               Herkunft, Parameter und Prüfbericht
"""

import argparse
import datetime
import gzip
import hashlib
import json
import re
import sys
import time
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import normalisierung  # noqa: E402
import quellen  # noqa: E402

SKRIPTE = Path(__file__).resolve().parent
KORPORA = SKRIPTE.parent
ZIEL = KORPORA / "ngramme"
STAPEL_ZEICHEN = 4_000_000
MAX_OFFEN = 50_000


def _segmente(einheiten, stat):
    """Normalisiert Einheiten und verbindet Fließtext-Zeilen; liefert zählbare Strings."""
    offen = ""
    for text, modus in einheiten:
        segmente = normalisierung.normalisiere(text, stat)
        if segmente is None:
            continue
        stat["zeilen_verwendet"] += 1
        if modus == "nachricht":
            if offen:
                yield offen
                offen = ""
            yield from segmente
            continue
        erstes = segmente[0]
        offen = f"{offen} {erstes}" if offen else erstes
        if len(segmente) > 1:
            yield offen
            yield from segmente[1:-1]
            offen = segmente[-1]
        if len(offen) > MAX_OFFEN:
            yield offen
            offen = ""
    if offen:
        yield offen


def _verarbeite(auftrag):
    nummer, einheiten, text_aus = auftrag
    stat = Counter()
    c1, c2, c3 = Counter(), Counter(), Counter()
    ausgabe = gzip.open(text_aus / f"teil-{nummer:05d}.txt.gz", "wt", encoding="utf-8") if text_aus else None
    for s in _segmente(einheiten, stat):
        c1.update(s)
        c2.update(s[i : i + 2] for i in range(len(s) - 1))
        c3.update(s[i : i + 3] for i in range(len(s) - 2))
        if ausgabe:
            ausgabe.write(s + "\n")
    if ausgabe:
        ausgabe.close()
    return c1, c2, c3, stat


def _stapel(einheiten, text_aus):
    stapel, groesse, nummer = [], 0, 0
    for e in einheiten:
        stapel.append(e)
        groesse += len(e[0])
        if groesse >= STAPEL_ZEICHEN:
            yield nummer, stapel, text_aus
            stapel, groesse, nummer = [], 0, nummer + 1
    if stapel:
        yield nummer, stapel, text_aus


def _sha256(pfad):
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def maskiere(ngramm):
    """Maskierung wie im keyboard_layout_optimizer: Backslash als \\\\, Zeilenumbruch als \\n."""
    return ngramm.replace("\\", "\\\\").replace("\n", "\\n")


_MASKE = re.compile(r"\\(\\|n)")


def demaskiere(text):
    """Umkehrung von maskiere(). Hinweis: Der Optimizer selbst ersetzt zuerst \\n und liest
    deshalb ein wörtliches Backslash-n falsch; im deutschen Text kommt das kaum vor."""
    return _MASKE.sub(lambda m: "\\" if m.group(1) == "\\" else "\n", text)


def _schreibe_ngramme(pfad, zaehler):
    with open(pfad, "w", encoding="utf-8") as f:
        for ngramm, anzahl in sorted(zaehler.items(), key=lambda x: (-x[1], x[0])):
            f.write(f"{anzahl} {maskiere(ngramm)}\n")


def pruefe_eingaben(name):
    """Gibt die Dateien zurück, die nicht der Original-Größe laut Manifest entsprechen (fehlend oder Dummy)."""
    return [e["name"] for e in quellen.eingaben()[name]
            if not e["ziel"].exists() or e["ziel"].stat().st_size != e["bytes"]]


def zaehle(name, prozesse, text_aus, ziel_wurzel):
    leser, parameter = quellen.QUELLEN[name]
    start = time.time()
    lese_stat = Counter()
    if text_aus:
        text_aus = Path(text_aus).expanduser() / name
        text_aus.mkdir(parents=True, exist_ok=True)
        for alt in text_aus.glob("teil-*.txt.gz"):
            alt.unlink()
    c1, c2, c3, stat = Counter(), Counter(), Counter(), Counter()
    with Pool(prozesse) as pool:
        auftraege = _stapel(leser(stat=lese_stat, **parameter), text_aus)
        for t1, t2, t3, s in pool.imap_unordered(_verarbeite, auftraege):
            c1.update(t1)
            c2.update(t2)
            c3.update(t3)
            stat.update(s)
    stat.update(lese_stat)

    ziel = ziel_wurzel / name
    ziel.mkdir(parents=True, exist_ok=True)
    for n, c in ((1, c1), (2, c2), (3, c3)):
        _schreibe_ngramme(ziel / f"{n}-grams.txt", c)

    dateien = quellen.eingaben()[name]
    eingaben = {}
    for e in dateien:
        eingaben[e["pfad"]] = {"sha256": e["sha256"], "bytes": e["bytes"], "url": e["url"]}

    meta = {
        "quelle": name,
        "erzeugt_von": {
            "skript": "korpora/skripte/zaehlen.py",
            "normalisierung_version": normalisierung.VERSION,
            "skripte_sha256": {
                p.name: _sha256(p) for p in sorted(SKRIPTE.glob("*.py"))
            },
        },
        "datum": datetime.date.today().isoformat(),
        "dauer_sekunden": round(time.time() - start),
        "eingaben": eingaben,
        "parameter": {k: v for k, v in parameter.items()},
        "summen": {
            "zeichen": sum(c1.values()),
            "bigramme": sum(c2.values()),
            "trigramme": sum(c3.values()),
            "verschiedene_unigramme": len(c1),
            "verschiedene_bigramme": len(c2),
            "verschiedene_trigramme": len(c3),
        },
        "pruefbericht": normalisierung.zusammenfassen(stat),
    }
    (ziel / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{name}: {meta['summen']['zeichen']:,} Zeichen in {meta['dauer_sekunden']} s", flush=True)


def uebersicht(ziel_wurzel):
    """Schreibt korpora/ngramme/README.md aus allen meta.json."""
    zeilen = [
        "# N-Gramme je Quelle",
        "",
        "Erzeugt von `korpora/skripte/zaehlen.py`; Details und Prüfbericht in `meta.json` je Ordner.",
        "Format der N-Gramm-Dateien: `Anzahl N-Gramm`, kompatibel mit dem keyboard_layout_optimizer.",
        "",
        "| Quelle | Datum | Zeichen | Zeilen verwendet | Zeilen verworfen | ersetzt | transliteriert | Grenzen |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for meta_pfad in sorted(ziel_wurzel.glob("*/meta.json")):
        m = json.loads(meta_pfad.read_text(encoding="utf-8"))
        s = m["pruefbericht"]["summen"]
        verworfen = sum(v for k, v in s.items() if "verworfen" in k)
        zeilen.append(
            f"| `{m['quelle']}` | {m['datum']} | {m['summen']['zeichen']:,} | {s.get('zeilen_verwendet', 0):,} "
            f"| {verworfen:,} | {s.get('ersetzt', 0):,} | {s.get('transliteriert', 0):,} | {s.get('grenze', 0):,} |"
        )
    (ziel_wurzel / "README.md").write_text("\n".join(zeilen) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("quellen", nargs="*", help="Quellen (Standard: alle): " + ", ".join(quellen.QUELLEN))
    parser.add_argument("--prozesse", type=int, default=4)
    parser.add_argument("--text-aus", help="Verzeichnis für den bereinigten Text (außerhalb von Git)")
    parser.add_argument("--ausgabe", help="anderes Ausgabeverzeichnis statt korpora/ngramme (nötig für Läufe auf Dummy-Dateien)")
    args = parser.parse_args()
    unbekannt = set(args.quellen) - set(quellen.QUELLEN)
    if unbekannt:
        parser.error(f"unbekannte Quelle(n): {', '.join(sorted(unbekannt))}")
    ziel_wurzel = Path(args.ausgabe).expanduser().resolve() if args.ausgabe else ZIEL
    auswahl = args.quellen or list(quellen.QUELLEN)
    if ziel_wurzel == ZIEL:
        # Schutz: Die Ergebnisse im Repo dürfen nur aus den echten Originalen entstehen.
        for name in auswahl:
            abweichend = pruefe_eingaben(name)
            if abweichend:
                parser.error(
                    f"{name}: Eingabe ist nicht das Original (fehlt oder Dummy): {', '.join(abweichend)}.\n"
                    "Originale laden: python3 korpora/skripte/herunterladen.py\n"
                    "Zum Ausprobieren mit Dummies: --ausgabe <Verzeichnis außerhalb von korpora/ngramme>")
    for name in auswahl:
        zaehle(name, args.prozesse, args.text_aus, ziel_wurzel)
    uebersicht(ziel_wurzel)


if __name__ == "__main__":
    main()
