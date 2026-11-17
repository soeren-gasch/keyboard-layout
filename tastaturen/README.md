# Tastaturen

Datenbank physischer Tastaturen, vorbereitet für eine öffentliche Seite mit Facettensuche. Sie soll helfen, eine Tastatur auszuwählen und ein Tasten-Layout für eine konkrete Tastatur zu finden. Jede Angabe ist mit ihrer genauen Fundstelle und deren Lizenz belegt.

Stand: 17.11.2026

## Aufbau

```
Quellen (gepinnt in quellen.json)  ──►  Datensätze je Quelle  ──►  Facetten-Angaben mit Beleg  ──►  Geräte  ──►  export/
QMK, Vial, ZMK, splitKbCompare, YAL,   (genaue Fundstelle,          (Vokabular facetten.json,        (Dubletten
golem.hu, KBD.news, GitHub-Topics,      Lizenz, Abrufdatum)          Methode: quelle/abgeleitet)       zusammengeführt)
KeymapDB, eigene Recherche
```

| Datei | Inhalt |
| --- | --- |
| `quellen.json` | Manifest: je Quelle URL, gepinnter Stand, Lizenz, was übernommen wird, wie sie zu nennen ist |
| `facetten.json` | Vokabular der Filter mit deutschen und englischen Bezeichnungen |
| `manuell.json`, `manuell/*.yaml` | eigene Recherche, jede Angabe mit Beleg-URL (Format: `recherche-vorlage.md`) |
| `zusammenfuehrung.json` | manuelle Korrekturen beim Zusammenführen (verbinden, trennen) |
| `ergogen.json` | gefundene Ergogen-Konfigurationen je Repository mit Commit |
| `skripte/` | Laden, Lesen, Zusammenführen, Exportieren (siehe unten) |
| `export/` | CSV-Übersichten und `web/` für die Online-Seite |
| `tastaturen.sqlite` | die Datenbank, lokal, nicht im Repository (rund 67 MB) |

## Quellen und Lizenzen

| Quelle | Datensätze | Fundstelle je Datensatz | Lizenz der Quelle | Übernommen |
| --- | --- | --- | --- | --- |
| QMK Firmware | 3.764 | `keyboard.json` am gepinnten Commit, dazu geerbte `info.json` | GPL-2.0-or-later | Fakten aus den Definitionen, Tastenpositionen |
| VIA-Definitionen | 2.026 | Definitionsdatei am Commit | GPL-3.0-only | Name, Layout (KLE), Matrix |
| KBD.news | 1.807 | Artikel-URL | keine Angabe | nur Fakten (Tags, Specs) und Links, keine Texte, keine Bilder |
| Reddit r/ErgoMechKeyboards (über Arctic Shift) | 834 | erster Post, der das Repository verlinkt | keine Angabe (Inhalte der Nutzer) | Fundquelle: Fakten aus Titel und Repository, Link zum Post; keine Texte |
| Deskthority-Wiki | 798 | Seite in der verwendeten Version (`oldid`) | keine Angabe | Fakten aus der Infobox (Hersteller, Schalter, Tastenzahlen, Schnittstelle, Jahr) |
| GitHub-Topics | 726 | Repository-URL | je Repository (SPDX laut GitHub) | Metadaten (Name, Topics, Lizenz, Datum) |
| golem.hu | 452 | Detailseite | keine Angabe | nur Fakten und Links |
| YAL's ergo keyboard list | 424 | Zeile in `docs/keyboards.js` bzw. `docs/rowstag.js` am Commit | CC-BY-4.0 | Einträge (Fakten und Links, keine Bilder, keine Notizen) |
| Ergogen (berechnet) | 337 | Konfigurationsdatei am Commit | je Repository | mit Ergogen 4.2.1 bzw. 3.1.2 berechnete Tastenpositionen |
| Vial | 153 | wie QMK | GPL-2.0-or-later | nur Tastaturen ohne QMK-Gegenstück |
| KeymapDB | 150 | Keymap-Seite und Datei am Commit | GPL-3.0-only | Fakten und Links |
| ZMK Firmware | 106 | `*.zmk.yml` und Layout-Dateien am Commit | MIT | Metadaten, physische Layouts |
| splitKbCompare | 71 | Zeile in `keyboards.csv` am Commit (`#L<n>`) | MIT | Tabellenzeile |
| eigene Recherche | 36 | Herstellerseite | CC-BY-4.0 (vorgeschlagen) | eigene Zusammenstellung belegter Fakten |

Rohdaten der Quellen (Texte, Bilder, vollständige Dateien) liegen nur lokal unter `~/keyboard/tastatur-quellen/` und werden nicht veröffentlicht. Die Spalte `datensatz.roh` bleibt in der lokalen Datenbank und geht nicht in den Export.

