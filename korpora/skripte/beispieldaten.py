"""Erzeugt die Dummy-Dateien, die im Repository an den Pfaden der Original-Korpora liegen.

Jede Dummy-Datei hat dasselbe Format wie das Original, aber nur 5 bis 10 **erfundene** Einträge.
Sie sind keine Auszüge aus den Korpora (deren Lizenzen das teils nicht erlauben), sondern frei
geschrieben. Damit lassen sich die Skripte ohne die großen Dateien ausprobieren und testen.

Aufruf (aus dem Repo-Wurzelverzeichnis):
    python3 korpora/skripte/beispieldaten.py
    python3 korpora/skripte/beispieldaten.py --ueberschreiben   # auch echte Originale ersetzen (Vorsicht)
    python3 korpora/skripte/beispieldaten.py --in-index         # Dummys nur in den Git-Index schreiben

Ein vorhandenes Original (Größe wie im Manifest) wird ohne --ueberschreiben nie angefasst.
Mit --in-index landet die Dummy-Fassung im Git-Index (der nächste Commit enthält sie), während im Arbeitsordner
das Original liegen bleibt; der Pfad wird mit skip-worktree vor git verborgen. So lassen sich neue Quellen
committen, deren Originale schon heruntergeladen sind.
Die Ausgabe ist deterministisch (feste Zeitstempel), die Dateien ändern sich also nur, wenn sich
die Beispiele ändern.
"""

import argparse
import bz2
import gzip
import io
import json
import sqlite3
import subprocess
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



# ============================================================================= Englisch

EN_NEWS = [
    "The council confirmed on Tuesday that the bridge would reopen to traffic next month.",
    "Shares in the retailer fell by three per cent after the company lowered its forecast.",
    "Police said a man in his thirties had been arrested in connection with the incident.",
    "The minister declined to comment on reports of a possible reshuffle.",
    "Heavy rain is expected across the north of the country over the weekend.",
    "The club announced the signing of a midfielder on a two-year contract.",
    "Organisers said more than ten thousand people attended the festival.",
]
EN_WEB = [
    "Thank you for subscribing to our newsletter, you will receive your first issue shortly.",
    "Our team of experienced advisers is happy to talk through the options with you.",
    "Please note that delivery times may vary during the holiday season.",
    "This recipe works just as well with frozen vegetables if you are short of time.",
    "Click here to find out more about how we use cookies on this website.",
    "All rooms include free wifi, a flat-screen television and tea and coffee facilities.",
]
EN_WIKI = [
    "The village lies on the northern bank of the river and had a population of 412 at the 2011 census.",
    "He studied chemistry at the University of Edinburgh before joining the family firm in 1923.",
    "The species is found in dry forests and scrubland at elevations of up to 800 metres.",
    "The album was released in March 1998 and reached number nine on the UK Albums Chart.",
    "Construction of the church began in the twelfth century and was completed around 1250.",
]
EN_UK = [
    "Visitors are welcome to enjoy the gardens, which are open daily from April until October.",
    "The Parish Council meets on the first Monday of each month in the village hall.",
    "Rooms are available from only 45 pounds per night, including a full English breakfast.",
    "Our centre offers a range of courses for adults who wish to return to learning.",
    "The practice is committed to providing a high standard of care for every patient.",
]


def leipzig_en(name, saetze, verzeichnis=True):
    inhalt = "".join(f"{i}\t{s}\n" for i, s in enumerate(saetze, 1)).encode("utf-8")
    pfad = f"{name}/{name}-sentences.txt" if verzeichnis else f"{name}-sentences.txt"
    mitglieder = ([(name, None)] if verzeichnis else []) + [(pfad, inhalt)]
    return _tar_gz(mitglieder)


EN_SUBS = [
    "[phone ringing]",
    "- Where have you been all day?",
    "- I told you, I was at the office.",
    "MAN: [over radio] We're leaving now.",
    "That''s not what he said, is it?",
    "(laughs) You must be joking.",
    "♪ and the night goes on ♪",
    "WARNING: AUTHORISED PERSONNEL ONLY",
    "I''ll call you when we get there.",
    "Don''t worry, it''s only a few miles.",
]


def opensubtitles_en():
    return gzip.compress(("\n".join(EN_SUBS) + "\n").encode("utf-8"), mtime=ZEIT)


