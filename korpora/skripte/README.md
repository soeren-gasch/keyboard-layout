# Skripte zur Korpus-Aufbereitung

Aus den Original-Korpora entstehen in zwei Schritten N-Gramm-Datensätze:

1. **`zaehlen.py`**: jede Quelle einzeln lesen, normalisieren und Uni-, Bi- und Trigramme zählen. Ergebnis unter `korpora/ngramme/<quelle>/`.
2. **`mischen.py`**: Quellen nach einem Rezept unter `korpora/mischungen/<name>.json` gewichtet zusammenführen. Ergebnis unter `korpora/mischungen/<name>/`.

Neue Sprachen oder Code kommen als weitere Quellen dazu. Eine Mischung aus Deutsch, Englisch und Code ist dann nur ein weiteres Rezept.

Nur Python-Standardbibliothek, ab Python 3.11.

```sh
python3 korpora/skripte/zaehlen.py --prozesse 8 --text-aus ~/keyboard/aufbereitet   # alle Quellen
python3 korpora/skripte/zaehlen.py de-leipzig-news-2024                            # eine Quelle
python3 korpora/skripte/mischen.py korpora/mischungen/de-standard.json
```

`--text-aus` schreibt zusätzlich den bereinigten Text (ein Segment je Zeile) außerhalb des Repos, etwa für spätere Kennzahlen auf Wortebene.

## Zielformat

Je Datensatz ein Ordner mit:

| Datei | Inhalt |
| --- | --- |
| `1-grams.txt`, `2-grams.txt`, `3-grams.txt` | je Zeile `Anzahl N-Gramm`, absteigend sortiert; Backslash als `\\`, Zeilenumbruch als `\n` maskiert |
| `meta.json` | Herkunft, Prüfsummen der Eingaben und Skripte, Parameter, Summen, Prüfbericht |

- Bei Quellen sind die Anzahlen **ganzzahlige Rohzählungen**, bei Mischungen relative Häufigkeiten mal 10^10.
- Gezählt werden **Zeichen, nicht Tasten**. Groß- und Kleinschreibung bleibt erhalten. Welche Taste, Ebene oder welcher Modifier ein Zeichen braucht, entscheidet das Bewertungswerkzeug. Die Daten hängen so weder vom Layout noch von einem bestimmten Optimizer ab.
- Das Format ist direkt mit dem [keyboard_layout_optimizer](https://github.com/dariogoetz/keyboard_layout_optimizer) lesbar. Skip-Bigramme lassen sich exakt aus den Trigrammen ableiten.
- Der Kopfblock für generierte Dateien steht in `meta.json`, weil die N-Gramm-Dateien sonst nicht mehr lesbar wären.

## Normalisierung (`normalisierung.py`)

**Tippbar** ist, was auf einer deutschen QWERTZ-Tastatur direkt erreichbar ist: druckbares ASCII, `äöüÄÖÜß`, `€§°²³µ`. Die Liste hängt bewusst nicht vom eigenen Layout ab, sonst wären die Daten zu dessen Gunsten verzerrt.

| Fall | Behandlung |
| --- | --- |
| C1-Steuerzeichen 0x80–0x9F | als Windows-1252 gelesen (0x84 → „), danach weiter wie unten |
| Unicode | NFC (kombinierte Umlaute werden ein Zeichen) |
| Typografie: `„“”«»`, `‚‘’´`, `–—−`, `…`, Sonderleerzeichen, Tab | ersetzt durch `"`, `'`, `-`, `...`, Leerzeichen |
| Unsichtbare Zeichen (weicher Trennstrich, Nullbreite) | entfernt |
| Lateinische Buchstaben mit Akzent außer äöüß (é, ć, Đ, ø, œ …) | Grundbuchstabe bzw. Tabelle (Đ → D, æ → ae) |
| Zeile mit mindestens 3 solchen Buchstaben und mehr als 5 % Anteil | Zeile verworfen (wahrscheinlich fremdsprachig) |
| Buchstaben fremder Schriften (Kyrillisch, Griechisch, Chinesisch, Japanisch, Koreanisch …) | Zeile verworfen |
| Übrige Zeichen (Emojis, ©, ™, Rahmenzeichen) | harte Grenze: kein N-Gramm über diese Stelle |
| Weniger als 2 Buchstaben oder weniger als 50 % Buchstaben unter den Nicht-Leerzeichen | Zeile verworfen |
| Mehrfache Leerzeichen | zusammengefasst; Leerzeichen am Zeilenanfang und -ende entfernt |

## Zeilenenden und Grenzen (`quellen.py`)

| Quelle | Einheit | Zeilenende |
| --- | --- | --- |
| Leipzig, OpenSubtitles, GC4 | Satz bzw. Absatz im Fließtext | Leerzeichen; aufeinanderfolgende Zeilen werden verbunden |
| One Million Posts, Dortmunder Chat-Korpus | Nachricht bzw. Absatz einer Nachricht | harte Grenze, **kein Enter** (Entscheidung vom 14.11.2026) |

Quellenspezifisch:

- **OpenSubtitles:** Stichprobe: jeder 50. Block aus 1.000 Zeilen, damit Dialogfolgen erhalten bleiben. Dialogstriche am Zeilenanfang entfernt, Einblendungen ganz in Großbuchstaben verworfen. Falsch dekodiertes UTF-8 („Ã¤“ statt „ä“) wird repariert, ebenso eine Quelle, die „Ì“ für ü und „À“ für ä schreibt. Bekannte, nicht behobene Schwächen: Doppelte Untertitelversionen desselben Films werden nicht erkannt; OCR-Fehler älterer Untertitel („SeeIen“, „lch“) bleiben stehen, sie betreffen in der Stichprobe rund 2.500 Wörter (etwa 0,003 % der Zeichen).
- **GC4:** Stichprobe: jedes 40. Dokument, nur Dokumente mit `language_score > 0.98`.
- **One Million Posts:** Titel und Text je Beitrag, HTML-Entitäten aufgelöst; Absätze innerhalb eines Beitrags sind eigene Einheiten.
- **Dortmunder Chat-Korpus:** nur getippte Nachrichten (`utterance`, `action`), keine Systemmeldungen. Nicht wohlgeformte XML-Dateien werden repariert oder übersprungen (siehe Prüfbericht).

Stichproben sind deterministisch: Gleiche Eingabe und gleiche Parameter ergeben dieselben Zählungen.
