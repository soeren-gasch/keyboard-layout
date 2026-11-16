# Optimizer

Bewertung und Optimierung mit dem [keyboard_layout_optimizer](https://github.com/dariogoetz/keyboard_layout_optimizer) von Dario Götz (Rust). Der Optimizer liegt außerhalb dieses Repositorys (auf dem Server unter `~/keyboard/keyboard_layout_optimizer`); hier stehen nur unsere Konfigurationen, Aufrufe und Ergebnisse.

Stand: 16.11.2026

## Build auf dem Server

Der Server hat weder C-Compiler noch Linker noch OpenSSL und keine Root-Rechte. Gebaut wird deshalb so:

| Baustein | Version | Herkunft | Ort |
| --- | --- | --- | --- |
| Optimizer | Commit `8c8ec9f` (24.04.2026) | GitHub, Original von Dario Götz | `~/keyboard/keyboard_layout_optimizer` |
| Rust | 1.100.0 | `rustup-init` von static.rust-lang.org, Prüfsumme geprüft | `~/.cargo` |
| Zig (als C-Compiler und Linker) | 0.17.1 | PyPI-Paket `ziglang`, Prüfsumme geprüft | `~/.local/zig` |
| Wrapper `cc`, `c++`, `ar`, `ranlib` | – | eigene Skripte, übersetzen das Rust-Ziel `x86_64-unknown-linux-gnu` in Zigs `x86_64-linux-gnu` | `~/keyboard/werkzeuge/zig-wrapper` |

**Lokale Änderung am Optimizer:** In `keyboard_layout_optimizer/Cargo.toml` ist `reqwest` auf die dort bereits vorbereitete rustls-Variante umgestellt (`features = ["blocking", "json", "rustls-tls"], default-features = false`), weil OpenSSL fehlt. `reqwest` wird nur zum Veröffentlichen von Ergebnissen beim Webdienst des Projekts gebraucht.

```sh
W=~/keyboard/werkzeuge/zig-wrapper
cd ~/keyboard/keyboard_layout_optimizer
env PATH="$W:$HOME/.cargo/bin:$PATH" CC="$W/cc" CXX="$W/c++" AR="$W/ar" \
    CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER="$W/cc" cargo build --release
```

Die Wrapper gelten nur für diesen Aufruf; sie liegen nicht im allgemeinen `PATH`.

## Funktionsprobe

```sh
cd ~/keyboard/keyboard_layout_optimizer
./target/release/evaluate -n ~/keyboard/keyboard-layout/korpora/mischungen/gesamt-standard \
    "jduax phlmwqß ctieo bnrsg fvüäö yz,.k"
```

Bone-Layout auf dem Standard-Keyboard des Optimizers mit unserer Gesamtmischung: Kosten 329,49, keine fehlenden Zeichen (16.11.2026).

## N-Gramme

Unsere Dateien unter `korpora/ngramme/` und `korpora/mischungen/` haben das Format des Optimizers und lassen sich direkt mit `-n <ordner>` angeben. Die Gesamtmischung ist `korpora/mischungen/gesamt-standard` (65 % Deutsch, 25 % Englisch, 10 % Code).

## Tastatur-Modell Voyager, 32 Tasten

`optimizer/konfiguration.py` erzeugt alle Konfigurationen; die YAML-Dateien unter `tastaturen/` und `bewertung/` sind daraus generiert und werden nicht von Hand bearbeitet.

```sh
python3 optimizer/konfiguration.py
```

| Baustein | Festlegung |
| --- | --- |
| Tasten | je Hand 3 × 5 plus die Daumentaste unter der inneren Spalte (QMK `k24`, `k51`) |
| Geometrie | aus QMK `keyboards/zsa/voyager/keyboard.json`: Spaltenversatz 0,5 / 0,25 / 0 / 0,25 / 0,5 Tasten (kleiner Finger … Zeige innen), 1 Taste = 50 Einheiten; Ferris Sweep und Corne ebenso aus QMK (siehe `GEOMETRIEN` im Skript) |
| Ebenen | 0 Basis, 1 Shift, 2 Symbole, 3 Navigation und Ziffern |
| Optimiert | Basis und Shift gemeinsam; alle 32 Tasten frei, auch Leertaste und E |
| Fest | Symbol- und Navigations-Ebene, übernommen aus Oryx `xmKwY` |
| Shift-Belegung | QWERTZ: `,` → `;`, `.` → `:`, `-` → `_` |
| q und ß | auf der Symbol-Ebene (Daumentasten) als Platzhalter; später Kombo oder Ebene |
| Modifikatoren | gehalten auf der Grundreihe, links und rechts symmetrisch, jeweils mit der Gegenhand |
| Ctrl, Alt, Win | auf der Grundreihe bzw. dem Daumen, kommen in den Korpora nicht vor und werden nicht bewertet |

### Wo die Geometrie wirkt

Keine der eingeschalteten Metriken liest die Koordinaten (`positions`). Sie arbeiten mit Matrix-Spalte und -Reihe, Finger, Fingerlänge (`movement_pattern`) und den von Hand gesetzten Tastenkosten (`key_costs`). Die Koordinaten dienen nur dem Plot und den abgeschalteten Metriken (`kla_distance`, Oxey-Metriken außer den Rolls). Folge: Voyager, Ferris Sweep und Corne ergeben mit denselben Tastenkosten dieselben Bewertungen (geprüft am 16.11.2026). Ein Unterschied zwischen den Tastaturen, etwa der starke Versatz des kleinen Fingers beim Sweep, muss in die Tastenkosten übersetzt werden.

### Home-Row-Varianten

Spalten von außen nach innen, gilt für beide Hände gleich:

| Variante | kleiner Finger | Ring | Mittel | Zeige | Zeige innen | Daumen (halten) |
| --- | --- | --- | --- | --- | --- | --- |
| A (wie heute plus Alt) | Navigation | Symbole | Shift | Ctrl | Win | Alt |
| B (GACS) | Win | Alt | Ctrl | Shift | Navigation | Symbole |
| C (Ring entlastet) | Navigation | Win/Alt | Symbole | Shift | Ctrl | Alt |

### Kostenprofile

| Profil | Herkunft |
| --- | --- |
| `standard` | Tastenkosten der Corne-Konfiguration des Optimizers, auf 3 × 5 gekürzt; Fingerlast wie Optimizer-Standard |
| `soeren` | Sörens Einschätzung vom 16.11.2026: kleine Finger weniger teuer (oben 14, Grundreihe 4, unten 8), Ringfinger teurer (oben 11, Grundreihe 4, unten 16); angestrebte Last kleiner Finger 1,3 statt 1,0, Ring 1,3 statt 1,6 |

Die Bewertung entspricht `config/evaluation/default.yml` des Optimizers mit einer Änderung: Die Metrik „Shortcut Keys“ ist eingeschaltet und bestraft Z, X, C und V außerhalb der linken Hand (Windows-Kürzel, Maus rechts), Gewicht 0,35 je Taste.

### Referenz

| Layout | Kosten (Variante A, standard) |
| --- | --- |
| Ist-Zustand Oryx `xmKwY` (q, ß auf der Basis, ohne Punkt) | 199,11 |
| Startbelegung `NEU_START` (Punkt und Strich statt q und ß) | 211,22 |

## Läufe

| Lauf | Datum | Inhalt | Ergebnisse |
| --- | --- | --- | --- |
| 01 | 16.11.2026 | Simulated Annealing (`sa.yml` Standard), zufälliger Start, 3 Varianten × 2 Kostenprofile × 6 Läufe, `gesamt-standard` | `ergebnisse/lauf-01/` |

Befunde aus Lauf 01 (Auswertung: [`ergebnisse/lauf-01/auswertung.md`](ergebnisse/lauf-01/auswertung.md)):

- **Die Suche konvergiert nicht.** Keines der 36 Ergebnisse wurde zweimal gefunden; innerhalb einer Konfiguration streuen die Kosten um 20 bis 30 Punkte (beste 158,3, schlechteste 191,7). Ursache ist vor allem die fest einprogrammierte schnelle Abkühlung (siehe `plan-48h.md`).
- **Die Leertaste landet immer auf einem Daumen** (36 von 36), ohne Vorgabe. Auf dem anderen Daumen liegt meist ein häufiger Buchstabe: s (13), e (7), u (6), t (5).
- **E** liegt in 28 von 36 Läufen auf der Grundreihe, in 7 auf dem Daumen.
- Bestes Ergebnis: Variante B mit Kostenprofil `soeren`, 158,31; zum Vergleich das Ist-Layout 199,11 (Variante A, standard).
- Code kostet etwa doppelt so viel wie Prosa, weil Symbol- und Navigations-Ebene fest sind und jedes Symbol einen gehaltenen Modifikator braucht.

## Noch offen

- Tastenkosten je Tastatur aus dem Spaltenversatz ableiten (Sweep: kleiner Finger 0,93 Tasten tiefer), erst dann ist der Vergleich mit Sweep und Corne aussagekräftig
- Leertaste darf nicht auf einer Modifikator-Position landen (Mod-Tap auf der Leertaste); bisher nicht im Modell
- Symbol- und Navigations-Ebene optimieren, Kombos für q und ß
