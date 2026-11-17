# Gegenprüfung mit Vergleichsseiten

Stand: 17.11.2026. Abgeglichen wurden nur Modellnamen. Wertungen, Texte und Daten dieser Seiten übernehmen wir nicht, und sie erscheinen nicht als Fundstelle. Fehlende Modelle werden über Hersteller- oder Projektseiten belegt (Vorlage: `recherche-vorlage.md`).

## Vorgehen

| Seite | Abgerufen (UTC) | Was | robots.txt |
| --- | --- | --- | --- |
| [OCDevel: Best Ergonomic Split Keyboards](https://ocdevel.com/ergo/keyboards) | 2026-11-17 13:48 | eine Seite, Tabelle mit 42 Modellen (Marke, Modell) | erlaubt alles |
| [keeb-finder.com](https://keeb-finder.com/) | 2026-11-17 13:48–13:55 | Sitemap (Produktadressen) sowie die Filterseiten `filter/split`, `filter/split-wireless` und `filter/ergonomic` (3 Seiten): 124 Produkte | erlaubt alles |

Abgleich: Jeder Modellname wird normalisiert (`normname` aus `zusammenfuehren.py`) und gegen alle Datensatznamen der Datenbank gesucht. Rohdaten liegen nur lokal unter `~/keyboard/tastatur-quellen/gegenpruefung/`.

## Ergebnis

- **OCDevel:** 40 von 42 Modellen sind schon in der Datenbank. Svalboard, Keebio Chiri CE und Royal Kludge RKS70 wurden zunächst nicht erkannt, sind aber vorhanden.
- **keeb-finder:** 124 Produkte in den Split- und Ergo-Filtern. Die meisten sind bekannte Bausätze (Corne, Lily58, Sofle, ErgoDash, Cantor …) oder Keychron- und Alice-Tastaturen, die wir bereits haben. Mehrere 40-%-Tastaturen mit geteilter Leertaste stehen dort unter „ergonomic“; die sind für uns Stufe 3.

## Fehlende Modelle zur manuellen Recherche

| Nr. | Modell | Gefunden bei | Bauform laut Name | Vorschlag Dateiname |
| --- | --- | --- | --- | --- |
| 1 | Nulea RT07B | OCDevel | ergonomische Tastatur (Massenmarkt) | `nulea-rt07b.html` |
| 2 | Arteck HW315 | OCDevel | ergonomische Tastatur (Massenmarkt) | `arteck-hw315.html` |
| 3 | Ursa Major V2 | keeb-finder | Split, kabellos, Aluminium | `ursa-major-v2.html` |
| 4 | Filco Majestouch Xacro M3A | keeb-finder | Split | `filco-xacro-m3a.html` |
| 5 | Hare Works Two 40 | keeb-finder | einteilig, Zelt, Alice | `hare-works-two-40.html` |
| 6 | A72 Alice / A72 HE | keeb-finder | Alice, HE = Hall-Effekt | `a72-alice.html` |
| 7 | ABM066 (ACGAM, Cidoo) | keeb-finder | Alice 65 % | `abm066.html` |
| 8 | Feker Alice60 | keeb-finder | Alice 60 % | `feker-alice60.html` |
| 9 | Monka Alice67 Pro | keeb-finder | Alice | `monka-alice67.html` |
| 10 | Ajazz AKS068 Pro | keeb-finder | Alice-artig (prüfen) | `ajazz-aks068-pro.html` |
| 11 | IC Keylice (Alice-65-PCB) | keeb-finder | Alice 65 % | `ic-keylice.html` |
| 12 | Weikav Record (kabelgebunden, Gasket) | keeb-finder | Alice; Variante der vorhandenen Weikav Record Alice | `weikav-record-wired.html` |

Nicht aufgenommen (geteilte Leertaste, sonst normale 40-%-Tastaturen): KB40, Cheerz 40, Roly-Poly 40, 40-40 Low Profile (NiuNiu), V98.

## Auffällig beim Abgleich

Die Namenssuche hat einige Produkte nur zufällig „erkannt“ (z. B. Evanthe über das Wort „the key“). Die Liste oben ist deshalb um diese Fälle ergänzt: Evanthe und Keyboy Advanced 50 sind über Shops bereits in der Datenbank, Minimi40 über QMK.
