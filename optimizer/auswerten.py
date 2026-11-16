"""Wertet die Ergebnisse eines Optimierungslaufs aus.

Aufruf (aus dem Repo-Wurzelverzeichnis):
    python3 optimizer/auswerten.py optimizer/ergebnisse/lauf-01

Liest alle `<konfiguration>.txt` im Lauf-Ordner (ein Layout je Zeile, so wie `optimize_sa --append-solutions-to` sie
schreibt), bewertet jedes Layout

- in jeder Konfiguration des Laufs mit der Gesamtmischung (zeigt, ob ein Layout nur unter seinen Annahmen gut ist),
- in seiner eigenen Konfiguration getrennt mit Deutsch, Englisch und Code,

und schreibt `auswertung.md` und `auswertung.json` in den Lauf-Ordner.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OPTIMIZER = Path.home() / "keyboard" / "keyboard_layout_optimizer"
KORPORA = {
    "gesamt": REPO / "korpora" / "mischungen" / "gesamt-standard",
    "de": REPO / "korpora" / "mischungen" / "de-standard",
    "en": REPO / "korpora" / "mischungen" / "en-standard",
    "code": REPO / "korpora" / "mischungen" / "code-standard",
}
# Metriken, die in der Tabelle als eigene Spalte erscheinen (Name im Optimizer -> Kürzel)
METRIKEN = {"Finger Repeats": "SFB", "Movement Pattern": "Bewegung", "Key Costs": "Tasten",
            "No Handswitch in Trigram": "Trigr.", "Finger Balance": "Balance", "Modifier Usage": "Mod"}


def bewerte(konfiguration, korpus, layouts):
    kosten = konfiguration.rsplit("-", 1)[1]
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as f:
        f.write("\n".join(layouts) + "\n")
        datei = f.name
    try:
        aus = subprocess.run(
            [str(OPTIMIZER / "target" / "release" / "evaluate"), "--json", "--do-not-remove-whitespace",
             "-l", str(REPO / "optimizer" / "tastaturen" / f"{konfiguration}.yml"),
             "-e", str(REPO / "optimizer" / "bewertung" / f"{kosten}.yml"),
             "-n", str(KORPORA[korpus]), "--from-file", datei],
            cwd=OPTIMIZER, capture_output=True, text=True, check=True).stdout
    finally:
        Path(datei).unlink()
    erg = {}
    for eintrag in json.loads(aus):
        metriken = {}
        for gruppe in eintrag["details"]["individual_results"]:
            for m in gruppe["metric_costs"]:
                if m["core"]["name"] in METRIKEN:
                    metriken[METRIKEN[m["core"]["name"]]] = m["weighted_cost"]
        erg[eintrag["details"]["layout"]] = {"kosten": eintrag["total_cost"], "metriken": metriken}
    return erg


def bild(layout):
    """3 × 5 je Hand plus Daumen; Leertaste als ␣."""
    z = ["␣" if c == " " else c for c in layout]
    zeilen = [" ".join(z[r * 10:r * 10 + 5]) + "   " + " ".join(z[r * 10 + 5:r * 10 + 10]) for r in range(3)]
    zeilen.append(" " * 8 + z[30] + "   " + z[31])
    return "\n".join(zeilen)


def main():
    lauf = Path(sys.argv[1]).resolve()
    quellen = {p.stem: [z for z in p.read_text(encoding="utf-8").split("\n") if z] for p in sorted(lauf.glob("*.txt"))}
    konfigurationen = list(quellen)
    alle = sorted({l for ls in quellen.values() for l in ls})

    quer = {k: bewerte(k, "gesamt", alle) for k in konfigurationen}
    eigen = {k: {s: bewerte(k, s, sorted(set(ls))) for s in ("de", "en", "code")} for k, ls in quellen.items()}

    ergebnisse = []
    for k, ls in quellen.items():
        for l in sorted(set(ls)):
            ergebnisse.append({
                "konfiguration": k, "layout": l, "gefunden": ls.count(l),
                "kosten": quer[k][l]["kosten"], "metriken": quer[k][l]["metriken"],
                "quer": {k2: quer[k2][l]["kosten"] for k2 in konfigurationen},
                "sprachen": {s: eigen[k][s][l]["kosten"] for s in ("de", "en", "code")},
            })
    (lauf / "auswertung.json").write_text(json.dumps(ergebnisse, ensure_ascii=False, indent=1) + "\n",
                                          encoding="utf-8")

    md = [f"# Auswertung {lauf.name}", "",
          "Erzeugt von `optimizer/auswerten.py`. Kosten: niedriger ist besser; nur innerhalb derselben "
          "Konfiguration direkt vergleichbar.", ""]
    for k in konfigurationen:
        zeilen = sorted((e for e in ergebnisse if e["konfiguration"] == k), key=lambda e: e["kosten"])
        md += [f"## {k}", "", f"{len(quellen[k])} Läufe, {len(zeilen)} verschiedene Layouts.", "",
               "| # | Layout | × | Kosten | DE | EN | Code | " + " | ".join(METRIKEN.values()) + " |",
               "| --- | --- | --- | --- | --- | --- | --- | " + " | ".join("---" for _ in METRIKEN) + " |"]
        for i, e in enumerate(zeilen, 1):
            m = e["metriken"]
            md.append(f"| {i} | `{e['layout'].replace(' ', '␣')}` | {e['gefunden']} | {e['kosten']:.2f} | "
                      f"{e['sprachen']['de']:.2f} | {e['sprachen']['en']:.2f} | {e['sprachen']['code']:.2f} | "
                      + " | ".join(f"{m.get(n, 0):.2f}" for n in METRIKEN.values()) + " |")
        md += ["", "Beste drei:", ""]
        for e in zeilen[:3]:
            md += ["```", bild(e["layout"]), "```", ""]

    md += ["## Quervergleich", "", "Jedes Layout in jeder Konfiguration (Gesamtmischung), sortiert nach Mittelwert.", "",
           "| Layout | gefunden in | " + " | ".join(konfigurationen) + " | Mittel |",
           "| --- | --- | " + " | ".join("---" for _ in konfigurationen) + " | --- |"]
    gesehen = {}
    for e in ergebnisse:
        gesehen.setdefault(e["layout"], (e["quer"], set()))[1].add(e["konfiguration"])
    for l, (q, herkunft) in sorted(gesehen.items(), key=lambda x: sum(x[1][0].values()))[:30]:
        md.append(f"| `{l.replace(' ', '␣')}` | {', '.join(sorted(herkunft))} | "
                  + " | ".join(f"{q[k]:.2f}" for k in konfigurationen) + f" | {sum(q.values()) / len(q):.2f} |")
    (lauf / "auswertung.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{len(alle)} Layouts ausgewertet -> {lauf / 'auswertung.md'}")


if __name__ == "__main__":
    main()
