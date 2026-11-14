"""Erzeugt die Dummy-Dateien, die im Repository an den Pfaden der Original-Korpora liegen.

Jede Dummy-Datei hat dasselbe Format wie das Original, aber nur 5 bis 10 **erfundene** Einträge.
Sie sind keine Auszüge aus den Korpora (deren Lizenzen das teils nicht erlauben), sondern frei
geschrieben. Damit lassen sich die Skripte ohne die großen Dateien ausprobieren und testen.

Aufruf (aus dem Repo-Wurzelverzeichnis):
    python3 korpora/skripte/beispieldaten.py
    python3 korpora/skripte/beispieldaten.py --ueberschreiben   # auch echte Originale ersetzen (Vorsicht)

Ein vorhandenes Original (Größe wie im Manifest) wird ohne --ueberschreiben nie angefasst.
Die Ausgabe ist deterministisch (feste Zeitstempel), die Dateien ändern sich also nur, wenn sich
die Beispiele ändern.
"""

import argparse
import bz2
import gzip
import io
import sqlite3
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import herunterladen  # noqa: E402

ZEIT = 0


def _tar_gz(mitglieder, kompression="gz"):
    """mitglieder: Liste (Name, Bytes) oder (Name, None) für ein Verzeichnis."""
    roh = io.BytesIO()
    with tarfile.open(fileobj=roh, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for name, daten in mitglieder:
            info = tarfile.TarInfo(name)
            info.mtime = ZEIT
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            if daten is None:
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)
            else:
                info.size = len(daten)
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(daten))
    if kompression == "bz2":
        return bz2.compress(roh.getvalue())
    return gzip.compress(roh.getvalue(), mtime=ZEIT)


def _zip(mitglieder):
    roh = io.BytesIO()
    with zipfile.ZipFile(roh, "w", zipfile.ZIP_DEFLATED) as z:
        for name, daten in mitglieder:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, daten)
    return roh.getvalue()


# ----------------------------------------------------------------------------- Leipzig

LEIPZIG_NEWS = [
    "Der Stadtrat hat am Dienstag den Haushalt für das kommende Jahr verabschiedet.",
    "Die Bahn kündigte an, die Strecke zwischen Nord und Süd ab Montag wieder freizugeben.",
    "Nach dem Spiel sagte der Trainer, man habe verdient gewonnen.",
    "Die Preise für Heizöl sind im Vergleich zum Vorjahr leicht gesunken.",
    "Ein Sprecher des Ministeriums wollte sich zu den Berichten nicht äußern.",
    "Am Wochenende wird es im Süden regnerisch, im Norden bleibt es trocken.",
    "Die Zahl der Besucher stieg im vergangenen Jahr um rund zehn Prozent.",
    "Das Unternehmen plant, bis 2030 klimaneutral zu produzieren.",
]
LEIPZIG_WEB = [
    "Bitte beachten Sie unsere geänderten Öffnungszeiten über die Feiertage.",
    "Hier finden Sie alle Informationen zur Anmeldung und zu den Kosten.",
    "Mit dem Newsletter bleiben Sie immer auf dem Laufenden.",
    "Das Rezept ist einfach nachzumachen und gelingt auch Anfängern.",
    "Die Lieferung erfolgt in der Regel innerhalb von drei bis fünf Werktagen.",
    "Wir freuen uns auf Ihren Besuch und beraten Sie gerne persönlich.",
    "Alle Preise verstehen sich inklusive der gesetzlichen Mehrwertsteuer.",
]
LEIPZIG_WIKI = [
    "Die Stadt liegt am Fuß eines bewaldeten Höhenzugs und hat etwa 20.000 Einwohner.",
    "Der Fluss mündet nach rund 80 Kilometern in den Rhein.",
    "Das Gebäude wurde im 18. Jahrhundert im Stil des Barock errichtet.",
    "Der Roman erschien erstmals 1952 und wurde mehrfach verfilmt.",
    "Die Art ist in Mitteleuropa weit verbreitet und kommt vor allem auf Wiesen vor.",
    "Er studierte Physik in Göttingen und promovierte 1931 über die Streuung von Licht.",
]


def leipzig(name, saetze):
    inhalt = "".join(f"{i}\t{s}\n" for i, s in enumerate(saetze, 1)).encode("utf-8")
    return _tar_gz([(name, None), (f"{name}/{name}-sentences.txt", inhalt)])