**Vor einer Veröffentlichung zu klären:** die Lizenz der zusammengestellten Daten (Vorschlag: CC BY 4.0 für Eigenes, Fakten aus GPL-Quellen mit Nennung) und ob golem.hu und KBD.news der Übernahme von Fakten zustimmen. Beide geben keine Lizenz an.

## Facetten

Vokabular in `facetten.json`, Typen: Auswahl, Mehrfachauswahl, Zahl/Bereich, Jahr.

| Facette | Werte |
| --- | --- |
| Split-Tastatur | ja, zusammensteckbar (Hälften greifen ineinander und bilden einen Block, z. B. Dygma Raise 2), einteilig mit geteiltem Tastenfeld, nein |
| Anzahl physischer Tasten, Tasten je Hälfte, Daumentasten je Hand | Zahl bzw. Bereich |
| Raster je Hand | z. B. 3x5, 3x6, 4x6 |
| Tastenanordnung | Spaltenversatz, ortholinear, Reihenversatz, Mulde, radial, Alice, sonstige; dazu „gespreizt“ |
| Maus integriert, Art | ja, optional, nein; Trackball, Trackpad, Trackpoint, Joystick |
| Tasten-Interface, Montage | MX, Choc v1, Choc v2, Gateron LP, Alps, Topre, magnetisch, optisch, Schere, Membran, Knickfeder, proprietär; Hotswap, gelötet, fest |
| Bauhöhe | flach, normal |
| Wireless, Technik | ja, optional, nein; Bluetooth, 2,4 GHz, WLAN, sonstiger Funk |
| Energieversorgung | Kabel, Akku fest, Akku wechselbar, AA, AAA, Knopfzelle, Solar |
| Firmware | QMK, ZMK, KMK, RMK, Vial, VIA, Kaleidoscope, UHK, proprietär |
| Offene Hardware, Hardware-Lizenz | ja, nein; SPDX |
| Bezug | Selbstbau, Bausatz, fertig, Gruppenbestellung, Prototyp, eingestellt |
| Zahlenreihe, Drehregler, Display, Tenting | ja, optional, nein |
| Jahr, Preis, Hersteller | – |
| In Keymaps genutzte Tasten | Zahl (KeymapDB) |

Jede Angabe in der Tabelle `angabe` hat:

- eine **Methode**: `quelle`, wenn sie so in der Quelle steht, oder `abgeleitet`, wenn sie berechnet ist, zum Beispiel die Tastenzahl aus Tastenpositionen;
- einen **Beleg**: das Feld, den Tag, die Specs-Zeile oder den Layoutnamen, aus dem sie stammt.

„Nein“ wird nur gesetzt, wenn eine Quelle es sagt. Fehlt eine Angabe, ist sie unbekannt.

## Zusammenführen der Dubletten

Ein **Gerät** ist eine physische Tastatur samt Revisionen und Varianten, zum Beispiel Corne mit 36 und 42 Tasten. Datensätze werden nach drei Regeln verbunden; jede Zuordnung speichert ihre Regel.

1. **familie:** QMK/Vial-Pfad ohne Revisions-, Controller- und Variantenteile am Ende, etwa `splitkb/kyria/rev3` → `splitkb/kyria`.
2. **repo:** dasselbe Projekt-Repository und dazu verwandter Name oder gleiche Tastenzahl. Sammel-Repos wie `gtips/reviung` werden so nicht zu einem Gerät.
3. **name:** gleicher normalisierter Name, mit und ohne Herstellerpräfix, bei verträglicher Tastenzahl. Ein Name, der nur noch die Marke enthält, verbindet nichts.

Verträglichkeit wird gegen die ganze bisherige Gruppe geprüft, nicht nur gegen einen Partner. So ketten Datensätze ohne Tastenzahl keine verschiedenen Tastaturen zusammen.

Beim Verdichten der Facetten gewinnt bei Auswahl-Facetten die vertrauenswürdigste Quelle in dieser Reihenfolge: eigene Recherche, YAL, splitKbCompare, golem.hu, KBD.news, ZMK, QMK, Vial, GitHub, KeymapDB. Abweichende Werte stehen unter `konflikte`. Mehrfach-Facetten werden vereinigt, Zahlen werden zu Bereichen.

Stand 17.11.2026: 8.261 Geräte aus 11.684 Datensätzen; 1.917 Geräte haben Angaben aus mehreren Quellen; 4.441 Geräte haben Tastenpositionen (11.702 Layouts, 739.392 Tasten). Gerätename ist der häufigste Name über alle Quellen.

## Export für die Online-Seite

`export/web/`:

