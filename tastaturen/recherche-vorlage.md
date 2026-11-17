# Vorlage für manuelle Recherche

Für Tastaturen und Angaben, die keine maschinenlesbare Quelle liefert. Ergebnisse landen in `tastaturen/manuell.json` und werden beim nächsten Aufbau der Datenbank mit den übrigen Quellen zusammengeführt.

## Format

Ein Block je Tastatur. Nur eintragen, was auf einer Seite steht, die Du gelesen hast. Was nicht dasteht, bleibt weg; leer heißt „unbekannt“, nicht „nein“.

```yaml
name: Svalboard Lightly
hersteller: Svalboard
url: https://svalboard.com/products/lightly          # Produkt- oder Projektseite
belege:                                               # jede Seite, aus der eine Angabe stammt
  - https://svalboard.com/products/lightly
  - https://svalboard.com/pages/specs
gelesen_am: 2026-11-17
facetten:                                             # IDs und Werte aus tastaturen/facetten.json
  geteilt: ja                                         # ja | abbrechbar | einteilig-geteilt | nein
  tasten: [60]                                        # eine Zahl oder [min, max] bei Varianten
  tasten_je_haelfte: 30
  raster: 3x5                                         # Reihen x Spalten je Hand, ohne Daumen
  daumentasten: 6                                     # je Hand
  versatz: [sonstige]                                 # spalten | ortho | reihen | mulde | radial | alice | sonstige
  spreizung: nein
  maus: optional                                      # ja | optional | nein
  maus_art: [trackball, trackpoint]                   # trackball | trackpad | trackpoint | joystick
  schalter: [magnetisch]                              # mx | choc-v1 | choc-v2 | gateron-lp | alps | topre | magnetisch | optisch | schere | membran | knickfeder | proprietaer
  schalter_montage: [hotswap]                         # hotswap | geloetet | fest
  profil: normal                                      # flach | normal
  drahtlos: optional                                  # ja | optional | nein
  drahtlos_technik: [bluetooth]                       # bluetooth | funk-2-4 | wifi | funk-proprietaer
  energie: [kabel, akku-fest]                         # kabel | akku-fest | akku-wechselbar | aa | aaa | knopfzelle | solar
  firmware: [qmk, vial]                               # qmk | zmk | kmk | rmk | vial | via | kaleidoscope | uhk | proprietaer
  open_source_hardware: nein
  hardware_lizenz: CERN-OHL-S-2.0                     # SPDX-Kennung, wenn bekannt
  verfuegbarkeit: [fertig, kit]                       # selbstbau | kit | fertig | gruppenbestellung | prototyp | eingestellt
  zahlenreihe: nein
  drehgeber: nein
  display: nein
  zelt: ja                                            # Tenting: ja | optional | nein
  jahr: 2023
  preis: "800 USD"                                    # Basismodell, wie auf der Seite angegeben
hinweise: |
  Freitext für alles, was in keine Facette passt (z. B. "Daumencluster mit 6 Richtungen je Taste").
```

Ein Block, dem Felder fehlen, ist ausdrücklich erwünscht. Lieber drei sichere Angaben als zehn geschätzte.

Wenn Dir Felder fehlen, die Du für die Auswahl einer Tastatur brauchst, schreib sie unter `hinweise` dazu. Dann ergänzen wir das Vokabular in `facetten.json`.

## Was die Quellen schlecht abdecken

1. **Energieversorgung und Funktechnik:** Akku fest, wechselbar oder AA/AAA; Bluetooth oder 2,4-GHz-Empfänger. Steht fast nur auf Herstellerseiten.
2. **Maus integriert:** Trackball, Trackpad, Trackpoint, vor allem bei kommerziellen Tastaturen.
3. **Abbrechbar (Snap-bar):** Einteilige Platinen, die sich in zwei Hälften brechen lassen; steht meist nur im Fließtext.
4. **Kommerzielle Tastaturen mit eigener Firmware:** Diese Herstellerseiten haben unseren automatischen Abruf gedrosselt; siehe `offen` in `manuell.json`.
5. **Neue Tastaturen 2024–2026**, die noch in keiner Sammlung stehen: Kickstarter, Gruppenbestellungen, asiatische Anbieter.
