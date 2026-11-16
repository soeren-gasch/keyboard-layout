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

## Noch offen

- Tastaturbeschreibung für das Voyager (32 genutzte Tasten) und für spätere Kandidaten (Ferris Sweep, Corne)
- Bewertung des aktuellen Layouts, dann Optimierung von Grund auf
