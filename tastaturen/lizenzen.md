# Lizenzen der Tastatur-Datenbank

Stand: 17.11.2026. Das ist eine Arbeitsgrundlage, keine Rechtsberatung. Vor der Veröffentlichung sollte jemand mit Kenntnis im Urheber- und Datenbankrecht drüberschauen.

## Was überhaupt geschützt ist

| Gegenstand | Schutz | Folge für uns |
| --- | --- | --- |
| **Einzelne Fakten** (Tastenzahl, Schaltertyp, „hat Bluetooth“) | kein Urheberrecht | frei übernehmbar, Quelle trotzdem nennen |
| **Texte, Bilder, Videos** (Beschreibungen, Fotos, Reviews) | Urheberrecht | übernehmen wir nicht; nur Link |
| **Dateien mit Gestaltungshöhe** (Tastatur-Definitionen, Ergogen-Konfigurationen, KLE-Layouts) | Urheberrecht nach der Lizenz der Datei möglich; ob bloße Tastenpositionen schutzfähig sind, ist offen | vorsichtshalber wie die Quelle lizenziert behandeln |
| **Datenbank als Ganzes** (Auswahl, Anordnung) | Urheberrecht am Datenbankwerk | eigene Auswahl/Anordnung nicht übernehmen |
| **Datenbank-Investition** in der EU | Datenbankherstellerrecht (Richtlinie 96/9/EG, 15 Jahre): schützt vor Entnahme **wesentlicher Teile**, auch wenn es nur Fakten sind | trifft golem.hu und KBD.news (Betreiber in Ungarn), Deskthority, EU-Shops: Wer fast alle Einträge einer solchen Sammlung übernimmt, braucht eine Erlaubnis |
| **Fremde Lizenz mit Bedingungen** (GPL, CC BY-SA, CC BY-NC) | Bedingungen gelten für das, was wir aus geschütztem Material ableiten | Lizenz je Datensatz mitführen |

## Unsere Quellen

| Quelle | Lizenz | Was wir übernehmen | Bedingung für die Veröffentlichung |
| --- | --- | --- | --- |
| QMK, Vial | GPL-2.0-or-later | Fakten, Tastenpositionen aus den Definitionen | Positionen vorsichtshalber unter GPL weitergeben (GPL-3.0-or-later möglich) und Quelle nennen |
| VIA-Definitionen | GPL-3.0-only | Fakten, Tastenpositionen (KLE) | Positionen unter GPL-3.0 weitergeben |
| KeymapDB | GPL-3.0-only | Fakten, Links | Fakten frei; Quelle nennen |
| ZMK | MIT | Fakten, Tastenpositionen | Copyright-Hinweis und MIT-Text beilegen |
| splitKbCompare | MIT | Tabellenzeilen | Copyright-Hinweis und MIT-Text beilegen |
| YAL's ergo keyboard list | CC BY 4.0 | Einträge | Namensnennung, Link, Änderungen kenntlich machen |
| Deskthority-Wiki | CC BY-SA 4.0 nur für Text ab 18.08.2026; ältere Inhalte ohne Lizenz; Rechte an Auswahl/Anordnung vorbehalten | Fakten aus Infoboxen | Fakten mit Link; für systematische Übernahme Erlaubnis einholen |
| golem.hu | keine Angabe | Fakten, Links (452 Einträge, also praktisch alles) | **Erlaubnis einholen** (Datenbankherstellerrecht) |
| KBD.news | keine Angabe | Fakten aus Tags und Specs, Links (1.807 Artikel) | **Erlaubnis einholen** |
| Reddit (über Arctic Shift) | Inhalte der Nutzer, Reddit-Nutzungsbedingungen | Repo-Links, Fakten aus Titeln | nur Fakten und Links; keine Titel wörtlich veröffentlichen |
| GitHub-Repositories | je Repository (MIT, GPL, CERN-OHL, CC BY, CC BY-NC …) | Metadaten | Metadaten frei; Lizenz je Repo anzeigen |
| Ergogen (berechnet) | je Repository | Tastenpositionen aus den Konfigurationen | Lizenz des Repos gilt für die Positionen; **CC BY-NC** (z. B. Battoota) verbietet kommerzielle Nutzung |
| Online-Shops, Herstellerseiten, Testberichte | keine Angabe | Fakten, Preis, Link mit Abfragezeitpunkt | Fakten mit Link; keine Texte und Bilder |
| eigene Recherche | wir entscheiden | eigene Zusammenstellung | – |

