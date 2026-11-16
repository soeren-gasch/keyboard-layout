"""Misst den Anteil britischer und amerikanischer Schreibung in einem Text.

Grundlage ist eine Liste von Wortpaaren (colour/color, organise/organize, centre/center, travelled/traveled,
grey/gray, mum/mom ...). Gezählt werden nur Wörter, die in genau einer der beiden Varianten vorkommen.
Mehrdeutige Paare (licence/license, practise/practice, programme/program, metre/meter, cheque/check, tyre/tire,
towards/toward, tonne/ton) sind bewusst nicht enthalten.

Der Anteil britisch = britische Treffer / (britische + amerikanische Treffer) ist eine Kennzahl je Quelle und steht
in deren meta.json. Er dient dazu, die Gewichte einer Mischung am Ziel "britisch bevorzugt" auszurichten.
Die Messung ist grob (Eigennamen wie "Labor Party" oder "Gray" zählen mit) und bei Quellen mit wenigen Treffern
unsicher; deshalb steht die Zahl der Treffer dabei.
"""

import re

# (britisch, amerikanisch)
_PAARE = [
    ("centre", "center"), ("centres", "centers"), ("centred", "centered"), ("centring", "centering"),
    ("theatre", "theater"), ("theatres", "theaters"), ("litre", "liter"), ("litres", "liters"),
    ("fibre", "fiber"), ("fibres", "fibers"), ("calibre", "caliber"), ("sombre", "somber"),
    ("spectre", "specter"), ("manoeuvre", "maneuver"), ("manoeuvres", "maneuvers"),
    ("manoeuvred", "maneuvered"), ("manoeuvring", "maneuvering"),
    ("defence", "defense"), ("defences", "defenses"), ("offence", "offense"), ("offences", "offenses"),
    ("pretence", "pretense"),
    ("travelled", "traveled"), ("travelling", "traveling"), ("traveller", "traveler"), ("travellers", "travelers"),
    ("cancelled", "canceled"), ("cancelling", "canceling"), ("labelled", "labeled"), ("labelling", "labeling"),
    ("modelled", "modeled"), ("modelling", "modeling"), ("signalled", "signaled"), ("signalling", "signaling"),
    ("fuelled", "fueled"), ("fuelling", "fueling"), ("counselled", "counseled"), ("counselling", "counseling"),
    ("levelled", "leveled"), ("levelling", "leveling"), ("marvellous", "marvelous"),
    ("jewellery", "jewelry"), ("skilful", "skillful"), ("wilful", "willful"),
    ("fulfil", "fulfill"), ("fulfils", "fulfills"), ("enrol", "enroll"), ("enrols", "enrolls"),
    ("enrolment", "enrollment"), ("instalment", "installment"),
    ("grey", "gray"), ("greys", "grays"), ("greyed", "grayed"), ("plough", "plow"), ("ploughs", "plows"),
    ("mould", "mold"), ("moulds", "molds"), ("moustache", "mustache"), ("aluminium", "aluminum"),
    ("artefact", "artifact"), ("artefacts", "artifacts"), ("sceptic", "skeptic"), ("sceptics", "skeptics"),
    ("sceptical", "skeptical"), ("scepticism", "skepticism"), ("catalogue", "catalog"),
    ("catalogues", "catalogs"), ("pyjamas", "pajamas"), ("aeroplane", "airplane"), ("aeroplanes", "airplanes"),
    ("mum", "mom"), ("mummy", "mommy"), ("ageing", "aging"), ("cosy", "cozy"),
    ("analyse", "analyze"), ("analysed", "analyzed"), ("analysing", "analyzing"),
    ("paralyse", "paralyze"), ("paralysed", "paralyzed"), ("catalyse", "catalyze"),
    ("behavioural", "behavioral"),
]

# -our / -or: Stamm + "ur" + Endung (britisch) bzw. Stamm + "r" + Endung (amerikanisch)
_OUR = ["colo", "favo", "hono", "neighbo", "behavio", "labo", "harbo", "humo", "rumo", "flavo", "savio",
        "vigo", "odo", "armo", "clamo", "endeavo", "parlo", "splendo", "tumo", "valo", "vapo"]
_OUR_ENDUNG = ["", "s", "ed", "ing", "ful", "less", "able", "ably", "ite", "ites", "er", "ers", "hood", "hoods"]

# -ise / -ize: nur Verben, die es in beiden Varianten gibt
_ISE = ["organ", "real", "recogn", "apolog", "critic", "emphas", "summar", "minim", "maxim", "author",
        "special", "capital", "categor", "colon", "civil", "general", "memor", "util", "final", "personal",
        "normal", "modern", "central", "digit", "stabil", "standard", "symbol", "sympath", "visual", "mobil",
        "industrial", "legal", "local", "national", "optim", "priorit", "popular", "familiar", "commercial",
        "criminal", "fertil", "hospital", "hypothes", "jeopard", "monopol", "neutral", "ostrac", "penal",
        "revolution", "scrutin", "social", "synchron", "synthes", "trivial", "vandal", "verbal"]
_ISE_ENDUNG = [("ise", "ize"), ("ised", "ized"), ("ises", "izes"), ("ising", "izing"),
               ("isation", "ization"), ("isations", "izations"), ("iser", "izer"), ("isers", "izers")]


def _tabelle():
    t = {}
    for b, a in _PAARE:
        t[b] = "b"
        t[a] = "a"
    for stamm in _OUR:
        for e in _OUR_ENDUNG:
            t[stamm + "ur" + e] = "b"
            t[stamm + "r" + e] = "a"
    for stamm in _ISE:
        for b, a in _ISE_ENDUNG:
            t[stamm + b] = "b"
            t[stamm + a] = "a"
    return t


TABELLE = _tabelle()
_WORT = re.compile(r"[a-z]+")


def zaehle(text, zaehler):
    """Zählt britische und amerikanische Schreibvarianten in `text` in `zaehler`.

    Schlüssel: 'b:<wort>' bzw. 'a:<wort>'."""
    tabelle = TABELLE
    for w in _WORT.findall(text.lower()):
        art = tabelle.get(w)
        if art:
            zaehler[art + ":" + w] += 1


def zusammenfassen(zaehler, top=8):
    britisch = sum(n for k, n in zaehler.items() if k[0] == "b")
    amerikanisch = sum(n for k, n in zaehler.items() if k[0] == "a")
    gesamt = britisch + amerikanisch

    def haeufigste(art):
        return [[k[2:], n] for k, n in sorted(((k, n) for k, n in zaehler.items() if k[0] == art),
                                              key=lambda x: -x[1])[:top]]

    return {
        "britisch": britisch,
        "amerikanisch": amerikanisch,
        "anteil_britisch": round(britisch / gesamt, 4) if gesamt else None,
        "haeufigste_britisch": haeufigste("b"),
        "haeufigste_amerikanisch": haeufigste("a"),
    }
