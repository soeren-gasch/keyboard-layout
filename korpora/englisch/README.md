# Korpora Englisch

Recherche und Auswahl der englischen Textkorpora, aus denen die N-Gramme für die Bewertung des Layouts entstehen.

Stand: 16.11.2026. Aufbau wie bei [`../deutsch/`](../deutsch/README.md): Manifest, Dummy-Dateien, Skripte, je Quelle eigene N-Gramme, Mischung per Rezept.

## Vorgaben und Kriterien

Zusätzlich zu den Kriterien des Deutschen (Fließtext, neue Rechtschreibung, Textart nah an Sörens Schreiben, private Nutzung erlaubt, als Download verfügbar) gelten für Englisch zwei Entscheidungen vom 15.11.2026:

1. **Britisches Englisch bevorzugt, US-Englisch enthalten.** Ob eine Mischung britisch genug ist, wird gemessen und nicht geschätzt (siehe „Schreibweise“).
2. **StackExchange aufgenommen, aber ohne Code-Inhalte.**

## Ausgewählt

Die Originale (zusammen 21 GB) liegen **nicht im Repository**. Quelle, SHA-256 und Größe jeder Datei stehen in [`quellen.json`](quellen.json), unter `original/` liegen Dummy-Dateien mit erfundenen Beispielen, `python3 korpora/skripte/herunterladen.py englisch/` lädt die vollen Dateien an dieselben Pfade (siehe [`../skripte/README.md`](../skripte/README.md)). Hugging-Face-Dateien sind auf eine feste Revision festgeschrieben, die GitHub-Datei auf einen Commit.

| Teil | Quelle (Name der N-Gramme) | Dateien | Original | Inhalt | Stichprobe | gezählt | Lizenz |
| --- | --- | --- | ---: | --- | --- | ---: | --- |
| förmlich | Leipzig News 2024 (`en-leipzig-news-2024`) | `leipzig/eng_news_2024_1M.tar.gz` | 288 MB | Nachrichten, 1 Mio. Sätze | alle | 118 Mio. | Leipzig-Bedingungen, laut Drittquelle CC BY; offiziell nicht abrufbar (Bot-Schutz) |
| förmlich | Leipzig Web 2018 (`en-leipzig-web-2018`) | `leipzig/eng-com_web-public_2018_1M.tar.gz` | 229 MB | Webseiten (.com), 1 Mio. Sätze | alle | 103 Mio. | wie oben |
| förmlich | Leipzig Wikipedia 2016 (`en-leipzig-wikipedia-2016`) | `leipzig/eng_wikipedia_2016_1M.tar.gz` | 267 MB | Wikipedia, 1 Mio. Sätze | alle | 128 Mio. | wie oben |
| förmlich | Leipzig UK-Web 2002 (`en-leipzig-uk-web-2002`) | `leipzig/eng-uk_web_2002_1M.tar.gz` | 226 MB | Webseiten der `.uk`-Domain, 1 Mio. Sätze, **von 2002** | alle | 112 Mio. | wie oben |
| förmlich | UK Hansard ab 2010 (`en-uk-hansard`) | `uk-hansard/*_ukhansard.jsonl.gz` (11) | 3,2 GB | Parlamentsdebatten Commons, Lords, Schottland, Wales, Nordirland | jedes 30. Dokument ab 2010 | 99 Mio. | Open Parliament Licence |
| förmlich | OANC geschrieben (`en-oanc-geschrieben`) | `oanc/OANC-1.0.1-UTF8.zip` | 334 MB | amerikanisch: Zeitschrift, Briefe, technische Berichte, Reiseführer | alle | 63 Mio. | OANC-Endnutzerlizenz (liegt im Archiv) |
| gesprochen | OpenSubtitles v2024 (`en-opensubtitles-2024`) | `opensubtitles/en.txt.gz` | 9,5 GB | Filmdialoge, 8,5 Mrd. Tokens | jeder 500. Block aus 1.000 Zeilen | 63 Mio. | im Projekt nicht klar ausgewiesen |
| gesprochen | CABNC (`en-cabnc`) | `cabnc/CABNC-0a28a11.zip` | 77 MB | britische Alltagsgespräche (BNC, 1990er), 1.436 Gespräche | alle | 9 Mio. | CC BY laut TalkBank-Seite |
| gesprochen | OANC gesprochen (`en-oanc-gesprochen`) | wie oben | – | amerikanisch: Telefongespräche (Switchboard), Gespräche vor Ort | alle | 15 Mio. | wie oben |
| informell | Ubuntu IRC (`en-ubuntu-irc`) | `ubuntu-irc/*_ubuntu.jsonl.gz` (8) | 2,4 GB | Chat-Protokolle der Ubuntu-Kanäle seit 2004 | jedes 40. Tagesprotokoll | 98 Mio. | gemeinfrei laut Common Pile |
| informell | Reddit TL;DR-17 (`en-reddit-tldr17`) | `reddit-tldr17/corpus-webis-tldr-17.zip` | 3,1 GB (19,6 GB entpackt) | Reddit-Beiträge 2006–2016 | jeder 60. Beitrag | 101 Mio. | CC BY 4.0 laut Hugging-Face-Eintrag; die Rechte an den Beiträgen haben die Nutzer |
| informell | StackExchange Prosa (`en-stackexchange-prosa`) | `stackexchange/<seite>/*_se.jsonl.gz` (20 Seiten, 40 Dateien) | 1,5 GB | Fragen, Antworten, Kommentare, Stand 12/2024 | jedes 30. Dokument, **ohne Code-Zeilen** | 115 Mio. | CC BY-SA je Dokument (in der Probe 3.0) |
| informell | StackExchange Softwareengineering (`en-stackexchange-softwareengineering`) | `stackexchange/softwareengineering.stackexchange.com/*` (2) | 152 MB | dasselbe, ohne Code-Zeilen | jedes 6. Dokument | 61 Mio. | wie oben |
| informell | EnronSent (`en-enronsent`) | `enronsent/enronsentv1.tar.gz` | 26 MB | bereinigte gesendete E-Mails von 2001 | alle | 79 Mio. | gemeinfrei laut README |