def _jsonl_gz(docs):
    return gzip.compress("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in docs).encode("utf-8"), mtime=ZEIT)


def irc(teil):
    def tag(datum, kanal, zeilen):
        text = "\n".join(zeilen)
        return {"id": f"{datum}-{kanal}", "text": text, "source": "ubuntu_irc", "added": "2025-04-01",
                "created": datum, "metadata": {"license": "Public Domain", "authors": [], "channel": kanal,
                                               "url": f"https://example.org/irclogs/{datum}/{kanal}.txt"}}
    d1 = tag(f"2007-0{teil + 1}-11", "#ubuntu", [
        "=== alice [n=alice@host.example]  has joined #ubuntu",
        "[12:14] <alice> hi, my wireless card is not detected after the upgrade",
        "[12:15] <bob> alice: did you try rebooting?",
        "[12:15] <alice> yes, twice",
        "[12:16] <bob> what does lspci say?",
        "[12:17] * carol waves",
        "=== alice [n=alice@host.example]  has left #ubuntu []"])
    d2 = tag(f"2012-0{teil + 1}-20", "#ubuntu-offtopic", [
        "[09:01] <dave> morning all",
        "[09:02] <erin> dave, morning! coffee time",
        "[09:03] <dave> always"])
    return _jsonl_gz([d1, d2])


def tldr():
    posts = [
        ("I've been thinking about moving to a smaller city.\n\n> big cities are expensive\n\nTrue, but the jobs are mostly there. See [this article](http://example.org/x) for details.\n\nTL;DR: not sure it's worth it", "personalfinance"),
        ("Honestly the second season was better than the first, don&#39;t @ me.", "television"),
        ("Does anyone know how to get rid of the smell in an old fridge?\n\nI tried baking soda but it didn't help much.", "AskReddit"),
        ("Finally finished my first marathon today! My legs hurt but I'm so happy.", "running"),
        ("The patch notes are out and, well, they nerfed everything I liked.", "gaming"),
    ]
    zeilen = []
    for i, (body, sub) in enumerate(posts):
        zeilen.append(json.dumps({"author": f"user{i}", "body": body, "normalizedBody": " ".join(body.split()),
                                  "content": " ".join(body.split()), "content_len": len(body),
                                  "summary": "Example summary.", "summary_len": 2, "id": f"c{i:07d}",
                                  "subreddit": sub, "subreddit_id": "t5_example"}))
    return _zip([("corpus-webis-tldr-17.json", ("\n".join(zeilen) + "\n").encode("utf-8"))])


def enronsent():
    text = ("\nPlease find attached the revised schedule for next week. Let me know if the times do not work for\n"
            "you and I will move things around.\n\n"
            "Thanks for the update. I will call the counterparty this afternoon and send a note once\n"
            "we have agreed on the price.\n\n"
            "----- Forwarded by Example User on 05/01/2001 -----\n\n"
            "Can we meet at 3pm tomorrow? The conference room is booked.\n\n"
            "See http://example.org/report for the numbers.\n").encode("utf-8")
    return _tar_gz([("enronsent", None), ("enronsent/.DS_Store", b"\x00\x00\x00\x01Bud1"),
                    ("enronsent/._enronsent00", b"\x00\x05\x16\x07"), ("enronsent/enronsent00", text)])


def oanc():
    dateien = [
        ("OANC/license.txt", "Dummy file. The real license text is part of the original download.\n".encode("cp1252")),
        ("OANC/readme.txt", b"Dummy file with invented examples.\n"),
        ("OANC/data/spoken/telephone/switchboard/20/sw0001-trans.txt",
         b"\n \n \t\thi how are you doing today\n \t\n \t\tfine um how about you\n \t\n \t\tpretty good just got back from work\n"),
        ("OANC/data/spoken/face-to-face/charlotte/Example-ENG.txt",
         b"\n   \n   How should I start?\n   \n   However you like.\n   \n   Well, it was a quiet town, uh, and we liked it.\n"),
        ("OANC/data/written_1/journal/slate/1/Article1.txt",
         b"\n  \n   Why We Still Write Letters\n\n   Nobody sends letters any more, or so the\nargument goes. Yet the post office\nstill delivers millions of them every day.\n"),
        ("OANC/data/written_1/letters/icic/001.txt",
         b"\n   Dear Friends,\n   Thank you for your generous support this year.\n   Sincerely,\n   The Committee\n"),
        ("OANC/data/written_2/technical/911report/chapter-1.txt",
         b"\n    The committee reviewed the available evidence and\n    interviewed more than a hundred witnesses.\n"),
        ("OANC/data/written_2/travel_guides/berlitz1/Example.txt",
         b"\n   The old town is best explored on foot; allow at least half a day.\n"),
    ]
    return _zip(dateien)


def hansard(teil):
    def doc(id_, jahr, zeilen):
        return {"text": "\n".join(zeilen), "source": "uk_hansard", "id": id_, "added": "2025-04-01",
                "metadata": {"year": str(jahr), "language": "en",
                             "license": "Open Parliament Licence - https://www.parliament.uk/"}}
    neu = doc(f"debates2012-0{teil % 9 + 1}-14a", 2012, [
        "Preamble", "", "The House met at half-past Two o'clock", "", "PRAYERS", "",
        "Oral Answers to Questions", "", "Transport", "",
        "Mr. Example (Exampleshire, North) (Con): What assessment has he made of the progress of the rail electrification programme?",
        "The Secretary of State for Transport (Mr. Sample): I thank my hon. Friend for his question. Work is on schedule and the first services will run next year.",
        "lord sample of nowhere: To ask Her Majesty's Government whether they intend to publish the review before the summer.",
        "Hon. Members: Hear, hear."])
    alt = doc(f"debates1979-02-1{teil % 9 + 1}a", 1979, [
        "Preamble", "", "Mr. Old (Oldtown): asked the Secretary of State whether he is satisfied with the arrangements."])
    return _jsonl_gz([neu, alt] if teil % 2 == 0 else [alt, neu])


def stackexchange(seite, teil):
    def doc(i, text):
        return {"id": f"{seite}-{teil}-{i}", "text": text, "source": "stackexchange", "added": "2025-04-01",
                "created": "2015-05-05",
                "metadata": {"license": "Creative Commons - Attribution Share-Alike - https://creativecommons.org/licenses/by-sa/3.0/",
                             "site": f"{seite}.stackexchange.com", "url": f"https://{seite}.stackexchange.com/questions/{i}",
                             "authors": ["Example User"]}}
    texte = [
        "What is the difference between 'affect' and 'effect'?\nI always mix them up when I write emails.\n\n@Sam Good question, I have the same problem.\n\n'Affect' is usually a verb and 'effect' is usually a noun.\n\nSee https://example.org/usage for a longer explanation.",
        "How do I politely decline a meeting invitation?\nA colleague keeps inviting me to meetings that are not relevant to my work.\n\nJust say that you are focusing on other priorities this week and ask for the notes afterwards.",
        "Which is the better approach for a long trip by train?\nI am planning two weeks across the country and cannot decide.\n\nBook the longer legs in advance; the short ones are usually cheap on the day.",
        "Why does this loop never finish?\nI wrote the following and it hangs.\n\nfor i in range(10):\n    while True:\n        print(i)\n\nBecause the inner loop has no exit condition.",
        "Is it normal to feel nervous before an interview?\nYes, completely. Preparing a few answers in advance helps a lot.",
    ]
    return _jsonl_gz([doc(i, t) for i, t in enumerate(texte[: 5 if teil == 0 else 2])])


def cabnc():
    kopf = ("@UTF8\n@PID:\tDUMMY\n@Begin\n@Languages:\teng\n@Participants:\tPS01A Anna Unidentified, PS01B Ben Unidentified\n"
            "@Date:\t06-FEB-1992\n@New Episode\n")
    zeilen = [
        ("PS01A", "Er it 's in the other room I think ."),
        ("PS01B", "Oh That 's the one we ca n't find ."),
        ("PS01A", "0 ."),
        ("PS01B", "Well I do n't know what you want to do about it ."),
        ("PS01A", "<I> [>] think we should go ."),
        ("PS01B", "Yeah ."),
    ]
    inhalt = kopf + "".join(f"*{w}:\t{t} \x15{1000 * i}_{1000 * i + 900}\x15\n" for i, (w, t) in enumerate(zeilen)) + "@End\n"
    wurzel = "CABNC-0a28a11e168e312d1b9ad406a3352f31c13b86a2"
    return _zip([(f"{wurzel}/README.md", b"Dummy README\n"), (f"{wurzel}/.gitignore", b"*.bak\n"),
                 (f"{wurzel}/data/cabnc_talkbank_chat/KB0_1.cha", inhalt.encode("utf-8")),
                 (f"{wurzel}/data/cabnc_txt/KB0_1.txt", b"ignored dummy file\n")])

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
    "englisch/leipzig/eng_news_2024_1M.tar.gz": lambda: leipzig_en("eng_news_2024_1M", EN_NEWS),
    "englisch/leipzig/eng-com_web-public_2018_1M.tar.gz": lambda: leipzig_en("eng-com_web-public_2018_1M", EN_WEB),
    "englisch/leipzig/eng_wikipedia_2016_1M.tar.gz": lambda: leipzig_en("eng_wikipedia_2016_1M", EN_WIKI),
    # Dieses Archiv hat im Original kein Oberverzeichnis.
    "englisch/leipzig/eng-uk_web_2002_1M.tar.gz": lambda: leipzig_en("eng-uk_web_2002_1M", EN_UK, verzeichnis=False),
    "englisch/opensubtitles/en.txt.gz": opensubtitles_en,
    "englisch/reddit-tldr17/corpus-webis-tldr-17.zip": tldr,
    "englisch/enronsent/enronsentv1.tar.gz": enronsent,
    "englisch/oanc/OANC-1.0.1-UTF8.zip": oanc,
    "englisch/cabnc/CABNC-0a28a11.zip": cabnc,
}
for _i in range(8):
    ERZEUGER[f"englisch/ubuntu-irc/{_i:05d}_ubuntu.jsonl.gz"] = (lambda i=_i: irc(i))
