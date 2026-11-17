# Online-Seite (Entwurf)

Englische Seite zur Tastatur-Datenbank. Arbeitstitel „Keyboard Index“, Veröffentlichung unter Sören Gasch. **Entwurf, nicht veröffentlicht:** Lizenz der Zusammenstellung und die Zustimmung von golem.hu und KBD.news sind noch offen (siehe `../lizenzen.md`).

```sh
python3 tastaturen/skripte/datenbank_bauen.py   # Datenbank und export/web/*.json
python3 tastaturen/skripte/seite_bauen.py       # Seite nach tastaturen/web/dist/ (nicht im Repo)
python3 tastaturen/web/vorschau.py              # http://localhost:8765/ mit gzip wie auf dem Server
```

| Datei | Inhalt |
| --- | --- |
| `style.css` | ein Stylesheet für alles; Farben als Variablen, hell/dunkel |
| `app.js` | Facettensuche im Browser (ohne Bibliotheken) |
| `vorschau.py` | lokaler Server, liefert die `.gz`-Dateien aus |
| `../skripte/seite_bauen.py` | erzeugt `dist/`: `index.html`, zwei Index-Dateien, eine Seite je Tastatur, Quellen, Über |

## Zielgruppe und Leitlinien

Technikaffine Menschen, Programmierer, Tastatur-Nerds. Daraus folgt: dichte Informationen statt Bilder, Zahlen in Tabellenziffern, Tastatursteuerung (`/` springt in die Suche, `Esc` schließt), teilbare URLs mit dem ganzen Filterzustand, Herkunft jeder Angabe sichtbar.

## Ladezeit: 56k-Modem als Maßstab

Ein 56k-Modem schafft real etwa 5–6 KB/s bei 150–200 ms Latenz.

| Schritt | Datei | Größe (gzip) | Zeit bei 56k | Ergebnis |
| --- | --- | --- | --- | --- |
| 1 | `index.html` (CSS, Skript, Filter mit Zählungen, 30 Treffer, alles inline) | ~19 KB | ~3–4 s | Seite vollständig lesbar, Links funktionieren auch ohne JavaScript |
| 2 | `idx.<hash>.json` Stufe A | ~49 KB | +8–9 s | Filter und Suche über die 2.600 am besten belegten Tastaturen |
| 3 | `idx.<hash>.json` Stufe B | ~102 KB | +17–20 s | Filter über alle 8.800; Ergebnisse werden still aktualisiert |
| bei Klick | `k/<slug>.html` | ~1–4 KB | < 1 s | Detailseite mit Tastenbild (SVG) |

