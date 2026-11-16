# Plan: 48 Stunden Optimierung

Stand: 16.11.2026, Entwurf zur Entscheidung durch Sören.

## Messungen, auf denen der Plan beruht

| Befund | Wert | Folge |
| --- | --- | --- |
| Abkühlung im Optimizer | fest einprogrammiert: Temperatur × 0,998 je Iteration (`layout_optimization_sa/src/optimization.rs`), unabhängig von `max_iters` | Ein Lauf ist nach rund 5.000 Iterationen kalt; die eigentliche Suche dauert nur etwa 2.000 Iterationen. Längere Läufe bringen nichts, mehr Läufe schon. |
| Leerlauf am Ende | `stall_accepted: 5000`: nach dem Abkühlen noch 5.000 Iterationen ohne Fortschritt | etwa die Hälfte der Rechenzeit eines Laufs |
| Starttemperatur 150 | die ersten rund 1.500 Iterationen sind Zufallssuche | `--init-temp` um 10 spart weitere 15 bis 20 % |
| Bewertung je Layout | 145 ms mit allen 480.000 Trigrammen, 25 ms mit `--tops 0.995` (55.000 Trigramme) | Faktor 6; Fehler bei Kostendifferenzen nahe dem Optimum ≤ 0,12, Reihenfolge der besten 10 Nachbarn unverändert |
| Landschaft am Optimum | bester Nachbar (ein Tausch) nur 0,02 schlechter | Viele fast gleichwertige Layouts. Die Unterschiede sind viel kleiner als die Unsicherheit des Modells (Sprachmix, Tastenkosten, Gewichte). |
| Hub | 8 dedizierte Kerne AMD EPYC 9645 (Zen 5c, AVX-512), 16 GB RAM, kein Steal | 7 parallele Läufe bringen etwa den Faktor 5 (Cache-Konkurrenz); 70 MB RAM je Lauf |

**Schluss:** 48 Stunden am Stück auf ein einziges Ziel würden immer wieder dasselbe flache Plateau finden. Der Nutzen liegt in der **Breite**: mehrere Modellannahmen, Prüfung auf Robustheit und gezieltes Nachschärfen der Finalisten. Gerechnet wird deshalb in **Generationen**. Jede baut auf der vorigen auf und endet mit einem Zwischenstand im Repo. Die Generationen laufen ohne Wartezeit nacheinander.

## Generationen

| Gen. | Dauer | Zweck | Vorgehen |
| --- | --- | --- | --- |
| G0 Kalibrierung | 2 h, vor dem Block | Einstellungen festlegen | getunte Läufe (`--tops 0.995`, `--init-temp 10`, `stall_accepted` 1.500) gegen die Standardläufe aus Lauf 01: gleiche Qualität bei etwa einem Viertel der Zeit? Ein Probelauf `optimize_genetic` zum Vergleich. Build mit `target-cpu=native` messen. |
| G1 Erkundung | 14 h | Landkarte je Szenario | Zufallsstarts in allen Szenarien (siehe unten). Läufe werden **adaptiv** verteilt: Ein Szenario gilt als abgedeckt, wenn sein bestes Layout in mindestens 4 unabhängigen Läufen gefunden wurde; danach bekommen die noch offenen Szenarien die Kerne. |
| G2 Nachschärfen | 16 h | Finalisten verbessern | je Hauptszenario die 30 besten verschiedenen Layouts als Startpunkt, niedrige Temperatur (`-s`, `--init-temp` 1 bis 3), volle N-Gramme. Am Ende prüft ein vollständiger Ein-Tausch-Test (alle 496 Nachbarn), ob jeder Finalist ein lokales Optimum ist. |
| G3 Robustheit | 4 h | Auswahl | alle Finalisten in allen Szenarien, je Sprache und mit Metrik-Gewichten ±30 % bewerten; Pareto-Front (Deutsch, Englisch, Code, Gesamt); Layouts zu Familien gruppieren |
| Reserve | 12 h | nach der Durchsicht mit Dir | Folgefragen, etwa Leertaste fest auf dem Daumen, q/ß als Kombo, Symbol-Ebene |

Durchsatz nach G0 (geschätzt): 2 bis 3 Minuten je Lauf statt 10, also 150 bis 200 Läufe je Stunde auf dem Hub, in G1 rund 2.500 Läufe.

### Szenarien für G1

| Dimension | Werte |
| --- | --- |
| Home-Row-Variante | A, B, C |
| Tastenkosten | `standard`, `soeren` |
| Sprachmix | 65/25/10 (Hauptszenario), 75/20/5, 50/35/15 |

Das ergibt 18 Szenarien. Schon vor G1 entschieden werden muss:

- ob die Leertaste auf einer Modifikator-Position landen darf (Lauf 01 zeigt, wohin sie von selbst wandert),
- ob die Shortcut-Metrik (Z, X, C, V links) mehr Gewicht bekommt.

## Betrieb

- Jeder Lauf hängt sein Ergebnis sofort an eine Datei an. Ein Abbruch kostet höchstens die gerade laufenden Läufe.
- Jede Stunde gibt es einen Zwischenstand: Auswertung, Commit und Push nach GitHub.
- Läufe mit `nice -n 19`, damit Hub, Remote Control und DecaSwift-Jobs Vorrang behalten.

## Hub (netcup) ändern?

