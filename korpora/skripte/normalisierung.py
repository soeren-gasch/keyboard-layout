"""Normalisierung von Rohtext auf tippbare Zeichen.

Ergebnis je Zeile: eine Liste von Segmenten. Zwischen zwei Segmenten liegt eine
harte Grenze, über die hinweg keine N-Gramme gezählt werden. Eine verworfene
Zeile ergibt None.

Regeln (siehe korpora/skripte/README.md):
1. Unicode NFC.
2. Typografie ersetzen (Anführungszeichen, Striche, Auslassungspunkte, Sonderleerzeichen).
3. Lateinische Buchstaben mit Akzent (außer äöüß) auf den Grundbuchstaben bringen.
4. Zeile verwerfen bei fremder Schrift oder zu vielen ersetzten Buchstaben.
5. Übrige nicht tippbare Zeichen werden zur harten Grenze.
6. Mehrfache Leerzeichen zusammenfassen.
"""

import re
import unicodedata
from collections import Counter

VERSION = "2"

# Was auf einer deutschen QWERTZ-Tastatur direkt tippbar ist (inkl. Shift und AltGr),
# unabhängig vom zu bewertenden Layout.
TIPPBAR = frozenset(
    [chr(c) for c in range(0x20, 0x7F)] + list("äöüÄÖÜß€§°²³µ")
)

ERSETZUNG = {}
for _z in "„“”‟«»″〃＂":
    ERSETZUNG[_z] = '"'
for _z in "‚‘’‛‹›′´`ʼ＇":
    ERSETZUNG[_z] = "'"
for _z in "‐‑‒–—―−⁃﹣－":
    ERSETZUNG[_z] = "-"
ERSETZUNG["…"] = "..."
ERSETZUNG["\t"] = " "
for _c in [0x00A0, 0x1680, *range(0x2000, 0x200B), 0x202F, 0x205F, 0x3000]:
    ERSETZUNG[chr(_c)] = " "
# Unsichtbare Zeichen ersatzlos entfernen.
for _c in [0x00AD, 0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF]:
    ERSETZUNG[chr(_c)] = ""

# Lateinische Buchstaben, die NFD nicht in Grundbuchstabe plus Akzent zerlegt.
TRANSLITERATION = {
    "Đ": "D", "đ": "d", "Ł": "L", "ł": "l", "Ø": "O", "ø": "o",
    "Æ": "Ae", "æ": "ae", "Œ": "Oe", "œ": "oe", "Þ": "Th", "þ": "th",
    "Ð": "D", "ð": "d", "ı": "i", "Ħ": "H", "ħ": "h", "Ŋ": "N", "ŋ": "n",
    "ĸ": "k", "ſ": "s", "Ŧ": "T", "ŧ": "t",
}

# Eine Zeile gilt als fremdsprachig, wenn mindestens MIN_ANZAHL_TRANSLITERIERT Buchstaben
# ersetzt wurden und deren Anteil an allen Buchstaben MAX_ANTEIL_TRANSLITERIERT übersteigt.
# Einzelne Namen und Lehnwörter ("Café", "Đoković") bleiben so erhalten.
MIN_ANZAHL_TRANSLITERIERT = 3
MAX_ANTEIL_TRANSLITERIERT = 0.05
# Mindestanteil Buchstaben an allen Nicht-Leerzeichen.
MIN_ANTEIL_BUCHSTABEN = 0.5
MIN_BUCHSTABEN = 2

_C1_MUSTER = re.compile("[\x80-\x9f]")

_cache = {}