Maßnahmen: keine Webfonts, keine Bilder, keine Bibliotheken; ein Request bis zum ersten vollständigen Bild; vorkomprimierte Dateien; Index-Dateien mit Hash im Namen, also unbegrenzt cachebar; Index spaltenweise als Base64-Zeichenketten (komprimiert sehr gut); Slugs werden aus dem Namen abgeleitet, nur Ausnahmen stehen im Index; einwertige Facetten ohne Kombinationstabelle. Das erste Bild passt nicht ganz in die 14-KB-Grenze des ersten TCP-Fensters ([Tune The Web](https://tunetheweb.com/blog/critical-resources-and-the-first-14kb), [endtimes.dev](https://endtimes.dev/why-your-website-should-be-under-14kb-in-size/)); das kostet bei 56k einen zusätzlichen Roundtrip (~0,2 s).

## Welches Bedienelement wofür

| Anwendungsfall | Element | Begründung |
| --- | --- | --- |
| Werte einer Facette, auch „nur einer möglich“ (Split: ja/zusammensteckbar/…) | **Checkboxen**, Mehrfachauswahl, ODER innerhalb, UND zwischen Facetten | Nutzer wollen „Split oder zusammensteckbar“; Baymard: fehlende Mehrfachauswahl ist ein häufiger Fehler ([Baymard](https://baymard.com/blog/allow-applying-of-multiple-filter-values)) |
| kurze Wertelisten (≤ 5, kurze Namen) | Checkbox als **Pill** nebeneinander | spart Höhe auf dem Handy, Zielgröße 40 px |
| lange Listen (Firmware, Keycap-Profil, Hersteller …) | Checkbox-Liste, erst die 8 häufigsten, „Show all“, ab 15 Werten **Suchfeld in der Facette** | lange Listen sind sonst nicht überschaubar |
| Zahlen (Tastenzahl, Daumentasten, Jahr, Gewicht) | **zwei Zahlenfelder** (Min/Max) plus **Bereichs-Pills** mit Anzahl; kein Schieberegler | Schieberegler sind ungenau, vor allem mit dem Finger; Baymard empfiehlt Eingabefelder ([Baymard: Slider](https://baymard.com/blog/slider-interfaces)) |
| sofort wirksame Einstellung (Farbschema) | Knopf, der Auto/Hell/Dunkel durchschaltet | Schalter nur für sofortige Wirkung ([NN/g](https://www.nngroup.com/videos/checkboxes-vs-switches-forms/)); drei Zustände passen nicht auf einen Schalter |
| wichtigste Filter | **Schnellfilter** als Pills über der Liste (Split, Spaltenversatz, Ortho, Funk, flach, Hot-swap, Zeigegerät, fertig kaufbar, Open Source, Layout-Vorschau) | ein Tippen statt Filterpanel |
| gesetzte Filter | **Chips** über der Liste, je mit ✕, ab zwei „Clear all“ | ohne Übersicht müssen Handy-Nutzer zum Entfernen das Panel öffnen ([Baymard](https://baymard.com/blog/how-to-design-applied-filters)) |
| Sortierung | natives `<select>` | wenige Optionen, auf dem Handy der System-Picker |
| Freitext | Suchfeld oben, sucht in Name, Hersteller, Slug; alle Wörter müssen passen | |
| Filter auf dem Handy | **Vollbild-Ebene** mit festem Fuß: „Clear“ und „Show N keyboards“ | eigene Ebene statt gequetschter Seitenleiste; die Zahl im Knopf zeigt vor dem Schließen, was kommt ([Baymard](https://baymard.com/blog/ecommerce-filter-ui)) |
| Filter am Rechner | Seitenleiste, wirkt sofort | |
| Facetten-Gruppen | einklappbar (`<details>`), die drei wichtigsten offen, gewählte Werte im Kopf | allgemeine Facetten oben, spezielle unten (NN/g) |
| Zählungen | Anzahl neben jedem Wert, live; Werte ohne Treffer ausgegraut | wirkungsvollste Verbesserung eines Filters ([Baymard](https://baymard.com/guidelines/467-indicating-the-number-of-matches-for-filtering-options)) |
| unbekannte Werte | eigener Wert „Unknown“ bzw. „Include unknown“; unter jeder Facette „Known for N of M“ | die Daten sind lückenhaft; Lücke heißt nicht „nein“ |
| Treffer | dichte Liste: Name, Hersteller, Kurzmerkmale, Zahl der Quellen | schneller zu überfliegen als Karten; keine Bilder |
| mehr Treffer | Knopf „Show 50 more“, kein Endlos-Scrollen | Fußzeile bleibt erreichbar, Position bleibt stabil |
| Details | Dialog (Handy: Vollbild, Rechner: Schublade rechts), Zurück-Taste schließt; dieselbe Seite als eigene URL | Liste und Filter bleiben erhalten |

## Offene Punkte für die nächste Runde

- Name und Domain der Seite.
- Impressum: Name, Anschrift und Kontakt nach § 5 DDG, wenn die Seite nicht rein privat ist.
- Vergleichsansicht (2–4 Tastaturen nebeneinander, Layouts übereinander).
- Tastenbild auch in der Trefferliste (nur bei schneller Verbindung nachladen).
- Hersteller vereinheitlichen (z. B. „KBDfans“ und „KBDFans“), Fantasienamen aus Ergogen-Dateien aussortieren.
- Server-Konfiguration: `.gz` ausliefern, `Cache-Control` wie in `vorschau.py`.
