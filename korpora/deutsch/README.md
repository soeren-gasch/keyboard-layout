# Korpora Deutsch

Recherche und Auswahl der deutschen Textkorpora, aus denen die N-Gramme für die Bewertung des Layouts entstehen.

Stand: 14.11.2026

## Kriterien

1. **Fließtext**, keine Wortlisten. Für Buchstaben-Bigramme und -Trigramme braucht es zusammenhängenden Text, auch über Wortgrenzen hinweg.
2. **Neue Rechtschreibung.** Texte vor etwa 2005 und historische Texte treiben das ß künstlich hoch (*daß*).
3. **Textart nah an Sörens eigenem Schreiben**: Mails, Chats, Notizen und Dokumentation, nicht nur Nachrichten und Lexikon.
4. **Lizenz erlaubt die private Nutzung** und das Ablegen in einem privaten Repository.
5. **Verfügbar** als Download, nicht nur als Online-Suche.

## Ausgewählt

Die Original-Dateien werden lokal unter `original/` abgelegt und nicht ins Repository aufgenommen. Prüfsummen stehen in [`original.sha256`](original.sha256).

| Teil | Korpus | Datei | Größe | Inhalt | Lizenz |
| --- | --- | --- | --- | --- | --- |
| förmlich | Leipzig Corpora Collection, News 2024 | `leipzig/deu_news_2024_1M.tar.gz` | 229 MB | 1 Mio. Sätze aus Nachrichten-Feeds 2024 | laut Drittquelle CC BY; offizielle Nutzungsbedingungen nicht abrufbar (Bot-Schutz), **offen** |
| förmlich | Leipzig, Web 2021 (`deu-de`) | `leipzig/deu-de_web_2021_1M.tar.gz` | 198 MB | 1 Mio. Sätze von Webseiten unter `.de`, 17,3 Mio. Tokens | wie oben |
| förmlich | Leipzig, Wikipedia 2021 | `leipzig/deu_wikipedia_2021_1M.tar.gz` | 207 MB | 1 Mio. Sätze aus der deutschen Wikipedia | wie oben; Wikipedia-Text selbst CC BY-SA |
| gesprochen | OpenSubtitles v2024 (OPUS), Teil Deutsch | `opensubtitles/de.txt.gz` | 1,5 GB | 141,6 Mio. Zeilen, 951 Mio. Tokens, ein Satz je Zeile | im Projekt nicht ausgewiesen; eine Hugging-Face-Kopie nennt CC BY-SA 3.0, **offen** |
| informell | GC4 (German colossal, cleaned Common Crawl), Teil „Middle“, Datei 0000 von Snapshot 2020-10 | `gc4/de_middle_0000_2020-10.tar.gz` | 2,3 GB | Stichprobe; laut Projekt „more colloquial language like forum entries, commentary sections“ | verweist auf die Nutzungsbedingungen von Common Crawl |
| informell | One Million Posts Corpus (derStandard.at, 2015–2016) | `one-million-posts/million_post_corpus.tar.bz2` | 106 MB | rund 1 Mio. Leserkommentare als SQLite-Datenbank | CC BY-NC-SA 4.0 (`LICENSE.txt` im Archiv) |
| informell | Dortmunder Chat-Korpus | `dortmunder-chatkorpus/chatkorpus-release.zip`, `chatkorpus-web.zip` | 4 MB, 17 MB | 381 Chat-Mitschnitte als XML (ISO-8859-1), rund 1 Mio. Tokens, 2002–2008 | keine Lizenzdatei im Archiv; in CLARIN offen oder akademisch-nichtkommerziell, **offen** |

Download-Quellen:

- Leipzig: `https://downloads.wortschatz-leipzig.de/corpora/<name>.tar.gz`, Übersicht unter https://wortschatz.uni-leipzig.de/en/download
- OpenSubtitles: https://object.pouta.csc.fi/OPUS-OpenSubtitles/v2024/mono/de.txt.gz, gefunden über `https://opus.nlpl.eu/opusapi/?corpus=OpenSubtitles&source=de&preprocessing=mono&version=latest`
- GC4: https://opendata.iisys.de/opendata/Datasets/CommonCrawl/middle/de_middle_0000_2020-10.tar.gz, Übersicht unter https://german-nlp-group.github.io/projects/gc4-corpus.html
- One Million Posts: https://github.com/OFAI/million-post-corpus/releases/download/v1.0.0/million_post_corpus.tar.bz2
- Dortmunder Chat-Korpus: https://www.uni-due.de/germanistik/chatkorpus/

