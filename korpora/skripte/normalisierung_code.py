"""Normalisierung für Quelltext (Gegenstück zu normalisierung.py für Prosa).

Eine Datei wird als Ganzes bearbeitet, damit N-Gramme über Zeilenenden hinweg entstehen. Ergebnis ist eine Liste von
Segmenten; zwischen zwei Segmenten liegt eine harte Grenze. Eine Datei ohne verwertbare Zeile ergibt None.

Regeln (Entscheidungen vom 16.11.2026, siehe korpora/code/README.md):
1. Führende Leerzeichen und Tabs jeder Zeile werden ignoriert (der Editor rückt ein).
2. Jedes Zeilenende (LF, CRLF, CR, auch Seitenvorschub und Unicode-Zeilentrenner) zählt als ein Enter ("\\n").
3. Zeichen wie in normalisierung.py: tippbar = deutsche QWERTZ-Tastatur; Typografie ersetzt, Akzentbuchstaben
   auf den Grundbuchstaben, übrige Zeichen werden zur harten Grenze.
4. Zeilen mit fremder Schrift (etwa chinesische Kommentare) oder überwiegend fremdsprachigem Text werden einzeln
   verworfen, nicht die ganze Datei. Sehr lange Zeilen (Daten, Minifizierung) werden verworfen.
5. Mehrfache Leerzeichen innerhalb einer Zeile (Ausrichtung) werden zu einem; mehr als zwei Leerzeilen in Folge
   werden auf zwei gekürzt; Leerzeilen am Dateianfang und -ende entfallen. Nach der letzten Zeile steht ein Enter.
"""

import re
import unicodedata
from collections import Counter

import normalisierung as N

VERSION = "1"

MAX_ZEILENLAENGE = 400
MAX_ZEILENLAENGE_OHNE_LEERZEICHEN = 200
MAX_LEERZEILEN = 2
# Datentabellen (Emoji-Listen, Namenslisten mit Akzenten) sind kein getippter Code: Dateien mit sehr vielen
# Sonderzeichen entfallen ganz.
MAX_GRENZEN_JE_DATEI = 100
MAX_TRANSLITERIERT_JE_DATEI = 300

_ZEILENENDE = re.compile("\r\n|\r|\n|\x0b|\x0c|\x85| | ")
_LEERZEICHEN = re.compile(" {2,}")


def _zeile(zeile, stat):
    """Bereinigt eine Zeile; liefert eine Liste von Teilen (mehr als einer bei harten Grenzen) oder None."""
    if len(zeile) > MAX_ZEILENLAENGE or (len(zeile) > MAX_ZEILENLAENGE_OHNE_LEERZEICHEN and " " not in zeile):
        stat["zeile_verworfen:zu_lang"] += 1
        return None
    teile, aktuell, transliteriert = [], [], 0
    for z in zeile:
        if z in N.TIPPBAR:
            aktuell.append(z)
            continue
        if z in N.ERSETZUNG:
            aktuell.append(N.ERSETZUNG[z])
            stat["ersetzt:" + z] += 1
            continue
        art, ersatz = N._klassifiziere(z)
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
    buchstaben = sum(c.isalpha() for t in teile for c in t)
    if transliteriert >= N.MIN_ANZAHL_TRANSLITERIERT and buchstaben and transliteriert / buchstaben > N.MAX_ANTEIL_TRANSLITERIERT:
        stat["zeile_verworfen:zu_viele_fremde_buchstaben"] += 1
        return None
    teile = [_LEERZEICHEN.sub(" ", t) for t in teile]
    return teile, transliteriert


def normalisiere_datei(text, stat):
    """Normalisiert den Text einer Quelltextdatei. Gibt eine Liste von Segmenten oder None zurück."""
    text = text.lstrip("﻿")
    if N._C1_MUSTER.search(text):
        text = N._C1_MUSTER.sub(lambda m: bytes([ord(m.group())]).decode("cp1252", "replace"), text)
        stat["c1_als_cp1252_gelesen"] += 1
    text = unicodedata.normalize("NFC", text)

    lokal = Counter()  # erst bei einer behaltenen Datei in stat übernehmen
    grenzen_datei = transliteriert_datei = 0
    segmente, zeilen, leer = [], [], 0
    for roh in _ZEILENENDE.split(text.replace("\t", " ")):
        zeile = roh.strip()
        if not zeile:
            leer += 1
            if leer <= MAX_LEERZEILEN and zeilen:
                zeilen.append("")
            elif zeilen:
                lokal["leerzeile_gekuerzt"] += 1
            continue
        erg = _zeile(zeile, lokal)
        if erg is None:
            continue
        teile, anzahl_transliteriert = erg
        grenzen_datei += len(teile) - 1
        transliteriert_datei += anzahl_transliteriert
        leer = 0
        if len(teile) == 1:
            zeilen.append(teile[0])
            continue
        # harte Grenzen mitten in der Zeile: erster Teil schließt das Segment, letzter beginnt ein neues
        zeilen.append(teile[0])
        segmente.append("\n".join(zeilen))
        for mitte in teile[1:-1]:
            segmente.append(mitte)
        zeilen = [teile[-1]]
        lokal["grenzen_gesetzt"] += len(teile) - 1
    while zeilen and zeilen[-1] == "":
        zeilen.pop()
    if zeilen:
        segmente.append("\n".join(zeilen) + "\n")
    segmente = [s for s in segmente if s.strip()]
    if not segmente:
        stat["datei_verworfen:ohne_verwertbare_zeile"] += 1
        return None
    if grenzen_datei >= MAX_GRENZEN_JE_DATEI or transliteriert_datei >= MAX_TRANSLITERIERT_JE_DATEI:
        stat["datei_verworfen:datentabelle_mit_sonderzeichen"] += 1
        return None
    stat.update(lokal)
    return segmente