def _klassifiziere(z):
    """Liefert (art, ersatz) für ein Zeichen, das weder tippbar noch in ERSETZUNG ist.

    art: 'trans' (lateinischer Buchstabe ersetzt), 'fremdschrift' (Zeile verwerfen),
    'kombi' (kombinierendes Zeichen, entfernen), 'grenze' (harte Grenze).
    """
    if z in _cache:
        return _cache[z]
    kat = unicodedata.category(z)
    if z in TRANSLITERATION:
        erg = ("trans", TRANSLITERATION[z])
    elif kat.startswith("M"):
        erg = ("kombi", "")
    elif kat.startswith("L"):
        name = unicodedata.name(z, "")
        if name.startswith("LATIN"):
            basis = "".join(
                c for c in unicodedata.normalize("NFD", z) if not unicodedata.category(c).startswith("M")
            )
            if basis and all(c in TIPPBAR for c in basis):
                erg = ("trans", basis)
            else:
                erg = ("grenze", None)
        else:
            erg = ("fremdschrift", None)
    else:
        erg = ("grenze", None)
    _cache[z] = erg
    return erg


def normalisiere(zeile, stat):
    """Normalisiert eine Zeile. Gibt eine Liste von Segmenten oder None (verworfen) zurück.

    stat ist ein Counter, in den Ereignisse gezählt werden.
    """
    if _C1_MUSTER.search(zeile):
        # C1-Steuerzeichen sind nie echter Text, sondern falsch gelesenes Windows-1252 (z. B. 0x84 = „).
        zeile = _C1_MUSTER.sub(lambda m: bytes([ord(m.group())]).decode("cp1252", "replace"), zeile)
        stat["c1_als_cp1252_gelesen"] += 1
    zeile = unicodedata.normalize("NFC", zeile)
    teile = []
    aktuell = []
    transliteriert = 0
    for z in zeile:
        if z in TIPPBAR:
            aktuell.append(z)
            continue
        if z in ERSETZUNG:
            aktuell.append(ERSETZUNG[z])
            stat["ersetzt:" + z] += 1
            continue
        if z in "\r\n":
            aktuell.append(" ")
            continue
        art, ersatz = _klassifiziere(z)
        if art == "trans":
            aktuell.append(ersatz)
            transliteriert += 1
            stat["transliteriert:" + z] += 1
        elif art == "kombi":
            stat["entfernt_kombinierend"] += 1
        elif art == "fremdschrift":
            stat["zeile_verworfen:fremde_schrift"] += 1
            return None
        else:
            stat["grenze:" + z] += 1
            teile.append("".join(aktuell))
            aktuell = []
    teile.append("".join(aktuell))

    buchstaben = 0
    nicht_leer = 0
    segmente = []
    for i, t in enumerate(teile):
        while "  " in t:
            t = t.replace("  ", " ")
        if i == 0:
            t = t.lstrip(" ")
        if i == len(teile) - 1:
            t = t.rstrip(" ")
        if t and t != " ":
            segmente.append(t)
            buchstaben += sum(c.isalpha() for c in t)
            nicht_leer += sum(c != " " for c in t)

    if buchstaben < MIN_BUCHSTABEN:
        stat["zeile_verworfen:zu_wenig_buchstaben"] += 1
        return None
    if buchstaben / nicht_leer < MIN_ANTEIL_BUCHSTABEN:
        stat["zeile_verworfen:zu_wenig_buchstabenanteil"] += 1
        return None
    if transliteriert >= MIN_ANZAHL_TRANSLITERIERT and transliteriert / buchstaben > MAX_ANTEIL_TRANSLITERIERT:
        stat["zeile_verworfen:zu_viele_fremde_buchstaben"] += 1
        return None
    stat["grenzen_gesetzt"] += len(segmente) - 1
    return segmente


def zusammenfassen(stat, top=15):
    """Verdichtet die Einzelzeichen-Statistik für den Prüfbericht."""
    erg = Counter()
    beispiele = {}
    for k, v in stat.items():
        if ":" in k and "verworfen" not in k:
            art, zeichen = k.split(":", 1)
            erg[art] += v
            beispiele.setdefault(art, Counter())[zeichen] = v
        else:
            erg[k] += v
    return {
        "summen": dict(sorted(erg.items())),
        "haeufigste_zeichen": {
            art: [[z, n] for z, n in c.most_common(top)] for art, c in sorted(beispiele.items())
        },
    }
