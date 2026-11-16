# Korpora Code

Quelltext für die Bewertung des Layouts, passend zu Sörens Stack: **PHP mit Laravel, Vue, JavaScript, Java und SQL**.

Stand: 16.11.2026. Aufbau wie bei [`../deutsch/`](../deutsch/README.md) und [`../englisch/`](../englisch/README.md): Manifest, Dummy-Dateien, Skripte, je Quelle eigene N-Gramme, Mischung per Rezept.

## Vorgaben (Entscheidungen vom 16.11.2026)

1. **Führende Leerzeichen und Tabs werden ignoriert.** Editoren rücken ein, die Einrückung ist nicht getippt.
2. **Jedes Zeilenende zählt als Enter**, egal ob LF, CRLF, CR oder ein anderer Zeilentrenner. In den N-Grammen steht es als `\n`. Wer Zeilenwechsel nicht bewerten will, kann das beim Bewerten abschalten (Optimizer: `exclude_line_breaks`).
3. **Gewichte der Sprachen:** PHP/Laravel 35 %, Vue 20 %, JavaScript 15 %, Java 15 %, SQL 15 % (Rezept [`code-standard`](../mischungen/code-standard.json)).
4. **Eigener Code** von Sören kommt als zusätzliche Quelle, sobald er vorliegt (siehe „Offen“).

## Warum Repositories statt fertiger Code-Sammlungen