| Option | Nutzen | Bewertung |
| --- | --- | --- |
| Build mit `-C target-cpu=native` (AVX-512) | vielleicht 5 bis 10 % | billig, nur lokal; in G0 messen |
| Tarif vorübergehend vergrößern | mehr Kerne | erst prüfen, ob netcup ein Upgrade wieder zurücknimmt; lohnt kaum, wenn das Homelab Kerne frei hat |
| Last auf dem Hub | 48 h Volllast blockiert den Hub für DecaSwift | in Woche 1 der Suchphase laufen dort noch keine Jobs; mit `nice` vertretbar |
| Ansible | Rust, Zig und Optimizer liegen nutzerlokal in `~`, nicht im Playbook | Wird der Hub aus `decaswift-hub.yml` neu aufgesetzt, fehlen sie; die Anleitung steht in `optimizer/README.md`. Für den 48-h-Block reicht das. |

## VM auf Proxmox-Node A?

Lohnt sich, wenn Node A mindestens 8 freie Kerne hat oder pro Kern deutlich schneller ist als der EPYC 9645. Der EPYC hat viele sparsame Kerne mit niedrigem Takt. Desktop-CPUs mit 5 GHz oder großem L3-Cache (X3D) sind für diesen Optimizer vermutlich schneller, weil er pro Lauf auf einem Kern läuft und stark am Cache hängt. Die Szenarien sind unabhängig. Hub und VM können also parallel rechnen und das Budget verdoppeln.

Einstellungen der VM:

| Einstellung | Wert | Grund |
| --- | --- | --- |
| CPU-Typ | `host` | alle Befehlssätze, `target-cpu=native` |
| Kerne | alle freien physischen Kerne plus SMT-Threads, NUMA an bei mehreren Sockeln | Durchsatz |
| RAM | 4 bis 8 GB, Ballooning aus | 70 MB je Lauf |
| Platte | 20 GB | Optimizer, N-Gramme, Ergebnisse |
| Host | CPU-Governor `performance` für die 48 h, danach zurück | Takt |
| Einrichtung | Debian 13 per Ansible von der Automation-VM, wie der Hub | Reproduzierbarkeit |

Netz: Das Homelab baut nur Verbindungen nach außen auf (Regel: kein VPN, der Hub greift nie ins Homelab). Die VM pusht ihre Ergebnisse mit einem eigenen Deploy-Key direkt nach GitHub; der Hub holt sie dort ab. Gesteuert wird die VM entweder durch einen eigenen Claude-Code-Zugang dort oder durch ein Startskript mit festem Szenarioplan.

Kosten: Strom für 48 h bei etwa 150 W, rund 7 kWh, also 2 bis 3 €.

Vergleich vor der Entscheidung: denselben Ein-Tausch-Test (496 Layouts, Einkern-Zeit je Layout) auf Hub und Node A laufen lassen.

## Variante: 2 Wochen auf Hub und Node A

Rund 18-mal so viel Rechenzeit wie 48 h auf dem Hub, unter der Annahme, dass Node A etwa 12 Kerne beisteuert. Mit beschleunigten Läufen wären das grob 150.000 Läufe. Ein Szenario braucht bis zur sicheren Konvergenz etwa 50 bis 100. Die Rechenzeit ist dann nicht mehr der Engpass. Engpässe sind die Annahmen im Modell und Sörens Rückmeldung.

| Änderung gegenüber 48 h | Inhalt |
| --- | --- |
| volle N-Gramme überall | kein `--tops`, keine Näherung |
| Home-Row-Belegung mitoptimieren | statt 3 Varianten alle 120 symmetrischen Zuordnungen von Shift, Symbol und Navigation auf die 5 Grundreihen-Spalten und den Daumen |
| mehr Szenarien | Tastenkosten je Tastatur (Voyager, Sweep, Corne), weitere Sprachmixe, Varianten für q/ß/x |
| fremde Richter | Finalisten mit Metrik-Sätzen bewerten, auf die sie nicht optimiert wurden (Oxey-, KLA-Metriken, andere Gewichte) |
| Zwei-Tausch-Prüfung | alle rund 120.000 Zwei-Tausch-Nachbarn je Finalist (etwa 5 Kernstunden je Layout) |
| Symbol- und Navigations-Ebene | eigene Optimierung bei fester Basis, danach im Wechsel |
| Mensch in der Schleife | Woche 1 Erkundung, dann tippt Sören die besten 3 bis 5 Kandidaten zur Probe und meldet zurück; die Rückmeldung passt Tastenkosten und Bigramm-Strafen an, Woche 2 rechnet neu |
| eigener Code | Ein kleiner Patch (Abkühlfaktor einstellbar, Wiederaufheizen) bringt mehr als zusätzliche Kerne; mit Sören neu entscheiden |
| Betrieb | Job-Warteschlange mit Neustart nach Reboot (systemd), stündlicher Push, Hub mit `nice` und weniger Kernen, sobald DecaSwift Stufe C (CPU-Embeddings) läuft |
| Kosten | Node A etwa 50 kWh, 15 bis 20 €; bei netcup prüfen, ob der Tarif dauerhafte Volllast erlaubt |

## Offen, von Sören

1. Daten von Node A: CPU-Modell, Kerne/Threads, RAM, was dort sonst läuft, ob 48 h Volllast in Ordnung sind (Kühlung, Lärm)
2. Darf der Hub 48 h unter Last laufen, oder sind DecaSwift-Jobs geplant?
3. Szenarien bestätigen: Sprachmixe, Kostenprofile, Leertaste auf Modifikator-Positionen ja oder nein
