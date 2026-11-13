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
| [`soeren-gasch/keyboard_corpus`](https://github.com/soeren-gasch/keyboard_corpus) | Text-Korpora, auf denen das Layout beruht | offen: noch nicht gesichtet |
| [`soeren-gasch/keyboard_layout_optimizer`](https://github.com/soeren-gasch/keyboard_layout_optimizer) | Fork des [Optimizers von Dario Götz](https://github.com/dariogoetz/keyboard_layout_optimizer) (Rust), bewertet Layouts anhand von Uni-, Bi- und Trigrammen | gesichtet: Fork liegt 11 Commits hinter dem Original; der eigene Beitrag (N-Gramme für ActionScript) ist upstream gemergt |

Offen ist noch, wie die Korpora gewichtet werden (Anteil Deutsch, Englisch, Code) und welche Kriterien beim Entwurf zählten.

## Struktur

Geplant, Ordner entstehen erst, wenn sie gebraucht werden:

```
keyboard-layout/
  README.md            Einstieg und Index (diese Datei)
  AGENTS.md            Regeln für Agenten
  .claude/             Einstellungen für Claude Code
  oryx/                Schnappschüsse der Oryx-Revisionen (JSON und QMK-Quellcode)
  optimizer/           Tastatur- und Bewertungs-Konfigurationen für den Optimizer
  analyse/             Skripte und Ergebnisse der Messungen
  entscheidungen/      Entscheidungslog, eine Datei je Entscheidung
```

## Oryx-Layout abrufen

Öffentliche Oryx-Layouts lassen sich ohne Anmeldung über die GraphQL-Schnittstelle lesen:

```sh
curl -s https://oryx.zsa.io/graphql -H 'Content-Type: application/json' -d '{
  "query": "query { layout(hashId: \"xmKwY\", geometry: \"voyager\", revisionId: \"latest\") { title revision { hashId title qmkVersion config zipUrl layers { position title keys } combos { keyIndices layerIdx trigger } } } }"
}'
```

`zipUrl` führt zum Download mit dem QMK-Quellcode (`keymap.c`, `config.h`, `rules.mk`).