for _i in range(11):
    ERZEUGER[f"englisch/uk-hansard/{_i:05d}_ukhansard.jsonl.gz"] = (lambda i=_i: hansard(i))
for _s in ("english ell scifi rpg diy workplace academia gaming travel philosophy money politics law history "
           "cooking movies skeptics parenting pets music softwareengineering").split():
    for _i in range(2):
        ERZEUGER[f"englisch/stackexchange/{_s}.stackexchange.com/{_i:05d}_se.jsonl.gz"] = (lambda s=_s, i=_i: stackexchange(s, i))


def in_index_schreiben(e, daten):
    """Dummy-Inhalt als Blob in den Index schreiben; die Datei im Arbeitsordner bleibt unberührt."""
    rel = str(e["ziel"].relative_to(herunterladen.REPO))
    blob = subprocess.run(["git", "-C", str(herunterladen.REPO), "hash-object", "-w", "--stdin"], input=daten,
                          capture_output=True, check=True).stdout.decode().strip()
    subprocess.run(["git", "-C", str(herunterladen.REPO), "update-index", "--add", "--cacheinfo", f"100644,{blob},{rel}"],
                   check=True)
    subprocess.run(["git", "-C", str(herunterladen.REPO), "update-index", "--skip-worktree", rel], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ueberschreiben", action="store_true", help="auch vorhandene Originale ersetzen")
    parser.add_argument("--in-index", action="store_true",
                        help="Dummys nur in den Git-Index schreiben, Originale im Arbeitsordner unberührt lassen")
    parser.add_argument("auswahl", nargs="*", help="nur Dateien, deren Name (sprache/pfad) so beginnt")
    args = parser.parse_args()
    for e in herunterladen.lade_manifeste():
        erzeuger = ERZEUGER.get(e["name"])
        if erzeuger is None:
            print(f"übersprungen (kein Generator): {e['name']}")
            continue
        if args.auswahl and not any(e["name"].startswith(a) for a in args.auswahl):
            continue
        ziel = e["ziel"]
        if args.in_index:
            in_index_schreiben(e, erzeuger())
            print(f"Dummy im Index: {e['name']}")
            continue
        if ziel.exists() and ziel.stat().st_size == e["bytes"] and not args.ueberschreiben:
            print(f"Original vorhanden, nicht angefasst: {e['name']}")
            continue
        ziel.parent.mkdir(parents=True, exist_ok=True)
        daten = erzeuger()
        ziel.write_bytes(daten)
        print(f"Dummy geschrieben ({len(daten):,} Bytes): {e['name']}")


if __name__ == "__main__":
    main()