StackExchange-Prosa umfasst: english, ell, scifi, rpg, diy, workplace, academia, gaming, travel, philosophy, money, politics, law, history, cooking, movies, skeptics, parenting, pets, music.

Adressen und Revisionen stehen je Datei im Manifest. Herkunft: [Leipzig Wortschatz](https://wortschatz.uni-leipzig.de/en/download), [OPUS OpenSubtitles](https://opus.nlpl.eu/opusapi/?corpus=OpenSubtitles&source=en&preprocessing=mono&version=latest), Common Pile ([Ubuntu IRC](https://huggingface.co/datasets/common-pile/ubuntu_irc), [UK Hansard](https://huggingface.co/datasets/common-pile/uk_hansard), [StackExchange](https://huggingface.co/datasets/common-pile/stackexchange)), [Webis TL;DR-17](https://huggingface.co/datasets/webis/tldr-17), [EnronSent](https://wstyler.ucsd.edu/enronsent/), [OANC](https://anc.org/data/oanc/download/), [CABNC](https://github.com/saulalbert/CABNC) und [TalkBank](https://ca.talkbank.org/access/CABNC.html).

## Schreibweise: britisch gegen amerikanisch

`zaehlen.py` zählt für jede englische Quelle die Wörter aus rund 1.600 Wortpaaren, die nur in einer Variante vorkommen (colour/color, organise/organize, centre/center, travelled/traveled, grey/gray, mum/mom …). Die Ergebnisse stehen in der `meta.json` der Quelle. Methode und Grenzen: [`../skripte/README.md`](../skripte/README.md).

| Quelle | britisch | Treffer |
| --- | ---: | ---: |
| `en-uk-hansard` | 99 % | 60.416 |
| `en-cabnc` | 93 % | 4.881 |
| `en-leipzig-uk-web-2002` | 88 % | 78.759 |
| `en-leipzig-news-2024` | 45 % | 78.303 |
| `en-leipzig-wikipedia-2016` | 30 % | 88.788 |
| `en-ubuntu-irc` | 28 % | 17.394 |
| `en-stackexchange-prosa` | 25 % | 51.259 |
| `en-stackexchange-softwareengineering` | 20 % | 24.728 |
| `en-opensubtitles-2024` | 17 % | 28.087 |
| `en-reddit-tldr17` | 14 % | 49.500 |
| `en-leipzig-web-2018` | 12 % | 68.925 |
| `en-enronsent` | 9 % | 28.012 |
| `en-oanc-geschrieben` | 5 % | 45.592 |
| `en-oanc-gesprochen` | 1 % | 5.349 |

Die Reihenfolge entspricht dem Erwartbaren und ist damit zugleich eine Probe auf die Messung: britische Herkunft oben, amerikanische unten.

## Mischung `en-standard`

Rezept: [`../mischungen/en-standard.json`](../mischungen/en-standard.json). Die Gewichte sind Anteile an allen Zeichen (Tastenanschlägen) und gelten als Startwert, der sich ohne Neuzählen ändern lässt.

| Teil | Anteil | Quellen mit Gewicht |
| --- | ---: | --- |
| förmlich | 42 % | News 12, UK Hansard 12, UK-Web 2002 10, Wikipedia 3, OANC geschrieben 3, Web 2018 2 |
| gesprochen | 25 % | CABNC 16, OpenSubtitles 8, OANC gesprochen 1 |
| informell und technisch | 33 % | Ubuntu IRC 12, StackExchange Prosa 8, Reddit 6, StackExchange Softwareengineering 4, EnronSent 3 |

**Britische Schreibung der Mischung: geschätzt 56 %** (Wert aus `mischen.py`, Treffer je Zeichen und Quelle mit den Gewichten verrechnet).

Was dieser Wert kostet, sollte man wissen:

- **Britisches getipptes Informelles gibt es offen praktisch nicht.** Um britisch zu bleiben, tragen deshalb förmliche Parlamentssprache (Hansard), Gespräche von 1992 (CABNC) und Webtexte von 2002 zusammen 38 % der Mischung. Der informelle Teil ist mit 33 % kleiner als beim Deutschen (40 %).
- **CABNC wiegt 16 %, obwohl es nur 9 Mio. Zeichen sind.** Seine Häufigkeiten sind entsprechend unsicherer, vor allem bei seltenen Trigrammen.
- Wer mehr Gewicht auf Alltagstext legen will, kann die Anteile von Hansard, UK-Web und CABNC senken und den britischen Anteil danach direkt in der Ausgabe von `mischen.py` ablesen.

## Eigenheiten und Schwächen

- **`£` ist nicht tippbar** (deutsche Tastatur) und wird zur harten Grenze. Der Prüfbericht jeder Quelle zählt, wie oft das passiert (in der StackExchange-Prosa-Stichprobe 767-mal).
- **Gesprochene Quellen** haben andere Statistiken als Getipptes: Füllwörter („erm“, „yeah“), kaum Satzzeichen, Transkriptionsregeln. Die Switchboard-Transkripte in OANC gesprochen sind kleingeschrieben und ohne Satzzeichen.
- **CABNC** ist eine Re-Transkription der BNC-Aufnahmen von 1992; Dialekt und Aussprache stehen im Text („oh aye“, „int“).
- **Ubuntu IRC** enthält Shell-Befehle. Sie bleiben drin, weil sie dort getippter Text sind; der Code-Filter gilt nur für StackExchange.
- **StackExchange:** Der Code-Filter arbeitet zeilenweise und kann Code mitten im Satz nicht erkennen; bei Softwareengineering fielen rund 70.000 Zeilen heraus, bei den Prosa-Seiten rund 8.000. Die Nutzer sind überwiegend amerikanisch (25 % britisch).
- **Hansard** besteht aus einem Mix aus Sprecherangaben, Überschriften und Rede; die Bereinigung entfernt Sprecherangaben und kurze Überschriften, Reste bleiben.
- **OpenSubtitles:** viele Filme sind aus dem Englischen oder für ein US-Publikum untertitelt; die Schreibweise ist gemischt (17 % britisch).
- Die Originale der Leipzig-Archive sind uneinheitlich aufgebaut: das `.uk`-Archiv hat kein Oberverzeichnis, die Sätze sind dort nicht sortiert.

## Geprüft und verworfen

| Korpus | Grund |
| --- | --- |
| FineWeb, FineWeb-Edu, C4, OpenWebText, CulturaX, CC-100, mC4, OSCAR | Common-Crawl-Sammlungen im Bereich 100 GB bis TB; inhaltlich durch Leipzig Web, Ubuntu IRC und Reddit abgedeckt |
| Common Pile YouTube, News, Wikimedia | Whisper-Transkripte ohne Herkunftsangabe, Nachrichten internationaler Kleinverlage, Wikipedia samt Diskussionsseiten ohne Abgrenzung |
| Teenage Health Freak Corpus | nur für registrierte Nutzer des UK Data Service, Rechte bei der Betreiberfirma |
| BNC 1994, BNC Baby, BNC Sampler | von BNC XML und BNC2014 überholt; Lizenztext nicht prüfbar; die Gespräche stecken in CABNC |
| ukWaC | nur auf Anfrage, Lizenz unklar |
| ParlaMint-GB | keine Download-Seite gefunden; Hansard deckt dasselbe ab |
| Webis Gmane, W3C-Mailinglisten, LKML5Ws | Zugang eingeschränkt, rechtlich unklar bzw. Code und Patches |
| Hacker-News- und Bluesky-Datensätze | Lizenzlabels der Hochlader, die Rechte liegen bei den Autoren; viel Code bzw. persönliche Beiträge |
| DailyDialog, Empathetic Dialogues, PersonaChat, Dolly-15k | nichtkommerzielle bzw. fehlende Lizenz oder zu klein |
| LMSYS-Chat-1M, LDC BOLT | gesperrt bzw. kostenpflichtig |
| NUS SMS Corpus | Lizenz nicht gefunden, SMS-Abkürzungen („u“, „2moro“) |
| Gutenberg, Pre-1929-Bücher | historisches Englisch |

## Offen

- **Spoken BNC2014** (Lancaster): 10,4 Mio. Wörter britischer Alltagsgespräche der 2010er, die beste britische Quelle. Der Download braucht eine Anmeldung mit Zustimmung zur Lizenz (nichtkommerziell, keine Weitergabe der Rohdaten) und muss manuell erfolgen. Sobald die Datei auf dem Server liegt, kommt sie ins Manifest.
- **OASST2** (Anfragen von Freiwilligen, Apache-2.0) und **Wikipedia mit der Vorlage „Use British English“** (425.946 Artikel) wurden nicht aufgenommen; beides ließe sich über den Weg in „Neue Quelle aufnehmen“ ergänzen.
- **Lizenzen:** Die offiziellen Leipzig-Bedingungen sowie die von OpenSubtitles und der Reddit-Beiträge sollten vor einer Veröffentlichung abgeleiteter N-Gramme geprüft werden; für die private Nutzung sind sie unkritisch.
- **Gewichtung zwischen den Sprachen und mit Code** steht noch aus.
