# Tastaturen

Datenbank physischer Tastaturen: Bauform, Tastenzahl, Versatz, Daumentasten und, wo eine Quelle sie liefert, die Position jeder einzelnen Taste. Sie ist die Grundlage, um Layouts gegen echte Geometrien zu prüfen und um Referenz-Tastaturen für den Benchmark auszuwählen.

Stand: 17.11.2026

## Inhalt

| Quelle | Einträge | Mit Tastenpositionen | Was sie liefert |
| --- | --- | --- | --- |
| [QMK Firmware](https://github.com/qmk/qmk_firmware) | 3.764 | 9.064 Layouts | Tastatur-Definitionen (`keyboard.json`, geerbte `info.json`) mit Position, Größe und Drehung jeder Taste je Layout-Makro; Hersteller, Prozessor, Split-Angabe |
| [Vial](https://github.com/vial-kb/vial-qmk) | 153 | 191 Layouts | nur Tastaturen, die im QMK-Stand fehlen |
| [ZMK Firmware](https://github.com/zmkfirmware/zmk) | 106 | 83 Layouts | Boards und Shields (`*.zmk.yml`) und physische Layouts (`zmk,physical-layout`) |
| [splitKbCompare](https://github.com/jhelvy/splitKbCompare) | 63 | – | kuratierte Split-Tastaturen mit Tastenzahl, Versatz, Bauart, Schaltern, Bezugsquelle |
| [golem.hu](https://golem.hu/boards/) | 452 | – | Sammlung von Split- und gewinkelten Einteilern bis etwa 2021: Entwickler, Tastenzahl, Versatz, Funk, Verfügbarkeit, Jahr, Tags |
| [KeymapDB](https://keymapdb.com/) | 150 | – | dokumentierte persönliche Keymaps; Tastatur, genutzte Tastenzahl, Home-Row-Mods, Buchstaben auf dem Daumen, Kombos, Ebenen |
| eigene Recherche (`manuell.json`) | 36 | – | kommerzielle Tastaturen mit eigener Firmware und neuere Projekte, die in keiner der Quellen stehen; jede Angabe mit Beleg-URL |
| **zusammen** | **4.724** | **9.339 Layouts, 602.829 Tasten, 3.710 verschiedene Geometrien** | |

Dieselbe physische Tastatur kann in mehreren Quellen stehen, etwa das Voyager in QMK, KeymapDB und der eigenen Recherche. Die Tabelle `verweis` hält Kandidaten für solche Paare fest. Sie beruhen auf gleichem Namen und sind nicht geprüft.

## Erste Befunde

- 1.111 Layouts von 819 Tastaturen sind geometrisch geteilt, 139 davon haben ein Layout mit höchstens 36 Tasten.
- Kleine Splits folgen wenigen Rastern (je Hälfte, aus den QMK-Layoutnamen):

  | Raster | Tastaturen |
  | --- | --- |
  | 3×5 + 3 Daumen | 51 |
  | 3×6 + 3 Daumen | 34 |
  | 3×5 + 2 Daumen | 23 |
  | 4×6 + 5 Daumen | 10 |
  | 3×6 + 5 Daumen | 9 |

  Sörens 32-Tasten-Belegung (3×5 + 1 Daumen) passt auf alle 3×5-Tastaturen.
- Mit 30 Tasten oder weniger gibt es als Split fast nur Steno- und Akkord-Tastaturen (Georgi, CHORD ZERO, The Uni) und Einzelprojekte wie das Battoota oder The Midge.
- Laut KeymapDB nutzen viele Leute auf größeren Tastaturen nur 30 bis 34 Tasten, etwa auf dem Corne.

## Grenzen

- **QMK und Vial** beschreiben vor allem Tastaturen, deren Firmware jemand eingereicht hat. Kommerzielle Tastaturen mit eigener Firmware fehlen dort: Dygma, UHK, Kinesis Advantage2 und 360 SmartSet, Logitech, Microsoft.
- **golem.hu** wird seit etwa 2021 kaum fortgeführt. Neuere Projekte erscheinen auf [kbd.news](https://kbd.news/), dort aber als Fließtext ohne strukturierte Angaben (siehe „Offen“).
- **KeymapDB** nennt die Zahl der Tasten, die eine Keymap nutzt, nicht die physische Tastenzahl. Ein Corne steht dort mit 30, 32 oder 36 Tasten.
- **Abgeleitete Werte** sind Heuristiken: `geteilt_geometrisch`, `raster_*` und `daumen_*` werden aus den Tastenpositionen berechnet. Das Raster ist verlässlich, wo es aus dem Layoutnamen stammt (`raster_quelle = 'name'`). Bei gespreizten Spalten oder tief sitzenden kleinen Fingern liegt die Heuristik oft daneben.
- **Eigene Recherche:** Viele Herstellerseiten haben die Abrufe gedrosselt (HTTP 429). Übernommen ist nur, was auf einer gelesenen Seite stand. Die Liste `offen` in `manuell.json` nennt die Tastaturen, die noch fehlen.

## Schema

| Tabelle | Inhalt |
| --- | --- |
| `quelle` | je Quelle URL, Stand (Commit oder Abrufdatum), Lizenz |
| `tastatur` | ein Eintrag je Tastatur und Quelle: Name, Hersteller, URL, geteilt, drahtlos, Tastenzahl laut Quelle, Versatz, Verfügbarkeit, Jahr, Firmware, Schalter; weitere Angaben als JSON in `merkmale` |
| `layout` | je Tastatur die Layout-Varianten mit abgeleiteten Werten: Tastenzahl, geteilt, Tasten je Hälfte, Raster und Daumen je Hälfte, Ausdehnung, Fingerabdruck der Geometrie (`signatur`) |
| `taste` | je Layout jede Taste: `x`, `y`, `w`, `h` in Tasten-Einheiten (KLE-Konvention: linke obere Ecke vor der Drehung), Drehung `r` in Grad um `rx`, `ry`, Mittelpunkt nach Drehung `cx`, `cy`, Matrix-Position, Beschriftung |
| `verweis` | Kandidaten für dieselbe Tastatur in verschiedenen Quellen |
| `meta` | Erzeugungsdatum und Bericht des Aufbaus |

ZMK gibt Positionen in Hundertstel-Tasten und Drehungen in Hundertstel-Grad an; sie werden beim Einlesen auf Tasten-Einheiten und Grad umgerechnet.

Beispiel: alle geteilten Tastaturen mit 3×5-Raster und Daumentasten:

```sql
SELECT t.quelle, t.quell_id, t.name, l.name, l.tasten, l.raster_links
FROM layout l JOIN tastatur t ON t.id = l.tastatur_id
WHERE l.geteilt_geometrisch = 1 AND l.raster_links LIKE '3x5+%'
ORDER BY l.tasten;
```

## Neu aufbauen

```sh
python3 tastaturen/skripte/quellen_laden.py      # Quellen nach ~/keyboard/tastatur-quellen/ (Stand aus quellen.json)
python3 tastaturen/skripte/datenbank_bauen.py    # tastaturen/tastaturen.sqlite und export/*.csv
```

Die Datenbank (`tastaturen.sqlite`, rund 46 MB) ist nicht im Repository, weil sie vollständig aus den gepinnten Quellen entsteht. Im Repository liegen die Übersichten `export/tastaturen.csv` (eine Zeile je Tastatur und Quelle) und `export/layouts.csv` (eine Zeile je Layout, ohne Einzeltasten).

Der Abruf mit `quellen_laden.py` wurde am 17.11.2026 in einem leeren Ordner geprüft und hat dieselben Stände ergeben.

## Lizenzen

Übernommen werden Fakten (Tastenzahl, Positionen, Bauart) und Links, keine Beschreibungstexte oder Bilder.

| Quelle | Lizenz |
| --- | --- |
| QMK, Vial | GPL-2.0-or-later |
| ZMK | MIT |
| splitKbCompare | MIT |
| KeymapDB | GPL-3.0 |
| golem.hu | ohne Angabe |

Vor einer Veröffentlichung der Datenbank prüfen wir je Quelle, ob die Übernahme der Fakten zulässig ist und wie sie zu nennen ist.

## Offen

- Fehlende Tastaturen aus `manuell.json` → `offen` nachtragen, sobald die Herstellerseiten erreichbar sind; dazu Keyboardio Model 100 und Atreus.
- kbd.news als Quelle für Tastaturen seit 2021: Liste der Artikel mit Titel, Kurzbeschreibung und Datum; Fakten nur nach Prüfung
- Ergogen-Projekte (wie das Battoota) haben ihre Geometrie in YAML. Ein Leser dafür würde Tastaturen ohne Firmware-Eintrag erschließen.
- Verweise zwischen Quellen prüfen und zu einer Tastatur-Identität zusammenführen
- Raster-Heuristik für gespreizte Tastaturen verbessern