# ----------------------------------------------------------------------------- OpenSubtitles

SUBS = [
    "Wo warst du gestern Abend?",
    "- Ich war noch im Büro.",
    "- Bis nach zehn?",
    "Die Besprechung hat länger gedauert, das habe ich dir doch gesagt.",
    "Das ist nicht fair!",
    "- Warte, ich komme mit.",
    "Hast du den Schlüssel gesehen?",
    "SIE SIND JETZT IM HOCHSICHERHEITSTRAKT",
    "Nein, auf dem Tisch liegt er nicht.",
    "Na gut, dann fahren wir eben morgen.",
]


def opensubtitles():
    return gzip.compress(("\n".join(SUBS) + "\n").encode("utf-8"), mtime=ZEIT)


# ----------------------------------------------------------------------------- GC4

def gc4():
    def dok(i, domain, titel, text, sprachwert=1.0):
        return {
            "url": f"http://www.{domain}/beitrag/{i}",
            "date_download": "2020-02-23T10:58:28Z",
            "digest": f"sha1:BEISPIEL{i:027d}",
            "length": len(text),
            "nlines": text.count("\n") + 1,
            "source_domain": domain,
            "title": titel,
            "raw_content": text,
            "cc_segment": "crawl-data/CC-MAIN-2020-10/segments/BEISPIEL/wet/BEISPIEL.warc.wet.gz",
            "original_nlines": text.count("\n") + 5,
            "original_length": len(text) * 2,
            "language": "de",
            "language_score": sprachwert,
            "perplexity": 400.0 + i,
            "bucket": "middle",
        }

    dokumente = [
        dok(1, "beispiel-forum.de", "Welche Heizung für ein altes Haus?",
            "Welche Heizung für ein altes Haus?\nHallo zusammen, wir haben ein Haus von 1960 gekauft. Lohnt sich eine Wärmepumpe?\nIch würde erst mal dämmen, sonst läuft sie nur auf Hochtouren."),
        dok(2, "beispiel-blog.de", "Sonntagsbraten",
            "Sonntagsbraten\nHeute gab es bei uns Schweinebraten mit Knödeln. Die Soße war diesmal richtig gut!"),
        dok(3, "beispiel-kommentare.de", "Kommentare",
            "Danke für den Tipp, das hat bei mir sofort funktioniert.\nBei mir leider nicht, ich bekomme eine Fehlermeldung."),
        dok(4, "beispiel-shop.de", "Gartenstuhl",
            "Gartenstuhl aus Akazienholz\nWitterungsbeständig, klappbar, in drei Farben erhältlich."),
        dok(5, "example.org", "English page", "This page is mostly written in English.", 0.62),
    ]
    inhalt = "".join(repr(d) for d in dokumente).encode("utf-8")
    return _tar_gz([("data_head_url_middle", None),
                    ("data_head_url_middle/de_middle_0000_2020-10.txt", inhalt)])


# ----------------------------------------------------------------------------- One Million Posts

POSTS = [
    (None, "Naja, das sehe ich anders. Aber jeder darf seine Meinung haben."),
    ("Genau!", "Endlich sagt es mal jemand &amp; zwar deutlich."),
    ("", "Warum wird das eigentlich immer teurer?\r\n\r\nIrgendwer muss das doch bezahlen."),
    ("Zur Sache", "Die Zahlen stimmen nicht, siehe Bericht von letzter Woche."),
    ("Lob", "Gut recherchiert, danke für den Artikel! :)"),
    (None, "Kein Kommentar."),
    ("Frage", "Weiß jemand, ab wann das gilt?"),
    ("Ironie", "Na klar, und morgen scheint dann die Sonne für alle."),
]