| Datei | Inhalt |
| --- | --- |
| `devices.json` | je Gerät: ID, Name, Hersteller, Facetten, Konflikte, Fundstellen (Quelle, URL, Lizenz, Abrufdatum, Zuordnungsregel), Projekt-Links, Hauptlayout |
| `layouts.json` | Hauptlayout je Gerät: Tasten als `[x, y, w, h, r, rx, ry]` in Tasten-Einheiten (KLE-Konvention), zum Zeichnen einer Vorschau |
| `facets.json` | Filter-Vokabular mit Anzahl Geräte je Wert |
| `sources.json` | alle Quellen mit Stand, Lizenz, Lizenztext, Nutzung und Nennung |

Der Export ist englisch (die spätere Seite ist englisch): Schlüssel und Werte stammen aus den `key`-Feldern in `facetten.json`, Quellenbeschreibungen aus `beschreibung_en`/`nutzung_en` in `quellen.json`. Datenbank, Skripte und Doku bleiben deutsch.

Die Dateien sind für eine statische Seite mit clientseitiger Facettensuche gedacht. `export/geraete.csv`, `export/datensaetze.csv` und `export/layouts.csv` sind diff-bare Übersichten für das Repository.

## Neu aufbauen

```sh
python3 tastaturen/skripte/quellen_laden.py              # alle Quellen (kbd.news: einige Stunden)
python3 tastaturen/skripte/datenbank_bauen.py            # Datenbank und Export
python3 tastaturen/skripte/ergogen_suchen.py             # Ergogen-Dateien in allen Repositories der Datenbank
python3 tastaturen/skripte/ergogen_berechnen.py          # Tastenpositionen berechnen (Node.js), danach datenbank_bauen.py erneut
```

| Skript | Aufgabe |
| --- | --- |
| `basis.py` | Schema, Geometrie (Mittelpunkte, Split, Raster, Versatz), Schreiber mit Herkunftsnachweis |
| `leser.py` | Leser für QMK, Vial, ZMK, VIA, splitKbCompare, YAL, golem.hu, Deskthority, GitHub-Topics, Reddit, Ergogen, KeymapDB, eigene Recherche |
| `ergogen_berechnen.py` | Ergogen-Konfigurationen mit Ergogen 4/3 berechnen (braucht Node.js) |
| `kbdnews.py` | Leser für KBD.news (Rubrik, Tags, Specs, Links) |
| `zusammenfuehren.py` | Dubletten zu Geräten, Verdichten der Facetten |
| `web_export.py` | Export für die Online-Seite und CSV |
| `ergogen_suchen.py` | Ergogen-Konfigurationen finden und mit Commit festhalten |

## Werkzeuge

| Werkzeug | Version | Ort | Zweck |
| --- | --- | --- | --- |
| nvm | v0.40.8 (Git-Tag) | `~/.nvm`, eingebunden in `~/.profile` und `~/.bashrc` | mehrere Node.js-Versionen nebeneinander (`nvm install <version>`, `nvm use <version>`) |
| Node.js | v26.13.1 (LTS, Standard) | über nvm; Prüfsumme beim Download von nvm geprüft | Ergogen und künftige Recherchen |
| Ergogen | 4.2.1 und 3.1.2 | `~/keyboard/werkzeuge/ergogen4`, `~/keyboard/werkzeuge/ergogen3` (npm, `--ignore-scripts`) | Tastenpositionen aus Ergogen-Konfigurationen |

Installiert für den Benutzer `decaswift` auf dem Hub (17.11.2026), ohne Root-Rechte. Eine systemweite Installation für alle Benutzer gehört in das Ansible-Playbook `decaswift-hub.yml` im Repository `soeren-gasch/infrastructure`.

## Grenzen

- **Abgeleitete Geometrie** ist heuristisch. Split, Raster, Daumentasten und Versatz werden aus Tastenpositionen berechnet. Das Raster ist verlässlich, wo es aus dem Layoutnamen kommt (`split_3x5_2`).
- **Ergogen:** Viele Konfigurationen beschreiben nur eine Hälfte; dann steht die Zahl unter „Tasten je Hälfte“. 50 Dateien ließen sich mit keiner der beiden Ergogen-Versionen berechnen oder enthalten Hilfsteile statt Tastaturen.
- **KBD.news-Specs** werden mit Mustern gelesen. Zum Beispiel wird „Choc“ ohne Version als Choc v1 gewertet.
- **KeymapDB** nennt die in einer Keymap genutzten Tasten, nicht die physischen.
- **Kommerzielle Tastaturen** sind lückenhaft; siehe `offen` in `manuell.json`.

## Offen

- weitere Quellen: Wikipedia „List of mechanical keyboards“ (CC BY-SA), 40% Club, Shopify-Produktlisten von Tastatur-Herstellern, weitere Subreddits
- Lizenz der Veröffentlichung festlegen, Nennung der eigenen Beiträge festlegen
