"""Leser für die englischen Original-Korpora.

Schnittstelle wie in quellen.py: Jede Quelle liefert Einheiten als (text, modus).
- modus "fliess": Zeile aus Fließtext; aufeinanderfolgende Zeilen werden mit einem Leerzeichen verbunden.
- modus "nachricht": abgeschlossene Einheit (Chat-Nachricht, Absatz, Äußerung); davor und danach liegt eine
  harte Grenze, es entsteht also kein N-Gramm über das Ende hinweg (Enter wird nicht mitgezählt).

Stichproben sind deterministisch (fester Schritt über Zeilen, Blöcke bzw. Dokumente).
"""

import gzip
import html
import io
import json
import re
import tarfile
import zipfile
from pathlib import Path

import quellen as _de

ORIGINAL_EN = Path(__file__).resolve().parent.parent / "englisch" / "original"

_URL = re.compile(r"(?:https?://|ftp://|www\.)\S+")


def _ohne_url(text):
    return _URL.sub("", text)


def _mojibake(zeile, stat):
    """Repariert UTF-8, das als Windows-1252 gelesen wurde ("Ã©" statt "é")."""
    if "Ã" in zeile or "Â" in zeile:
        try:
            zeile = _de._zurueck_zu_bytes(zeile).decode("utf-8")
            stat["mojibake_repariert"] += 1
        except (UnicodeEncodeError, UnicodeDecodeError):
            stat["mojibake_nicht_reparierbar"] += 1
    return zeile


def _codeartig(zeile):
    """Grobe Erkennung von Code- und Shell-Zeilen in Fließtext (siehe korpora/englisch/README.md)."""
    s = zeile.strip()
    n = len(s)
    if n == 0:
        return False
    buchstaben = sum(c.isalpha() for c in s)
    sonder = sum((not c.isalnum()) and c != " " and c not in ".,;:!?'\"()-" for c in s)
    if re.match(r"^(\$|#|>>>|sudo |cd |ls |apt|cat |echo |grep |git |chmod|chown|\./|/[a-z]+/)", s):
        return True
    if re.search(r"[{};]\s*$", s) and sonder / n > 0.04:
        return True
    if sonder / n > 0.12:
        return True
    return len(s.split()) <= 3 and sonder >= 1 and buchstaben / n < 0.8


def _zeilen_gz(pfad, chunk=1 << 24):
    """Liefert Listen von Zeilen (bytes, ohne Zeilenende) aus einer gzip-Datei, in großen Stücken."""
    rest = b""
    with gzip.open(pfad, "rb") as f:
        while True:
            daten = f.read(chunk)
            if not daten:
                break
            stuecke = (rest + daten).split(b"\n")
            rest = stuecke.pop()
            yield stuecke
    if rest:
        yield [rest]


# ----------------------------------------------------------------------------- Leipzig

def leipzig(name, stat, **_):
    pfad = ORIGINAL_EN / "leipzig" / f"{name}.tar.gz"
    with tarfile.open(pfad, "r:gz") as tar:
        # Manche Archive haben ein Oberverzeichnis, andere nicht: die Satzdatei am Namensende erkennen.
        eintrag = next(m for m in tar if m.name.endswith("-sentences.txt"))
        for roh in io.TextIOWrapper(tar.extractfile(eintrag), encoding="utf-8"):
            stat["einheiten_gelesen"] += 1
            yield roh.rstrip("\n").split("\t", 1)[-1], "fliess"


# ----------------------------------------------------------------------------- OpenSubtitles

_KLAMMER = re.compile(r"\[[^\]]*\]|\([^)]*\)")
_SPRECHER = re.compile(r"^[A-Z][A-Z0-9 .'\-]{1,24}:\s*")
_GROSS = re.compile(r"[^\W\d_]")


def _untertitel(zeile, stat):
    zeile = _mojibake(zeile.strip(), stat)
    zeile = zeile.replace("''", "'")
    if "♪" in zeile or "♫" in zeile or "♬" in zeile:
        stat["zeile_verworfen:liedtext"] += 1
        return None
    zeile = _KLAMMER.sub(" ", zeile)
    zeile = _SPRECHER.sub("", zeile.strip())
    zeile = re.sub(r"^-\s*", "", zeile.strip())
    buchstaben = _GROSS.findall(zeile)
    if len(buchstaben) > 3 and all(b.isupper() for b in buchstaben):
        stat["zeile_verworfen:einblendung_grossbuchstaben"] += 1
        return None
    return zeile