| Sammlung | Befund |
| --- | --- |
| The Stack v1/v2, StarCoderData | gesperrt: Zugang nur mit Hugging-Face-Anmeldung und Zustimmung; Lizenz je Datei |
| `codeparrot/github-code` (-clean) | 287 bzw. 314 GB, nur Parquet (ohne Zusatzpakete nicht lesbar), ohne Vue |
| Common Pile Stack v2 | offen und lesbar, aber 764 Dateien zu je 2 GB (rund 1,5 TB) und **nicht nach Sprache sortiert** (CSV, JSON, C und C# tauchen verstreut mehrfach auf); PHP, Java, Vue ließen sich nur durch Durchsuchen von bis zu 1,5 TB finden |
| Stack-Edu | nach „Lehrwert“ gefiltert: Code in Lehrbuch-Stil statt Alltagscode |

Stattdessen werden ausgewählte, frei lizenzierte Repositories auf einem **festen Commit** als Archiv geladen (`https://github.com/<repo>/archive/<commit>.tar.gz`). Die Auswahl besteht aus Frameworks und Bibliotheken **und aus Anwendungen** mit Controllern, Modellen, Migrationen und Komponenten (Bagisto, Krayin-CRM, BookStack, Koel; YesPlayMusic, Dashy, vue-admin-better; mall, eladmin, CAS, Apollo; Fastify, Mongoose, hackathon-starter).

**Lizenzprüfung:** Aufgenommen ist, was am gepinnten Commit als MIT, Apache-2.0, BSD, ISC oder PostgreSQL-Lizenz erkannt wurde (Lizenzdatei im Repository). Das sind **80 × MIT, 15 × Apache-2.0, 1 × PostgreSQL-Lizenz und 2 Repositories mit MIT-Angabe nur im `package.json`** (vuestic-ui, best-resume-ever), dazu der Datensatz `sql-create-context` (CC BY 4.0). Kein Copyleft. Von Hand entschieden: Vuetify (Lizenzdatei liegt in `packages/vuetify/`) und Postgres (Datei `COPYRIGHT`) aufgenommen; **ausgeschlossen** wurden Cachet (eigene Lizenz der Alt Three Services) und `laravel/laravel` (keine Lizenzdatei, nur `composer.json`).

## Quellen im Überblick

| Quelle | Sprache | Repositories | gezählt | Gewicht |
| --- | --- | ---: | ---: | ---: |
| `code-php` | PHP und Laravel (einschließlich Blade) | 34 | 42,3 Mio. | 35 % |
| `code-vue` | Vue (`.vue`-Dateien) | 23 | 22,3 Mio. | 20 % |
| `code-javascript` | JavaScript | 21 | 50,2 Mio. | 15 % |
| `code-java` | Java | 16 | 72,0 Mio. | 15 % |
| `code-sql` | SQL | 6 | 22,8 Mio. | 15 % |

Die Archive jeder Quelle ergeben sich aus dem Manifest [`quellen.json`](quellen.json) (Feld `genutzt_von`). Ein Repository kann mehrere Quellen speisen (Quasar liefert `.vue`- und `.js`-Dateien). Download, Normalisierung und Dateiauswahl: [`../skripte/README.md`](../skripte/README.md), Abschnitt „Code-Quellen“.

## Repositories je Sprache

Die Spalte „geeignet“ ist die Menge an Dateien der richtigen Endung nach Ausschluss von `vendor`, `node_modules`, Übersetzungen und Ähnlichem; „gewählt“ der Anteil, der wegen der Obergrenze von 10 MB je Repository tatsächlich gelesen wird.

### PHP und Laravel (einschließlich Blade) (`code-php`)

Gezählt: **42,3 Mio. Zeichen** aus 17.097 Dateien; Gewicht in `code-standard`: 35 %.

| Repository | Lizenz | Commit | geeignet (MB) | gewählt | Dateien | Zeichen roh (MB) |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| [bagisto/bagisto](https://github.com/bagisto/bagisto) | MIT | `ed8dcf2` | 11,7 | 86 % | 2321 | 9,7 |
| [symfony/symfony](https://github.com/symfony/symfony) | MIT | `a9bd44f` | 51,4 | 20 % | 1088 | 8,1 |
| [laravel/framework](https://github.com/laravel/framework) | MIT | `06d1eab` | 7,7 | 100 % | 1765 | 7,7 |
| [filamentphp/filament](https://github.com/filamentphp/filament) | MIT | `531b069` | 6,2 | 100 % | 1608 | 6,1 |
| [krayin/laravel-crm](https://github.com/krayin/laravel-crm) | MIT | `ed6deeb` | 4,3 | 100 % | 971 | 4,3 |
| [flarum/framework](https://github.com/flarum/framework) | MIT | `b77f310` | 4,2 | 100 % | 1669 | 4,2 |
| [BookStackApp/BookStack](https://github.com/BookStackApp/BookStack) | MIT | `0b6b667` | 3,6 | 100 % | 1151 | 3,5 |
| [koel/koel](https://github.com/koel/koel) | MIT | `9ec40db` | 3,2 | 100 % | 1759 | 3,2 |
| [composer/composer](https://github.com/composer/composer) | MIT | `5147ea1` | 2,9 | 100 % | 321 | 2,9 |
| [pterodactyl/panel](https://github.com/pterodactyl/panel) | MIT | `90b2aa8` | 2,1 | 100 % | 973 | 2,1 |
| [webreinvent/vaahcms](https://github.com/webreinvent/vaahcms) | MIT | `8d7898f` | 1,3 | 100 % | 239 | 1,3 |
| [laravelio/laravel.io](https://github.com/laravelio/laravel.io) | MIT | `b9d33e2` | 0,8 | 100 % | 463 | 0,8 |
| [livewire/livewire](https://github.com/livewire/livewire) | MIT | `e03c29c` | 0,8 | 100 % | 306 | 0,8 |
| [spatie/freek.dev](https://github.com/spatie/freek.dev) | MIT | `f786cbb` | 0,7 | 100 % | 406 | 0,7 |
| [spatie/laravel-data](https://github.com/spatie/laravel-data) | MIT | `7bda01d` | 0,5 | 100 % | 353 | 0,5 |
| [laravel/jetstream](https://github.com/laravel/jetstream) | MIT | `10046c0` | 0,4 | 100 % | 231 | 0,4 |
| [SpartnerNL/Laravel-Excel](https://github.com/SpartnerNL/Laravel-Excel) | MIT | `49d7521` | 0,3 | 100 % | 215 | 0,3 |
| [laravel/horizon](https://github.com/laravel/horizon) | MIT | `0aaa5ec` | 0,3 | 100 % | 145 | 0,3 |
| [laravel/cashier-stripe](https://github.com/laravel/cashier-stripe) | MIT | `7064e18` | 0,3 | 100 % | 64 | 0,3 |
| [laravel/breeze](https://github.com/laravel/breeze) | MIT | `a282521` | 0,3 | 100 % | 159 | 0,3 |
| [laravel/scout](https://github.com/laravel/scout) | MIT | `bb583fe` | 0,3 | 100 % | 50 | 0,3 |
| [laravel/telescope](https://github.com/laravel/telescope) | MIT | `ccd60c1` | 0,3 | 100 % | 89 | 0,3 |
| [fruitcake/laravel-debugbar](https://github.com/fruitcake/laravel-debugbar) | MIT | `033b34a` | 0,2 | 100 % | 77 | 0,2 |
| [spatie/laravel-medialibrary](https://github.com/spatie/laravel-medialibrary) | MIT | `7d8c78f` | 0,2 | 100 % | 99 | 0,2 |
| [barryvdh/laravel-ide-helper](https://github.com/barryvdh/laravel-ide-helper) | MIT | `66f7ec1` | 0,2 | 100 % | 22 | 0,2 |
| [laravel/passport](https://github.com/laravel/passport) | MIT | `aa6d837` | 0,2 | 100 % | 93 | 0,2 |
| [stefanzweifel/screeenly](https://github.com/stefanzweifel/screeenly) | MIT | `0c04289` | 0,2 | 100 % | 112 | 0,2 |
| [spatie/laravel-backup](https://github.com/spatie/laravel-backup) | MIT | `9a5597f` | 0,2 | 100 % | 86 | 0,2 |
| [laravel/fortify](https://github.com/laravel/fortify) | MIT | `3db382a` | 0,1 | 100 % | 120 | 0,1 |
| [spatie/laravel-permission](https://github.com/spatie/laravel-permission) | MIT | `799e1ae` | 0,1 | 100 % | 42 | 0,1 |
| [laravel/socialite](https://github.com/laravel/socialite) | MIT | `8032bb1` | 0,1 | 100 % | 33 | 0,1 |
| [spatie/laravel-query-builder](https://github.com/spatie/laravel-query-builder) | MIT | `3070dfc` | 0,1 | 100 % | 49 | 0,1 |
| [spatie/laravel-activitylog](https://github.com/spatie/laravel-activitylog) | MIT | `fdcc5ee` | 0,1 | 100 % | 24 | 0,1 |
| [laravel/sanctum](https://github.com/laravel/sanctum) | MIT | `a8f7ef1` | 0,0 | 100 % | 22 | 0,0 |

### Vue (`.vue`-Dateien) (`code-vue`)

Gezählt: **22,3 Mio. Zeichen** aus 11.531 Dateien; Gewicht in `code-standard`: 20 %.

| Repository | Lizenz | Commit | geeignet (MB) | gewählt | Dateien | Zeichen roh (MB) |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| [primefaces/primevue](https://github.com/primefaces/primevue) | MIT | `36965f1` | 8,7 | 100 % | 2605 | 8,7 |
| [quasarframework/quasar](https://github.com/quasarframework/quasar) | MIT | `8424c2b` | 3,4 | 100 % | 1463 | 3,4 |
| [nuxt/ui](https://github.com/nuxt/ui) | MIT | `aa54cd8` | 2,4 | 100 % | 805 | 2,4 |
| [vuetifyjs/vuetify](https://github.com/vuetifyjs/vuetify) | MIT | `d6eda7e` | 2,2 | 100 % | 1310 | 2,2 |
| [epicmaxco/vuestic-ui](https://github.com/epicmaxco/vuestic-ui) | MIT (package.json) | `c5337ed` | 2,1 | 100 % | 1002 | 1,9 |
| [vbenjs/vue-vben-admin](https://github.com/vbenjs/vue-vben-admin) | MIT | `53b47f8` | 1,7 | 100 % | 693 | 1,7 |
| [element-plus/element-plus](https://github.com/element-plus/element-plus) | MIT | `3b5d0ad` | 1,6 | 100 % | 832 | 1,6 |
| [buefy/buefy](https://github.com/buefy/buefy) | MIT | `469dadd` | 1,4 | 100 % | 439 | 1,4 |
| [vueComponent/ant-design-vue](https://github.com/vueComponent/ant-design-vue) | MIT | `7483836` | 1,0 | 100 % | 731 | 1,0 |
| [lissy93/dashy](https://github.com/lissy93/dashy) | MIT | `cb56d1d` | 0,9 | 100 % | 174 | 0,9 |
| [vuejs/router](https://github.com/vuejs/router) | MIT | `4b89de6` | 0,9 | 100 % | 324 | 0,9 |
| [ElemeFE/element](https://github.com/ElemeFE/element) | MIT | `c345bb4` | 0,7 | 100 % | 155 | 0,7 |
| [elk-zone/elk](https://github.com/elk-zone/elk) | MIT | `6b956a6` | 0,5 | 100 % | 261 | 0,5 |
| [zxwk1998/vue-admin-better](https://github.com/zxwk1998/vue-admin-better) | MIT | `b02834b` | 0,4 | 100 % | 75 | 0,4 |
| [PanJiaChen/vue-element-admin](https://github.com/PanJiaChen/vue-element-admin) | MIT | `6858a9a` | 0,4 | 100 % | 131 | 0,4 |
| [youzan/vant](https://github.com/youzan/vant) | MIT | `7cc4992` | 0,3 | 100 % | 129 | 0,3 |
| [qier222/YesPlayMusic](https://github.com/qier222/YesPlayMusic) | MIT | `5d5fa23` | 0,3 | 100 % | 42 | 0,3 |
| [vueuse/vueuse](https://github.com/vueuse/vueuse) | MIT | `bed1dce` | 0,2 | 100 % | 195 | 0,2 |
| [vuejs/vitepress](https://github.com/vuejs/vitepress) | MIT | `40b2e09` | 0,2 | 100 % | 71 | 0,2 |
| [salomonelli/best-resume-ever](https://github.com/salomonelli/best-resume-ever) | MIT (package.json) | `29e753c` | 0,1 | 100 % | 21 | 0,1 |
| [lin-xin/vue-manage-system](https://github.com/lin-xin/vue-manage-system) | MIT | `6a7019e` | 0,1 | 100 % | 40 | 0,1 |
| [vuejs/pinia](https://github.com/vuejs/pinia) | MIT | `4817135` | 0,0 | 100 % | 25 | 0,0 |
| [vuejs/core](https://github.com/vuejs/core) | MIT | `cbd9595` | 0,0 | 100 % | 11 | 0,0 |

### JavaScript (`code-javascript`)

Gezählt: **50,2 Mio. Zeichen** aus 18.725 Dateien; Gewicht in `code-standard`: 15 %.

| Repository | Lizenz | Commit | geeignet (MB) | gewählt | Dateien | Zeichen roh (MB) |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| [mrdoob/three.js](https://github.com/mrdoob/three.js) | MIT | `f9bb9a4` | 15,0 | 66 % | 1194 | 10,3 |
| [webpack/webpack](https://github.com/webpack/webpack) | MIT | `8466aab` | 20,2 | 50 % | 7290 | 9,3 |
| [eslint/eslint](https://github.com/eslint/eslint) | MIT | `97efadd` | 9,1 | 100 % | 818 | 9,1 |
| [quasarframework/quasar](https://github.com/quasarframework/quasar) | MIT | `8424c2b` | 7,5 | 100 % | 1388 | 7,1 |
| [Automattic/mongoose](https://github.com/Automattic/mongoose) | MIT | `ab4e363` | 4,2 | 100 % | 478 | 4,2 |
| [prettier/prettier](https://github.com/prettier/prettier) | MIT | `2cc4f0f` | 3,4 | 100 % | 4058 | 3,4 |
| [bootstrap-vue/bootstrap-vue](https://github.com/bootstrap-vue/bootstrap-vue) | MIT | `9a246f4` | 2,6 | 100 % | 524 | 2,5 |
| [fastify/fastify](https://github.com/fastify/fastify) | MIT | `4679723` | 1,9 | 100 % | 262 | 1,9 |
| [jquery/jquery](https://github.com/jquery/jquery) | MIT | `feaa9fc` | 1,7 | 100 % | 211 | 1,7 |
| [axios/axios](https://github.com/axios/axios) | MIT | `85ffbaf` | 1,4 | 100 % | 249 | 1,4 |
| [chartjs/Chart.js](https://github.com/chartjs/Chart.js) | MIT | `71d4421` | 1,2 | 100 % | 131 | 1,2 |
| [mochajs/mocha](https://github.com/mochajs/mocha) | MIT | `5b5afa7` | 1,2 | 100 % | 235 | 1,2 |
| [moment/moment](https://github.com/moment/moment) | MIT | `c2a703a` | 1,1 | 100 % | 202 | 1,1 |
| [jestjs/jest](https://github.com/jestjs/jest) | MIT | `aa88f7c` | 1,1 | 100 % | 1224 | 1,1 |
| [socketio/socket.io](https://github.com/socketio/socket.io) | MIT | `f8e8746` | 0,7 | 100 % | 177 | 0,7 |
| [sahat/hackathon-starter](https://github.com/sahat/hackathon-starter) | MIT | `532a217` | 0,6 | 100 % | 56 | 0,6 |
| [expressjs/express](https://github.com/expressjs/express) | MIT | `43fca52` | 0,6 | 100 % | 141 | 0,6 |
| [webtorrent/webtorrent](https://github.com/webtorrent/webtorrent) | MIT | `2ea1ded` | 0,3 | 100 % | 65 | 0,3 |
| [lodash/lodash](https://github.com/lodash/lodash) | MIT | `2b5e6f7` | 0,2 | 100 % | 24 | 0,2 |
| [standard/standard](https://github.com/standard/standard) | MIT | `753309b` | 0,0 | 100 % | 9 | 0,0 |
| [typicode/json-server](https://github.com/typicode/json-server) | MIT | `89a34a4` | 0,0 | 0 % | 0 | 0,0 |

### Java (`code-java`)

Gezählt: **72,0 Mio. Zeichen** aus 18.062 Dateien; Gewicht in `code-standard`: 15 %.

| Repository | Lizenz | Commit | geeignet (MB) | gewählt | Dateien | Zeichen roh (MB) |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| [google/guava](https://github.com/google/guava) | Apache-2.0 | `fce80fd` | 27,4 | 36 % | 1144 | 10,9 |
| [spring-projects/spring-boot](https://github.com/spring-projects/spring-boot) | Apache-2.0 | `3d8ad8e` | 25,4 | 39 % | 3321 | 10,7 |
| [apereo/cas](https://github.com/apereo/cas) | Apache-2.0 | `45d89dd` | 28,9 | 35 % | 2685 | 10,1 |
| [spring-projects/spring-framework](https://github.com/spring-projects/spring-framework) | Apache-2.0 | `4cb62d8` | 52,0 | 19 % | 1686 | 10,1 |
| [apache/calcite](https://github.com/apache/calcite) | Apache-2.0 | `7d72586` | 24,5 | 41 % | 1048 | 9,8 |
| [conductor-oss/conductor](https://github.com/conductor-oss/conductor) | Apache-2.0 | `1d268e4` | 12,8 | 78 % | 1182 | 9,5 |
| [apache/commons-lang](https://github.com/apache/commons-lang) | Apache-2.0 | `e2a0789` | 7,9 | 100 % | 642 | 7,9 |
| [iluwatar/java-design-patterns](https://github.com/iluwatar/java-design-patterns) | MIT | `4cabb20` | 5,2 | 100 % | 2042 | 5,2 |
| [apolloconfig/apollo](https://github.com/apolloconfig/apollo) | Apache-2.0 | `504e5cd` | 3,8 | 100 % | 761 | 3,8 |
| [mockito/mockito](https://github.com/mockito/mockito) | MIT | `10b31ba` | 3,6 | 100 % | 1013 | 3,6 |
| [macrozheng/mall](https://github.com/macrozheng/mall) | Apache-2.0 | `dcaa93b` | 2,7 | 100 % | 524 | 2,7 |
| [hs-web/hsweb-framework](https://github.com/hs-web/hsweb-framework) | Apache-2.0 | `f2617a5` | 2,5 | 100 % | 723 | 2,4 |
| [codecentric/spring-boot-admin](https://github.com/codecentric/spring-boot-admin) | Apache-2.0 | `4501683` | 1,6 | 100 % | 418 | 1,6 |
| [pig-mesh/pig](https://github.com/pig-mesh/pig) | Apache-2.0 | `1939970` | 1,5 | 100 % | 554 | 1,4 |
| [elunez/eladmin](https://github.com/elunez/eladmin) | Apache-2.0 | `646c58c` | 0,8 | 100 % | 274 | 0,8 |
| [square/okhttp](https://github.com/square/okhttp) | Apache-2.0 | `1bd972a` | 0,2 | 100 % | 71 | 0,2 |

### SQL (`code-sql`)

Gezählt: **22,8 Mio. Zeichen** aus 82.613 Dateien; Gewicht in `code-standard`: 15 %.

| Repository | Lizenz | Commit | geeignet (MB) | gewählt | Dateien | Zeichen roh (MB) |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| [postgres/postgres](https://github.com/postgres/postgres) | PostgreSQL | `7fc2f04` | 7,3 | 100 % | 852 | 7,1 |
| [apache/spark](https://github.com/apache/spark) | Apache-2.0 | `63c95a0` | 2,8 | 100 % | 561 | 2,8 |
| [sqlfluff/sqlfluff](https://github.com/sqlfluff/sqlfluff) | MIT | `5f5205f` | 1,7 | 100 % | 2632 | 1,7 |
| [Thomas-George-T/HackerRank-SQL-Challenges-Solutions](https://github.com/Thomas-George-T/HackerRank-SQL-Challenges-Solutions) | MIT | `41e1fa6` | 0,0 | 100 % | 52 | 0,0 |
| [b-mc2/sql-create-context](https://github.com/b-mc2/sql-create-context) | CC BY 4.0 | `feste Revision` | – | alle | 78577 | 0,0 |
| [ben-nour/SQL-tips-and-tricks](https://github.com/ben-nour/SQL-tips-and-tricks) | MIT | `c5f547f` | 0,0 | 0 % | 0 | 0,0 |

## Eigenheiten und Schwächen

- **Frameworks sind überrepräsentiert.** Laravel-typischer Anwendungscode (Controller, Eloquent-Modelle, Migrationen, Blade) macht nur einen Teil von `code-php` aus; Symfony ist auf 20 % seiner Menge gedeckelt. Eigener Code würde das verbessern.
- **Blade ist klein** (rund 2 MB in den Laravel-Repositories) und steckt in `code-php`.
- **Vue ist mit 22 Mio. Zeichen die kleinste der großen Quellen.** Eine `.vue`-Datei enthält Template (HTML), Skript (JS oder TS) und Stil (CSS); die Statistik ähnelt deshalb teils der von JavaScript.
- **SQL besteht aus Test-SQL (Spark, PostgreSQL, sqlfluff) und aus Frage-Antwort-Paaren (`sql-create-context`)**, nicht aus der SQL-Alltagsarbeit gegen MySQL oder PostgreSQL. Test-SQL enthält Randfälle und Dialekte. SQL steckt außerdem in PHP-Strings und Laravel-Migrationen (`code-php`).
- **Chinesische und andere fremdsprachige Kommentare** (mall, eladmin, vue-admin-better u. a.) fallen zeilenweise heraus; die Zahl steht je Quelle im Prüfbericht.
- **Datentabellen** (Emoji- und Namenslisten, mehr als 100 Sonderzeichen oder mehr als 300 Akzentbuchstaben in einer Datei) werden ganz verworfen, im PHP-Teil 27 Dateien.
- **GitHub-Archive lassen Verzeichnisse mit `export-ignore` aus**, bei Laravel `tests/`. Testcode ist darum unterrepräsentiert.
- **Lizenzköpfe werden entfernt**, damit nicht in jeder Datei derselbe Absatz gezählt wird.
- **Kein TypeScript:** Es steht nicht in Sörens Stack, steckt aber in vielen Vue- und JavaScript-Repositories und wird nicht gelesen.

## Offen

- **Eigener Code von Sören:** wird als weitere Quelle ergänzt (zum Beispiel `code-eigen-php`). Aus eigenem Code kommen nur aggregierte N-Gramme ins Repo, nie Quelltext. Code von Arbeitgebern darf nicht verwendet werden.
- **Gewichtung zwischen Deutsch, Englisch und Code** steht noch aus.
- **Weitere SQL-Quellen,** etwa die sqllogictest-Dateien von DuckDB (großer Pool, aber eigener Leser nötig).
- **Lizenzpflichten:** Apache-2.0 und MIT verlangen die Nennung der Urheber bei Weitergabe des Codes. Für aggregierte N-Gramme ist das kein Problem, bei einer Veröffentlichung sollte die Liste der Repositories (Manifest) mitgeliefert werden.