def one_million_posts():
    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "corpus.sqlite3"
        db = sqlite3.connect(pfad)
        db.execute("""CREATE TABLE Posts (
            ID_Post INTEGER PRIMARY KEY, ID_Parent_Post INTEGER, ID_Article INTEGER NOT NULL,
            ID_User INTEGER NOT NULL, CreatedAt TIMESTAMP NOT NULL, Status TEXT, Headline TEXT, Body TEXT,
            PositiveVotes INTEGER NOT NULL, NegativeVotes INTEGER NOT NULL)""")
        for i, (titel, text) in enumerate(POSTS, 1):
            db.execute("INSERT INTO Posts VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (i, None, 1, 100 + i, "2015-06-01 12:00:00", "online", titel, text, 0, 0))
        db.commit()
        db.execute("VACUUM")
        db.close()
        daten = pfad.read_bytes()
    readme = (b"Dummy-Datei mit erfundenen Beispielen im Format des One Million Posts Corpus.\n"
              b"Das Original: https://ofai.github.io/million-post-corpus/\n")
    return _tar_gz([("million_post_corpus", None),
                    ("million_post_corpus/corpus.sqlite3", daten),
                    ("million_post_corpus/README.txt", readme)], kompression="bz2")


# ----------------------------------------------------------------------------- Dortmunder Chat-Korpus

def chat_release():
    nachrichten = [
        ("system", "server", "<nickname>Anna</nickname> entered the room <roomname>Cafe</roomname> at 20:01:12"),
        ("utterance", "Anna", "hallo zusammen"),
        ("utterance", "Ben", "hi anna, wie geht's?"),
        ("utterance", "Anna", "ganz gut, und dir? war heute viel los <emoticon>:)</emoticon>"),
        ("action", "Ben", "gähnt"),
        ("utterance", "Ben", "geht so, bin müde.. gleich ab ins bett"),
        ("system", "server", "<nickname>Ben</nickname> left the room <roomname>Cafe</roomname> at 20:19:40"),
        ("utterance", "Anna", "schlaf gut!"),
    ]
    teile = ['<?xml version="1.0" encoding="ISO-8859-1"?>\n\n<logfile>\n\n<head>\n'
             '\t<record plattformName="BEISPIEL" recDate="2005-03-01" TNOM="8"/>\n</head>\n\n<body>\n\n']
    for i, (typ, wer, text) in enumerate(nachrichten, 1):
        teile.append(
            f'<message id="{i}" type="{typ}" creator="{wer}">\n\t<timestamp>\n\t\t20:{i:02d}\n\t</timestamp>\n'
            f'\t<messageHead>\n\t\t<nickname>{wer}</nickname>\n\t</messageHead>\n'
            f'\t<messageBody>\n\t\t{text}\n\t</messageBody>\n</message>\n\n')
    teile.append("</body>\n\n</logfile>\n")
    xml = "".join(teile).encode("iso-8859-1")
    return _zip([("Releasekorpus/Chat Korpus/Beispiel/beispiel-chat_a.xml", xml)])


def chat_web():
    seiten = [f"chatkorpus-webarchiv/{n}.html" for n in ("index", "bestand", "aufbereitung", "lizenz", "kontakt")]
    return _zip([(s, f"<html><body><p>Beispielseite {s}</p></body></html>\n".encode()) for s in seiten])


# ----------------------------------------------------------------------------- Zuordnung

ERZEUGER = {
    "deutsch/leipzig/deu_news_2024_1M.tar.gz": lambda: leipzig("deu_news_2024_1M", LEIPZIG_NEWS),
    "deutsch/leipzig/deu-de_web_2021_1M.tar.gz": lambda: leipzig("deu-de_web_2021_1M", LEIPZIG_WEB),
    "deutsch/leipzig/deu_wikipedia_2021_1M.tar.gz": lambda: leipzig("deu_wikipedia_2021_1M", LEIPZIG_WIKI),
    "deutsch/opensubtitles/de.txt.gz": opensubtitles,
    "deutsch/gc4/de_middle_0000_2020-10.tar.gz": gc4,
    "deutsch/one-million-posts/million_post_corpus.tar.bz2": one_million_posts,
    "deutsch/dortmunder-chatkorpus/chatkorpus-release.zip": chat_release,
    "deutsch/dortmunder-chatkorpus/chatkorpus-web.zip": chat_web,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ueberschreiben", action="store_true", help="auch vorhandene Originale ersetzen")
    args = parser.parse_args()
    for e in herunterladen.lade_manifeste():
        erzeuger = ERZEUGER.get(e["name"])
        if erzeuger is None:
            print(f"übersprungen (kein Generator): {e['name']}")
            continue
        ziel = e["ziel"]
        if ziel.exists() and ziel.stat().st_size == e["bytes"] and not args.ueberschreiben:
            print(f"Original vorhanden, nicht angefasst: {e['name']}")
            continue
        ziel.parent.mkdir(parents=True, exist_ok=True)
        daten = erzeuger()
        ziel.write_bytes(daten)
        print(f"Dummy geschrieben ({len(daten):,} Bytes): {e['name']}")


if __name__ == "__main__":
    main()