def opensubtitles(stat, schritt=500, blockgroesse=1000, **_):
    """Jeder `schritt`-te Block aus `blockgroesse` Zeilen, damit Dialogfolgen erhalten bleiben."""
    pfad = ORIGINAL_EN / "opensubtitles" / "en.txt.gz"
    periode = schritt * blockgroesse
    i0 = 0
    for stuecke in _zeilen_gz(pfad):
        n = len(stuecke)
        for k in range(i0 // periode, (i0 + n - 1) // periode + 1):
            start = k * periode
            lo, hi = max(start, i0), min(start + blockgroesse, i0 + n)
            for roh in (stuecke[lo - i0 : hi - i0] if lo < hi else ()):
                stat["einheiten_gelesen"] += 1
                zeile = _untertitel(roh.decode("utf-8", "replace"), stat)
                if zeile:
                    yield zeile, "fliess"
        i0 += n


# ----------------------------------------------------------------------------- Ubuntu IRC

_IRC = re.compile(r"^\[\d\d:\d\d\]\s+<([^>]+)>\s?(.*)$")
_ANREDE = re.compile(r"^([^\s:,]+)[:,]\s+")


def ubuntu_irc(stat, schritt=40, **_):
    """Jedes `schritt`-te Tagesprotokoll (Kanal und Tag); nur getippte Nachrichten, ohne Systemzeilen."""
    index = 0
    for pfad in sorted((ORIGINAL_EN / "ubuntu-irc").glob("*_ubuntu.jsonl.gz")):
        with gzip.open(pfad, "rt", encoding="utf-8") as f:
            for zeile in f:
                index += 1
                if (index - 1) % schritt:
                    continue
                stat["dokumente_gelesen"] += 1
                text = json.loads(zeile)["text"]
                nachrichten = []
                for l in text.split("\n"):
                    m = _IRC.match(l)
                    if m:
                        nachrichten.append((m.group(1), m.group(2)))
                    else:
                        stat["irc_keine_nachricht"] += 1
                nicks = {n.lower() for n, _ in nachrichten}
                for _, nachricht in nachrichten:
                    a = _ANREDE.match(nachricht)
                    if a and a.group(1).lower() in nicks:
                        nachricht = nachricht[a.end():]
                        stat["irc_anrede_entfernt"] += 1
                    stat["einheiten_gelesen"] += 1
                    yield _ohne_url(nachricht), "nachricht"


# ----------------------------------------------------------------------------- Reddit (Webis TL;DR-17)

_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def reddit_tldr17(stat, schritt=60, **_):
    """Jeder `schritt`-te Beitrag; Zitate (Zeilen mit ">") und Links entfernt."""
    pfad = ORIGINAL_EN / "reddit-tldr17" / "corpus-webis-tldr-17.zip"
    with zipfile.ZipFile(pfad) as z, z.open("corpus-webis-tldr-17.json") as f:
        for i, zeile in enumerate(f):
            if i % schritt:
                continue
            stat["beitraege_gelesen"] += 1
            body = html.unescape(json.loads(zeile).get("body") or "")
            for absatz in body.split("\n"):
                absatz = absatz.strip()
                if absatz.startswith(">"):
                    stat["zitat_verworfen"] += 1
                    continue
                stat["einheiten_gelesen"] += 1
                yield _ohne_url(_MD_LINK.sub(r"\1", absatz)), "nachricht"


# ----------------------------------------------------------------------------- EnronSent

_ENRON_KOPF = re.compile(r"^(-{2,}|_{2,}|={2,}|\*{3,})|forwarded by|original message", re.I)


def enronsent(stat, **_):
    """Absätze der bereinigten E-Mails; harte Zeilenumbrüche innerhalb eines Absatzes werden zu Leerzeichen."""
    pfad = ORIGINAL_EN / "enronsent" / "enronsentv1.tar.gz"
    with tarfile.open(pfad, "r:gz") as tar:
        for m in tar:
            name = m.name.rsplit("/", 1)[-1]
            if not m.isfile() or not name.startswith("enronsent") or name.startswith("._"):
                continue
            text = tar.extractfile(m).read().decode("utf-8", "replace")
            for absatz in re.split(r"\n[ \t]*\n", text):
                absatz = " ".join(absatz.split())
                if _ENRON_KOPF.search(absatz[:60]):
                    stat["absatz_verworfen:kopf_oder_weiterleitung"] += 1
                    continue
                stat["einheiten_gelesen"] += 1
                yield _ohne_url(absatz), "nachricht"


# ----------------------------------------------------------------------------- OANC

def oanc(stat, bereich, **_):
    """Textdateien des Open American National Corpus; bereich 'gesprochen' (spoken/) oder 'geschrieben' (written_*/)."""
    pfad = ORIGINAL_EN / "oanc" / "OANC-1.0.1-UTF8.zip"
    with zipfile.ZipFile(pfad) as z:
        for info in sorted(z.infolist(), key=lambda i: i.filename):
            teile = info.filename.split("/")
            if len(teile) < 4 or teile[1] != "data" or not info.filename.endswith(".txt"):
                continue
            if (teile[2] == "spoken") != (bereich == "gesprochen"):
                continue
            stat["dateien_gelesen"] += 1
            text = z.read(info).decode("utf-8", "replace")
            for absatz in re.split(r"\n[ \t]*\n", text):
                absatz = " ".join(absatz.split())
                stat["einheiten_gelesen"] += 1
                yield _ohne_url(absatz), "nachricht"


# ----------------------------------------------------------------------------- UK Hansard

_KLEIN = {"of", "the", "for", "and", "de", "van", "von", "to", "in", "on", "upon", "with", "at", "a"}
_TITEL = {"lord", "lady", "baroness", "baron", "earl", "viscount", "countess", "duke", "marquess", "dame"}
_JAHR = re.compile(r"(?:19|20)\d\d")


def _ohne_sprecher(zeile):
    """Entfernt Sprecherangaben wie 'The Secretary of State (Mr. X): ' am Zeilenanfang."""
    i = zeile.find(": ")
    if i <= 0 or i > 140:
        return zeile
    woerter = zeile[:i].replace("(", " ( ").replace(")", " ) ").split()
    if len(woerter) > 18:
        return zeile
    if woerter[0].lower() in _TITEL and len(woerter) <= 9:
        return zeile[i + 2:]  # Lords-Anfragen: Sprecher steht teils komplett in Kleinschreibung
    for w in woerter:
        if w in "()" or w.lower() in _KLEIN or not w[0].isalpha() or w[0].isupper():
            continue
        return zeile
    return zeile[i + 2:]


def uk_hansard(stat, ab_jahr=2010, schritt=8, **_):
    """Jedes `schritt`-te Dokument ab `ab_jahr`; Sprecherangaben und Überschriften entfernt."""
    index = 0
    for pfad in sorted((ORIGINAL_EN / "uk-hansard").glob("*_ukhansard.jsonl.gz")):
        with gzip.open(pfad, "rt", encoding="utf-8") as f:
            for zeile in f:
                doc = json.loads(zeile)
                jahr = (doc.get("metadata") or {}).get("year")
                if jahr is None:
                    m = _JAHR.search(str(doc.get("id", "")))
                    jahr = m.group() if m else None
                if jahr is None:
                    stat["dokument_verworfen:ohne_jahr"] += 1
                    continue
                if int(jahr) < ab_jahr:
                    stat["dokument_verworfen:vor_ab_jahr"] += 1
                    continue
                index += 1
                if (index - 1) % schritt:
                    continue
                stat["dokumente_gelesen"] += 1
                for absatz in doc["text"].split("\n"):
                    absatz = _ohne_sprecher(absatz.strip())
                    woerter = absatz.split()
                    if absatz.startswith("[") or (len(woerter) <= 8 and not re.search(r"[.?!][\"'”’)]?$", absatz)):
                        stat["absatz_verworfen:ueberschrift"] += 1
                        continue
                    stat["einheiten_gelesen"] += 1
                    yield absatz, "nachricht"


# ----------------------------------------------------------------------------- StackExchange

_ERWAEHNUNG = re.compile(r"@\w+[:,]?\s*")


def stackexchange(stat, sites, schritt=30, **_):
    """Jedes `schritt`-te Dokument der genannten Seiten; Code-Zeilen, Links und @-Erwähnungen entfernt."""
    index = 0
    for site in sites:
        verzeichnis = ORIGINAL_EN / "stackexchange" / f"{site}.stackexchange.com"
        for pfad in sorted(verzeichnis.glob("*_se.jsonl.gz")):
            with gzip.open(pfad, "rt", encoding="utf-8") as f:
                for zeile in f:
                    index += 1
                    if (index - 1) % schritt:
                        continue
                    stat["dokumente_gelesen"] += 1
                    for absatz in json.loads(zeile)["text"].split("\n"):
                        absatz = _ERWAEHNUNG.sub("", _ohne_url(absatz)).strip()
                        if _codeartig(absatz):
                            stat["zeile_verworfen:code"] += 1
                            continue
                        stat["einheiten_gelesen"] += 1
                        yield absatz, "nachricht"


# ----------------------------------------------------------------------------- CABNC

_CAB_ZEIT = re.compile("\x15[\\d_]*\x15?")
_CAB_KLAMMER = re.compile(r"\[[^\]]*\]")
_CAB_NT = re.compile(r"\b(ca|wo|sha) n't\b", re.I)
_CAB_NT2 = re.compile(r"(\w) n't\b")
_CAB_KLITIKA = re.compile(r"(\w)\s+'(s|d|ll|re|ve|m)\b")
_CAB_PUNKT = re.compile(r"\s+([.,?!;:])")
_CAB_VERSCHMELZ = {"gon na": "gonna", "wan na": "wanna", "got ta": "gotta", "gim me": "gimme", "lem me": "lemme"}


def _cab_aeusserung(text, stat):
    text = _CAB_ZEIT.sub(" ", text)
    text = _CAB_KLAMMER.sub(" ", text).replace("<", " ").replace(">", " ")
    if re.fullmatch(r"[0 .?!]*", text.strip()):
        stat["aeusserung_verworfen:stille"] += 1
        return None
    text = _CAB_NT.sub(lambda m: {"ca": "can", "wo": "won", "sha": "shan"}[m.group(1).lower()] + "'t", text)
    text = _CAB_NT2.sub(r"\1n't", text)
    text = _CAB_KLITIKA.sub(r"\1'\2", text)
    text = _CAB_PUNKT.sub(r"\1", text)
    for alt, neu in _CAB_VERSCHMELZ.items():
        text = re.sub(rf"\b{alt}\b", neu, text, flags=re.I)
    return " ".join(text.split())


def cabnc(stat, **_):
    """Äußerungen aus den CHAT-Transkripten; BNC-Tokenisierung ("do n't", "it 's") wird zurückgebaut."""
    pfad = next((ORIGINAL_EN / "cabnc").glob("CABNC-*.zip"))
    with zipfile.ZipFile(pfad) as z:
        namen = sorted((i for i in z.infolist()
                        if "/data/cabnc_talkbank_chat/" in i.filename and i.filename.endswith(".cha")),
                       key=lambda i: i.filename)
        for info in namen:
            stat["dateien_gelesen"] += 1
            aktuell = None
            for l in z.read(info).decode("utf-8", "replace").split("\n"):
                if l.startswith("*"):
                    if aktuell is not None:
                        yield from _cab_ausgabe(aktuell, stat)
                    aktuell = l.split("\t", 1)[1] if "\t" in l else ""
                elif l.startswith("\t") and aktuell is not None:
                    aktuell += " " + l.strip()
                elif aktuell is not None:
                    yield from _cab_ausgabe(aktuell, stat)
                    aktuell = None
            if aktuell is not None:
                yield from _cab_ausgabe(aktuell, stat)


def _cab_ausgabe(text, stat):
    stat["einheiten_gelesen"] += 1
    t = _cab_aeusserung(text, stat)
    if t:
        yield t, "nachricht"


_PROSA = ["english", "ell", "scifi", "rpg", "diy", "workplace", "academia", "gaming", "travel", "philosophy",
          "money", "politics", "law", "history", "cooking", "movies", "skeptics", "parenting", "pets", "music"]

QUELLEN = {
    "en-leipzig-news-2024": (leipzig, {"name": "eng_news_2024_1M"}),
    "en-leipzig-web-2018": (leipzig, {"name": "eng-com_web-public_2018_1M"}),
    "en-leipzig-wikipedia-2016": (leipzig, {"name": "eng_wikipedia_2016_1M"}),
    "en-leipzig-uk-web-2002": (leipzig, {"name": "eng-uk_web_2002_1M"}),
    "en-opensubtitles-2024": (opensubtitles, {"schritt": 500, "blockgroesse": 1000}),
    "en-ubuntu-irc": (ubuntu_irc, {"schritt": 40}),
    "en-reddit-tldr17": (reddit_tldr17, {"schritt": 60}),
    "en-enronsent": (enronsent, {}),
    "en-oanc-gesprochen": (oanc, {"bereich": "gesprochen"}),
    "en-oanc-geschrieben": (oanc, {"bereich": "geschrieben"}),
    "en-uk-hansard": (uk_hansard, {"ab_jahr": 2010, "schritt": 30}),
    "en-stackexchange-prosa": (stackexchange, {"sites": _PROSA, "schritt": 30}),
    "en-stackexchange-softwareengineering": (stackexchange, {"sites": ["softwareengineering"], "schritt": 6}),
    "en-cabnc": (cabnc, {}),
}