Die Quellen sind also tatsächlich unterschiedlich lizenziert. Eine einzige Lizenz für alles ginge nur, wenn wir die Bestandteile mit Bedingungen weglassen oder getrennt veröffentlichen.

## Lizenzen, die für uns infrage kommen

| Lizenz | Namensnennung | Weitergabe unter gleicher Lizenz (Share-Alike) | kommerzielle Nutzung | deckt Datenbankherstellerrecht ab | passt zu unseren Quellen | Einschätzung |
| --- | --- | --- | --- | --- | --- | --- |
| **CC0 1.0** | nein | nein | ja | ja (Verzicht) | nur für Eigenes und Fakten; nicht für GPL-, CC-BY- oder MIT-Bestandteile, deren Hinweise wir weitergeben müssen | maximal offen, aber wir dürften fremde Teile nicht so stellen |
| **CC BY 4.0** | ja | nein | ja | ja | passt zu YAL (CC BY), MIT, Fakten; **nicht** zu GPL-abgeleiteten Positionen; nicht zu CC BY-SA (Deskthority neu) | einfach und verbreitet; unser Vorschlag für Eigenes |
| **CC BY-SA 4.0** | ja | ja | ja | ja | passt zu YAL, MIT, Deskthority (neu); kann einseitig in GPL-3.0 übergehen, aber GPL-Material darf **nicht** in CC BY-SA | gut, wenn Bearbeitungen offen bleiben sollen |
| **ODbL 1.0** (+ DbCL für Inhalte) | ja | ja, für die Datenbank | ja | ja, eigens dafür geschrieben | wie CC BY-SA; bekannt durch OpenStreetMap | passt gut zu einer Datenbank; weniger bekannt außerhalb von Geodaten |
| **CDLA-Permissive-2.0** | nur Lizenztext beilegen | nein | ja | ja | ähnlich CC BY, sehr wenige Pflichten | einfach, aber wenig verbreitet |
| **CDLA-Sharing-1.0** | ja | ja | ja | ja | ähnlich ODbL | wenig verbreitet |
| **GPL-3.0-or-later** | ja (Hinweise) | ja (Copyleft) | ja | eher nicht gedacht für Daten | Pflicht für GPL-abgeleitete Tastenpositionen (QMK, Vial, VIA) | nur für diesen Teil sinnvoll |
| **CC BY-NC 4.0** | ja | nein | **nein** | ja | Pflicht für Ableitungen aus NC-Quellen | nur für NC-Datensätze |

Für den Programmcode der Seite und der Skripte: MIT oder Apache-2.0. Code und Daten werden getrennt lizenziert.

## Mögliche Modelle

| Modell | Aufbau | Vorteil | Nachteil |
| --- | --- | --- | --- |
| **A: eine Lizenz für alles** | z. B. alles unter CC BY-SA 4.0 | einfach | GPL-Positionen und NC-Daten passen nicht hinein; müssten entfallen |
| **B: Schichten nach Lizenz** (empfohlen) | `devices.json` mit Fakten und eigener Arbeit unter **CC BY 4.0**; `layouts-gpl.json` mit Positionen aus QMK/Vial/VIA unter **GPL-3.0-or-later**; `layouts-mit.json` (ZMK) unter MIT; Ergogen-Positionen je Repo-Lizenz, NC-Datensätze ausgewiesen; Quellenliste mit allen Nennungen | rechtlich sauber, jede Datei hat genau eine Lizenz | mehr Dateien; Nutzer müssen pro Datei hinsehen |
| **C: Lizenz je Datensatz** | jeder Datensatz trägt seine Lizenz (haben wir schon), die Seite filtert, z. B. „nur frei kommerziell nutzbar“ | maximal transparent | Exporte werden komplizierter; für Endnutzer schwer zu verstehen |
| **D: nur Fakten und Links, CC0** | keine Positionen, keine Texte; nur Facetten und Links | einfachste Weitergabe | Layout-Vorschau entfällt; Datenbankrecht von golem/KBD.news bleibt trotzdem zu klären |

