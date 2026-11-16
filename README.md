# Keyboard-Layout

Eigenes Tastaturlayout für Deutsch, Englisch und Programmieren, entwickelt auf einem ZSA Voyager und begrenzt auf 32 Tasten.

Dieses Repository ist der **Kanon** des Layouts: Ziele, Vorgaben, Messungen und Entscheidungen. Was hier nicht steht, gilt als unbekannt.

## Status

Stand: 13.11.2026

| | |
| --- | --- |
| Tastatur | ZSA Voyager, konfiguriert mit Oryx |
| Oryx-Layout | [`xmKwY`](https://configure.zsa.io/voyager/layouts/xmKwY/latest/0), Titel „soeren“ |
| Letzte Revision | `NjXvj` „replacing . by ,“ (QMK 24, Oryx-Option „german“) |
| Phase | Bestandsaufnahme: Datengrundlage sammeln, aktuelles Layout vermessen |

## Ziele und Vorgaben

1. **32 Tasten.** Je Hand 3 × 5 Tasten und 2 Daumentasten. Die Zahlenreihe und die äußeren Spalten des Voyager bleiben leer, damit das Layout später auf eine kleinere Tastatur passt.
2. **Drei Einsatzzwecke:** deutscher Text, englischer Text und Programmieren.
3. **Deutsches Betriebssystem-Layout (QWERTZ).** Die Tastatur sendet Keycodes, die erst mit dem deutschen OS-Layout die richtigen Zeichen ergeben.
4. **Belege statt Gefühl.** Jede Änderung wird vorher an den Korpora gemessen und im Entscheidungslog begründet.

## Aktuelles Layout

Basis-Ebene (Ebene 0):

```
 X  F  L  P  B   |  Ä  Q  O  ,  Ö
 C  S  N  T  G   |  J  ␣  A  I  U
 M  W  V  D  K   |  ß  Z  Ü  Y  H
          E  ·   |  ·  R              (Daumen, · = frei)
```

| Funktion | Belegung |
| --- | --- |
| Home-Row-Mods | Shift auf N und A, Ctrl auf T und Leertaste, GUI auf G und J |
| Ebenen-Tasten (halten) | S → 2, I → 1, C → 4, U → 3 |
| Ebenen 1 und 2 | dieselbe Symbol-Ebene, gespiegelt, damit sie immer mit der Gegenhand erreichbar ist |
| Ebenen 3 und 4 | links Navigation (Pfeile, Pos1/Ende, Bild, Backspace, Entf, Esc, Tab, Enter), rechts Ziffernblock; gespiegelt wie 1 und 2 |
| Timing | Oryx-Standard, kein eigener Tapping Term, kein Chordal Hold oder Flow Tap |
| Combos | keine |

### Bekannte Probleme

Aus der ersten Einschätzung vom 13.11.2026:

- [ ] **Punkt fehlt.** Seit Revision `NjXvj` ist `.` auf keiner Ebene belegt.
- [ ] **Undo sendet Redo.** `KC_PC_UNDO` ist `Ctrl` + US-`Z`; mit deutschem OS-Layout wird daraus Ctrl+Y.
- [ ] **Ziffern hängen an NumLock.** Alle Ziffern sind Keypad-Codes; `KC_KP_COMMA` verhält sich je nach Betriebssystem unterschiedlich.
- [ ] **Keine Alt- oder AltGr-Taste.**
- [ ] **Leertaste als Mod-Tap auf dem rechten Zeigefinger.** Risiko für versehentliches Ctrl, keine Tastenwiederholung.
- [ ] **Backspace, Enter, Esc und Tab nur auf Ebenen**, Backspace nur mit gehaltenem kleinen Finger.
- [ ] **Buchstaben-Platzierung prüfen:** H auf der schwächsten Position, Q auf einer guten.

## Datengrundlage

| Quelle | Inhalt | Status |
| --- | --- | --- |
| [`soeren-gasch/keyboard_corpus`](https://github.com/soeren-gasch/keyboard_corpus) | Übungs-Wortlisten zum Erlernen des Layouts (`customLayout-soeren/words-german/`, nur Deutsch): 18 Stufen, die Buchstaben in der Reihenfolge der Tastenpositionen freischalten, plus eine Gesamtliste mit rund 510.000 Wörtern; eindeutige Wörter ohne Häufigkeiten, Stand 12.09.2024 | gesichtet; eignet sich zum Üben, nicht zum Vermessen |
| Korpora, aus denen das Layout entworfen wurde | Häufigkeiten bzw. N-Gramme für Deutsch, Englisch und Code | offen: Quelle und Gewichtung unbekannt |
| [`korpora/deutsch/`](korpora/deutsch/README.md) | neu zusammengestellte deutsche Korpora: förmlich (Leipzig), gesprochen (OpenSubtitles), informell (GC4, One Million Posts, Dortmunder Chat-Korpus) | Originale per Skript ladbar (4,6 GB, nicht im Repo); N-Gramme je Quelle unter [`korpora/ngramme/`](korpora/ngramme/README.md), Mischung `de-standard` unter `korpora/mischungen/` |
| [`korpora/englisch/`](korpora/englisch/README.md) | englische Korpora, britisches Englisch bevorzugt, US-Englisch enthalten: förmlich (Leipzig, UK Hansard), gesprochen (OpenSubtitles, CABNC, OANC), informell und technisch (Ubuntu IRC, Reddit, E-Mails, StackExchange ohne Code) | 14 Quellen einzeln gezählt (N-Gramme unter `korpora/ngramme/en-*`), Mischung `en-standard`; Originale (21 GB) per Skript ladbar, nicht im Repo |
| [`korpora/code/`](korpora/code/README.md) | Quelltext aus 98 freien Repositories für PHP/Laravel, Vue, JavaScript, Java und SQL (Sörens Stack) | 5 Quellen einzeln gezählt (`korpora/ngramme/code-*`), Mischung `code-standard`; Originale (1,3 GB) per Skript ladbar, nicht im Repo; eigener Code von Sören steht noch aus |
| [`dariogoetz/keyboard_layout_optimizer`](https://github.com/dariogoetz/keyboard_layout_optimizer) | Optimizer von Dario Götz (Rust), bewertet Layouts anhand von Uni-, Bi- und Trigrammen; enthält Sörens N-Gramme für ActionScript (`ngrams/code_actionScript`, PR #74) | gesichtet; der frühere Fork wird nicht mehr gebraucht |

Offen ist noch, wie Deutsch, Englisch und Code untereinander gewichtet werden und welche Kriterien beim Entwurf zählten. Innerhalb einer Sprache legt ein Rezept unter `korpora/mischungen/` die Gewichte fest (`de-standard`, `en-standard`, `code-standard`); sie lassen sich ändern, ohne neu zu zählen.

## Struktur

Geplant, Ordner entstehen erst, wenn sie gebraucht werden:

```
keyboard-layout/
  README.md            Einstieg und Index (diese Datei)
  AGENTS.md            Regeln für Agenten
  .claude/             Einstellungen für Claude Code
  korpora/             Korpora je Sprache: Recherche, Manifest (quellen.json), Dummy-Dateien;
                       skripte/ (Download, Aufbereitung), ngramme/ (je Quelle), mischungen/ (gewichtet)
  oryx/                Schnappschüsse der Oryx-Revisionen (JSON und QMK-Quellcode)
  optimizer/           Build-Anleitung, Tastatur- und Bewertungs-Konfigurationen, Ergebnisse
  analyse/             Skripte und Ergebnisse der Messungen
  entscheidungen/      Entscheidungslog, eine Datei je Entscheidung
```

## Original-Korpora (nicht im Repository)

Die großen Original-Korpora (Deutsch zusammen 4,6 GB, Englisch 21 GB, Code 1,3 GB) liegen **nicht** im Repository. Stattdessen gibt es:

- ein **Manifest** je Sprache (`korpora/<sprache>/quellen.json`) mit URL, SHA-256 und Größe jeder Datei,
- **Dummy-Dateien** an den Pfaden der Originale (`korpora/<sprache>/original/...`): gleiches Format, aber nur 5 bis 10 erfundene Beispiel-Einträge. Damit laufen alle Skripte nach einem frischen Klon, nur eben auf Beispieldaten,
- das Skript `korpora/skripte/herunterladen.py`, das die Dummys lokal durch die vollen Originale ersetzt. Die Ersetzung führt git nicht als Änderung (`skip-worktree`).

```sh
python3 korpora/skripte/herunterladen.py --status   # was ist Dummy, was ist das Original?
python3 korpora/skripte/herunterladen.py            # alle Originale laden und prüfen
```

Einzelheiten und Fallstricke: [`korpora/skripte/README.md`](korpora/skripte/README.md).

## Oryx-Layout abrufen

Öffentliche Oryx-Layouts lassen sich ohne Anmeldung über die GraphQL-Schnittstelle lesen:

```sh
curl -s https://oryx.zsa.io/graphql -H 'Content-Type: application/json' -d '{
  "query": "query { layout(hashId: \"xmKwY\", geometry: \"voyager\", revisionId: \"latest\") { title revision { hashId title qmkVersion config zipUrl layers { position title keys } combos { keyIndices layerIdx trigger } } } }"
}'
```

`zipUrl` führt zum Download mit dem QMK-Quellcode (`keymap.c`, `config.h`, `rules.mk`).