### Eigenheiten der Formate

- **Leipzig:** Je Archiv eine Datei `*-sentences.txt` mit `ID<TAB>Satz`. Die Sätze sind dedupliziert und **alphabetisch sortiert**, Zusammenhänge zwischen Sätzen fehlen also. Die übrigen Dateien (Wortlisten, Kookkurrenzen) werden nicht gebraucht. Typografische Anführungszeichen („…“) und Gedankenstriche kommen vor.
- **OpenSubtitles:** Ein Satz je Zeile, Dialogzeilen beginnen oft mit `- `, Titel und Einblendungen stehen in Großbuchstaben. Viele Filme sind aus dem Englischen übersetzt.
- **GC4:** Das Archiv enthält eine einzige Textdatei mit 6,1 GB. Die Datensätze sind keine JSON-Zeilen, sondern aneinandergehängte Python-Dictionaries (`{'url': …, 'raw_content': …}{…}`) mit `language_score`, `perplexity` und Quell-Domain. Das Projekt empfiehlt, nach `language_score > 0.98` zu filtern. Seiten sind teils abgeschnitten (`…`).
- **One Million Posts:** `corpus.sqlite3` mit Titel und Text je Beitrag, teils mit HTML-Resten.
- **Dortmunder Chat-Korpus:** XML je Chat-Mitschnitt, Nachrichten mit `type="system"` sind Servermeldungen und keine getippten Texte.

## Geprüft und verworfen

| Korpus | Grund |
| --- | --- |
| FineWeb-2, CulturaX, mC4, CC-100, OSCAR 23.01 | Common Crawl in Größenordnungen von 100 GB und mehr, teils erst nach Freischaltung; inhaltlich durch Leipzig Web und GC4 abgedeckt |
| German Commons v1.1 | überwiegend historische Zeitungen und gemeinfreie Bücher mit OCR-Fehlern; einzelne Teile (MOSEL, Wikibooks, Wikinews) als spätere Ergänzung möglich |
| DWDS (BBAW) | seit 08.06.2026 nur Recherche nach Login, kein Volltext-Download |
| DeReKo / DeReWo (IDS) | kein Massen-Download, DeReWo nur Wortliste |
| Deutsches Textarchiv, LIMAS, Projekt Gutenberg, diachrone Korpora der HU-Linkliste | historische Sprache bzw. alte Rechtschreibung |
| German4All | 25.000 von GPT-4 umformulierte Absätze: klein und synthetisch |
| Europarl, GermaParl, AustroParl | förmliche Parlamentsreden, ältere Jahrgänge in alter Rechtschreibung; allenfalls spätere Beimischung |
| SwissParl / GerParCor (Schweiz) | Schweizer Rechtschreibung ohne ß |
| DeWaC / SdeWaC | Crawl um 2008, nur auf Anfrage; durch Leipzig Web abgedeckt |
| 10kGNAD | 10.000 Nachrichtenartikel, durch Leipzig News abgedeckt |
| SUBTLEX-DE, Google Books Ngrams | nur Wort-Häufigkeiten bzw. Wort-N-Gramme, kein Fließtext |
| TIGER, TüBa-D/Z, Hamburg Dependency Treebank | kleine Baumbanken, nur akademische Lizenz, Texte vor 2005 |
| DGD / FOLK | Transkripte gesprochener Sprache nach Transkriptionskonventionen, kein getippter Text |
| MoCoDa 2 | WhatsApp-Chats, ideale Textart, aber nur Online-Suche; Anfrage beim Projekt möglich |
| Korpus Südtirol | regional gefärbt, nicht im Detail geprüft |

## Offen

- Lizenzen von Leipzig, OpenSubtitles und Dortmunder Chat-Korpus verbindlich prüfen, bevor abgeleitete N-Gramme veröffentlicht werden.
- Aufbereitung siehe [`../skripte/README.md`](../skripte/README.md); Ergebnisse unter [`../ngramme/`](../ngramme/README.md).
- Eigene Texte von Sören als zusätzliche Quelle: Daraus kommen nur aggregierte N-Gramme ins Repo, nie Rohtexte.