**Empfehlung:** Modell B mit den Lizenzfeldern aus Modell C (sind schon in der Datenbank).

| Teil | Lizenz |
| --- | --- |
| Fakten und eigene Zusammenstellung | CC BY 4.0 |
| GPL-abgeleitete Tastenpositionen | GPL-3.0-or-later |
| ZMK-Positionen | MIT |
| Ergogen-Positionen | Lizenz des jeweiligen Repos; ohne erkennbare Lizenz nicht veröffentlichen |
| NC-Daten | gekennzeichnet |
| golem.hu und KBD.news | erst nach Zustimmung von Tamás Dövényi |
| Deskthority | bis zur Klärung nur Link und wenige Fakten |

## Eine Gesamtlizenz für alles?

Eine Lizenz für die ganze Datenbank muss mit **jeder** Quelle verträglich sein, deren Material wir weitergeben.

| Gesamtlizenz | Möglich? | Bedingung |
| --- | --- | --- |
| **GPL-3.0-or-later** | **ja, als einzige mit allen Bestandteilen** | QMK (GPL-2.0-or-later) darf unter GPL-3.0 weiter; VIA und KeymapDB sind GPL-3.0; MIT (ZMK, splitKbCompare), CC BY 4.0 (YAL) und CC BY-SA 4.0 (Deskthority, neue Texte) dürfen in GPL-3.0 eingehen. Ausgeschlossen bleiben CC-BY-NC-Daten (z. B. Battoota-Geometrie) und Quellen ohne Lizenz ohne Zustimmung (golem.hu, KBD.news, Shops: dort nur Fakten und Links). Nachteil: Die GPL ist für Software geschrieben; Pflichten wie „vollständiger Quelltext“ passen schlecht zu Daten, und viele Datennutzer meiden sie. |
| CC BY-SA 4.0 | nur ohne GPL-Bestandteile | Positionen aus QMK, Vial und VIA müssten wegfallen oder nur als Link auf die Quelldatei erscheinen; GPL-Material darf nicht in CC BY-SA. |
| ODbL 1.0 | nur ohne GPL-Bestandteile | wie CC BY-SA |
| CC BY 4.0 | nur ohne GPL- und ohne CC-BY-SA-Bestandteile | Positionen aus QMK/Vial/VIA weg; Deskthority nur Fakten (das tun wir ohnehin) |
| CC0 | nur ohne GPL-, CC-BY(-SA)- und MIT-Bestandteile, deren Hinweise wir weitergeben müssen | praktisch nur Fakten und eigene Arbeit |

**Ergebnis:** Soll es genau eine Lizenz sein, ist das GPL-3.0-or-later (mit NC-Daten ausgenommen). Wenn die Layout-Vorschau statt eigener Positionsdaten auf die Quelldateien verweist, ginge auch CC BY-SA 4.0 oder ODbL für alles. Modell B (Schichten) bleibt die sauberste Lösung, wenn mehrere Lizenzen akzeptabel sind.

## Offene Entscheidungen

1. Lizenz für Fakten und eigene Arbeit: CC BY 4.0 (Vorschlag), CC BY-SA 4.0 oder ODbL?
2. Unter welchem Namen werden eigene Beiträge genannt?
3. Datensätze ohne erkennbare Lizenz (manche Ergogen-Repos): nur verlinken oder ganz weglassen?
4. Anfragen an golem.hu/KBD.news und Deskthority stellen (Entwürfe unter `tastaturen/anfragen/`).
