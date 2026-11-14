"""Leser für die Original-Korpora.

Jede Quelle liefert Einheiten als (text, modus):
- modus "fliess": Zeile aus Fließtext; aufeinanderfolgende Zeilen werden mit einem
  Leerzeichen verbunden.
- modus "nachricht": abgeschlossene Einheit (Chat-Nachricht, Kommentar, Absatz eines
  Kommentars); davor und danach liegt eine harte Grenze.

Stichproben sind deterministisch (fester Schritt über Blöcke bzw. Dokumente).
"""

import ast
import codecs
import gzip
import html
import io
import re
import sqlite3
import tarfile
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ORIGINAL = Path(__file__).resolve().parent.parent / "deutsch" / "original"


def leipzig(name, stat, **_):
    pfad = ORIGINAL / "leipzig" / f"{name}.tar.gz"
    with tarfile.open(pfad, "r:gz") as tar:
        datei = tar.extractfile(f"{name}/{name}-sentences.txt")
        for roh in io.TextIOWrapper(datei, encoding="utf-8"):
            stat["einheiten_gelesen"] += 1
            yield roh.rstrip("\n").split("\t", 1)[-1], "fliess"


_GROSS = re.compile(r"[^\W\d_]")


def opensubtitles(stat, schritt=50, blockgroesse=1000, **_):
    """Jeder `schritt`-te Block aus `blockgroesse` Zeilen, damit Dialogfolgen erhalten bleiben."""
    pfad = ORIGINAL / "opensubtitles" / "de.txt.gz"
    with gzip.open(pfad, "rt", encoding="utf-8", errors="replace") as f:
        for i, zeile in enumerate(f):
            if (i // blockgroesse) % schritt:
                continue
            stat["einheiten_gelesen"] += 1
            zeile = _repariere_mojibake(zeile.strip(), stat)
            if zeile.startswith("- "):
                zeile = zeile[2:]
            elif zeile.startswith("-"):
                zeile = zeile[1:].lstrip()
            buchstaben = _GROSS.findall(zeile)
            if len(buchstaben) > 3 and all(b.isupper() for b in buchstaben):
                stat["zeile_verworfen:einblendung_grossbuchstaben"] += 1
                continue
            yield zeile, "fliess"


def _zurueck_zu_bytes(zeile):
    """Kehrt eine falsche Dekodierung um: je Zeichen Windows-1252, ersatzweise Latin-1."""
    teile = []
    for z in zeile:
        try:
            teile.append(z.encode("cp1252"))
        except UnicodeEncodeError:
            teile.append(z.encode("latin-1"))
    return b"".join(teile)


def _repariere_mojibake(zeile, stat):
    """Repariert Kodierungsfehler in Untertiteln.

    1. UTF-8, das als Windows-1252/Latin-1 gelesen wurde ("Ã¤" statt "ä").
    2. Eine Untertitelquelle schreibt "Ì" für "ü" und "À" für "ä" ("fÌr", "wÀre"); erkennbar an "Ì",
       das im Deutschen nicht vorkommt, oder an "À" in einer eben reparierten Zeile. Nur dann
       wird "À" ersetzt, damit französisches "À la carte" erhalten bleibt.
    """
    repariert = False
    if "Ã" in zeile or "Â" in zeile:
        try:
            zeile = _zurueck_zu_bytes(zeile).decode("utf-8")
            stat["mojibake_repariert"] += 1
            repariert = True
        except (UnicodeEncodeError, UnicodeDecodeError):
            stat["mojibake_nicht_reparierbar"] += 1
    if "Ì" in zeile or (repariert and "À" in zeile):
        zeile = zeile.replace("Ì", "ü").replace("À", "ä")
        stat["umlaut_kodierung_repariert"] += 1
    return zeile


_GC4_TRENNER = "}{'url': "


def gc4(stat, schritt=40, min_sprachwert=0.98, **_):
    """Jedes `schritt`-te Dokument, gefiltert nach language_score."""
    with tarfile.open(ORIGINAL / "gc4" / "de_middle_0000_2020-10.tar.gz", mode="r|gz") as tar:
        for mitglied in tar:
            if not mitglied.isfile():
                continue
            datei = tar.extractfile(mitglied)
            decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
            rest = ""
            index = 0
            while True:
                roh = datei.read(1 << 22)
                if not roh:
                    break
                rest += decoder.decode(roh)
                stuecke = rest.split(_GC4_TRENNER)
                rest = stuecke.pop()
                for s in stuecke:
                    yield from _gc4_dokument(s, index, schritt, min_sprachwert, stat)
                    index += 1
            yield from _gc4_dokument(rest, index, schritt, min_sprachwert, stat)


def _gc4_dokument(s, index, schritt, min_sprachwert, stat):
    if index % schritt:
        return
    s = s.strip()
    if not s.startswith("{"):
        s = "{'url': " + s
    if not s.endswith("}"):
        s = s + "}"
    try:
        dok = ast.literal_eval(s)
    except (ValueError, SyntaxError):
        stat["dokument_unlesbar"] += 1
        return
    stat["dokumente_gelesen"] += 1
    if dok.get("language_score", 0) <= min_sprachwert:
        stat["dokument_verworfen:sprachwert"] += 1
        return
    for zeile in dok.get("raw_content", "").split("\n"):
        stat["einheiten_gelesen"] += 1
        yield zeile, "fliess"


def one_million_posts(stat, **_):
    """Titel und Text jedes Beitrags; jeder Absatz ist eine eigene Nachricht."""
    pfad = ORIGINAL / "one-million-posts" / "million_post_corpus.tar.bz2"
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(pfad, "r:bz2") as tar:
            tar.extract("million_post_corpus/corpus.sqlite3", path=tmp, filter="data")
        db = sqlite3.connect(Path(tmp) / "million_post_corpus" / "corpus.sqlite3")
        for titel, text in db.execute("SELECT Headline, Body FROM Posts ORDER BY ID_Post"):
            stat["beitraege_gelesen"] += 1
            for feld in (titel, text):
                if not feld:
                    continue
                for absatz in html.unescape(feld).splitlines():
                    if not absatz.strip():
                        continue
                    stat["einheiten_gelesen"] += 1
                    yield absatz, "nachricht"
        db.close()


_CHAT_TYPEN = {"utterance", "uttterance", "action"}


def dortmunder_chatkorpus(stat, **_):
    """Getippte Nachrichten (utterance, action) aus dem Release-Korpus, ohne Systemmeldungen."""
    pfad = ORIGINAL / "dortmunder-chatkorpus" / "chatkorpus-release.zip"
    with zipfile.ZipFile(pfad) as z:
        for name in sorted(n for n in z.namelist() if n.endswith(".xml")):
            daten = z.read(name)
            try:
                wurzel = ET.fromstring(daten)
            except ET.ParseError:
                # Einige Dateien sind kein wohlgeformtes XML; Kodierung ersetzen und erneut versuchen.
                try:
                    text = daten.decode("iso-8859-1")
                    text = re.sub(r"<\?xml[^>]*\?>", "", text, count=1)
                    text = re.sub(r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", text)
                    wurzel = ET.fromstring(text)
                    stat["datei_repariert"] += 1
                except ET.ParseError:
                    stat["datei_unlesbar"] += 1
                    continue
            stat["dateien_gelesen"] += 1
            for m in wurzel.iter("message"):
                if m.get("type") not in _CHAT_TYPEN:
                    continue
                koerper = m.find("messageBody")
                if koerper is None:
                    continue
                text = " ".join("".join(koerper.itertext()).split())
                stat["einheiten_gelesen"] += 1
                yield text, "nachricht"


QUELLEN = {
    "de-leipzig-news-2024": (leipzig, {"name": "deu_news_2024_1M"}),
    "de-leipzig-web-2021": (leipzig, {"name": "deu-de_web_2021_1M"}),
    "de-leipzig-wikipedia-2021": (leipzig, {"name": "deu_wikipedia_2021_1M"}),
    "de-opensubtitles-2024": (opensubtitles, {"schritt": 50, "blockgroesse": 1000}),
    "de-gc4-middle-2020": (gc4, {"schritt": 40, "min_sprachwert": 0.98}),
    "de-one-million-posts": (one_million_posts, {}),
    "de-dortmunder-chatkorpus": (dortmunder_chatkorpus, {}),
}

EINGABEN = {
    "de-leipzig-news-2024": ["leipzig/deu_news_2024_1M.tar.gz"],
    "de-leipzig-web-2021": ["leipzig/deu-de_web_2021_1M.tar.gz"],
    "de-leipzig-wikipedia-2021": ["leipzig/deu_wikipedia_2021_1M.tar.gz"],
    "de-opensubtitles-2024": ["opensubtitles/de.txt.gz"],
    "de-gc4-middle-2020": ["gc4/de_middle_0000_2020-10.tar.gz"],
    "de-one-million-posts": ["one-million-posts/million_post_corpus.tar.bz2"],
    "de-dortmunder-chatkorpus": ["dortmunder-chatkorpus/chatkorpus-release.zip"],
}
