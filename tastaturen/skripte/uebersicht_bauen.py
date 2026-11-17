"""Interne Prüfseite: alle Geräte von oben nach unten, je Eintrag Nummer, ID (Slug), Fotos (verlinkt), Tastenumriss,
Kurzangaben und fehlende Kernangaben. Zum Durchgehen und Melden von Nachträgen ("ID corne-ish-zen: …").

Ausgang: tastaturen/web/dist/review/index.html und review/NNN.html (je SEITE Geräte, Reihenfolge wie die Hauptseite).
Voraussetzung: seite_bauen.py (dist/, s.css, k/) und bilder_sammeln.py (bilder.json).
Nicht zur Veröffentlichung: Fotos sind fremde Werke und nur verlinkt; jede Seite trägt noindex.

Aufruf: python3 tastaturen/skripte/uebersicht_bauen.py
"""

import html
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seite_bauen as sb  # noqa: E402
from basis import DB, QUELLEN  # noqa: E402

SEITE = 200
BILD_VORRANG = ["manuell", "yal", "aposymbiont", "keebfolio", "golem", "shops", "qmk", "kbdnews"]
KERN = [("split", "split"), ("keys", "keys"), ("stagger", "stagger"), ("switch_interface", "switches"),
        ("wireless", "wireless"), ("availability", "availability")]
e = html.escape

CSS = """
.rv{max-width:80rem;margin:0 auto;padding:0 16px 32px}
.nav{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:12px 0}
.nav a,.nav span{min-height:40px;display:inline-flex;align-items:center;padding:0 12px;border:1px solid var(--line);border-radius:8px;text-decoration:none}
.c{border-top:1px solid var(--line);padding:14px 0}
.c header{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline}
.nr{color:var(--mut);font-variant-numeric:tabular-nums}
.id{background:var(--soft);border:1px solid var(--line);border-radius:4px;padding:1px 6px;user-select:all}
.c b{font-size:1.05rem}
.mk{color:var(--mut)}
.sp{margin:4px 0;color:var(--mut);font-size:.9rem}
.miss{margin:4px 0;font-size:.85rem;color:var(--warn)}
.md{display:flex;flex-wrap:wrap;gap:10px;margin:8px 0}
.md figure{margin:0;display:flex;flex-direction:column;gap:2px}
.md img{height:150px;width:auto;max-width:100%;object-fit:contain;background:var(--soft);border:1px solid var(--line);border-radius:6px}
.md figcaption{font-size:.7rem;color:var(--mut)}
.md .lay svg{height:150px;width:auto;max-width:min(100%,32rem)}
.md .leer{height:150px;min-width:9rem;display:flex;align-items:center;justify-content:center;border:1px dashed var(--line);border-radius:6px;color:var(--mut);font-size:.8rem;padding:0 10px}
.lay rect{fill:var(--key);stroke:var(--keyl);stroke-width:.05}
.qs{font-size:.8rem;color:var(--mut);margin:2px 0;overflow-wrap:anywhere}
.tab{width:100%;font-size:.9rem}
"""


def main():
    voc, geraete, layouts, quellen = sb.laden()
    F = sb.facetten_bauen(voc, geraete)
    bilder = json.loads((QUELLEN / "bilder.json").read_text(encoding="utf-8"))
    db = sqlite3.connect(DB)
    ds_je = defaultdict(list)
    for slug, q, qid in db.execute("SELECT g.slug, d.quelle, d.quell_id FROM geraet g JOIN geraet_datensatz gd ON "
                                   "gd.geraet_id = g.id JOIN datensatz d ON d.id = gd.datensatz_id"):
        ds_je[slug].append((q, qid))
    ziel = sb.DIST / "review"
    ziel.mkdir(parents=True, exist_ok=True)
    seiten = [geraete[i:i + SEITE] for i in range(0, len(geraete), SEITE)]
    n_seiten = len(seiten)
    mit_foto = mit_lay = 0

    def nav(i):
        teile = [f'<a href="index.html">Overview</a>']
        if i > 0:
            teile.append(f'<a href="{i:03d}.html" rel=prev>← {i}</a>')
        teile.append(f'<span>Page {i + 1} of {n_seiten}</span>')
        if i + 1 < n_seiten:
            teile.append(f'<a href="{i + 2:03d}.html" rel=next>{i + 2} →</a>')
        return '<nav class=nav>' + "".join(teile) + '</nav>'

    uebersicht = []
    for i, teil in enumerate(seiten):
        karten = []
        for j, g in enumerate(teil):
            nr = i * SEITE + j + 1
            fac = g["facets"]
            # Fotos: höchstens zwei, aus verschiedenen Quellen, nach Vorrang
            fotos, gesehen = [], set()
            for q, qid in sorted(ds_je[g["id"]], key=lambda x: BILD_VORRANG.index(x[0]) if x[0] in BILD_VORRANG else 99):
                for u in bilder.get(f"{q}:{qid}", [])[:1]:
                    if q not in gesehen and u not in {f[1] for f in fotos} and len(fotos) < 2:
                        fotos.append((q, u))
                        gesehen.add(q)
            mit_foto += bool(fotos)
            media = [f'<figure><img src="{e(u)}" alt="" loading=lazy decoding=async referrerpolicy=no-referrer>'
                     f'<figcaption>photo: {e(q)}</figcaption></figure>' for q, u in fotos]
            if not fotos:
                dt = next((qid for q, qid in ds_je[g["id"]] if q == "deskthority"), None)
                media.append(f'<div class=leer><a href="https://deskthority.net/wiki/{e(dt.replace(" ", "_"))}" rel=nofollow>'
                             f'photo on Deskthority</a></div>' if dt else '<div class=leer>no photo</div>')
            if g["layout"] and str(g["layout"]) in layouts:
                lay = layouts[str(g["layout"])]
                mit_lay += 1
                media.append(f'<figure class=lay>{sb.svg(lay)}<figcaption>{len(lay["keys"])} keys · '
                             f'{e(lay["name"])}</figcaption></figure>')
            else:
                media.append('<div class=leer>no key layout</div>')
            fehlt = [label for k, label in KERN if k not in fac]
            if not g["maker"]:
                fehlt.append("maker")
            abg = [k for k in g.get("derived", [])]
            zus = sb.zusammenfassung(g, F) + (f" · derived: {', '.join(abg)}" if abg else "")
            qn = sorted({q for q, _ in ds_je[g["id"]]})
            links = " · ".join(f'<a href="{e(u)}" rel=nofollow>{e(sb.urlparse(u).netloc)}</a>' for u in g["links"][:4])
            karten.append(
                f'<article class=c id="{e(g["id"])}"><header><span class=nr>#{nr}</span>'
                f'<code class=id>{e(g["id"])}</code><b>{e(g["name"])}</b>'
                f'<span class=mk>{e(g["maker"] or "maker unknown")}</span></header>'
                f'<p class=sp>{e(zus) or "no facts yet"}</p>'
                + (f'<p class=miss>Missing: {", ".join(fehlt)}</p>' if fehlt else "")
                + f'<div class=md>{"".join(media)}</div>'
                f'<p class=qs>{len(qn)} source{"s" if len(qn) != 1 else ""}: {", ".join(qn)} · '
                f'<a href="../k/{e(g["id"])}.html">details</a>' + (f' · {links}' if links else "") + '</p></article>')
        inhalt = (f'<div class=rv>{nav(i)}<h1>Review list {i * SEITE + 1}–{i * SEITE + len(teil)}</h1>'
                  + "".join(karten) + nav(i) + '</div>')
        (ziel / f"{i + 1:03d}.html").write_text(seite(f"Review {i + 1}/{n_seiten}", inhalt), encoding="utf-8")
        uebersicht.append(f'<tr><td><a href="{i + 1:03d}.html">{i + 1}</a></td><td class=num>#{i * SEITE + 1}–'
                          f'{i * SEITE + len(teil)}</td><td>{e(teil[0]["name"])} … {e(teil[-1]["name"])}</td></tr>')
    kopf = (f'<div class=rv><h1>Review list</h1><p>{len(geraete):,} keyboards in the order of the main page (best '
            f'documented first), {SEITE} per page. Each entry shows its running number and its <b>ID</b> (click to '
            f'select). Report additions as „ID: what is missing or wrong“.</p><p class=note>{mit_foto:,} with photo, '
            f'{mit_lay:,} with key layout. Photos are linked from the sources and remain the work of their creators; '
            f'internal use only, not for publication.</p><table class=tab><thead><tr><th>Page</th><th>Numbers</th>'
            f'<th>From … to</th></tr></thead><tbody>{"".join(uebersicht)}</tbody></table></div>')
    (ziel / "index.html").write_text(seite("Review list", kopf), encoding="utf-8")
    for p in ziel.glob("*.html"):
        sb.gz(p)
    print(f"{n_seiten} Seiten, {mit_foto} mit Foto, {mit_lay} mit Layout von {len(geraete)} Geräten")


def seite(titel, inhalt):
    return (f'<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport '
            f'content="width=device-width,initial-scale=1"><meta name=robots content="noindex,nofollow">'
            f'<title>{e(titel)} – {sb.TITEL}</title><meta name=color-scheme content="light dark">{sb.THEME_JS}'
            f'<link rel=stylesheet href="../s.css"><style>{CSS}</style></head><body><header class=top><div class=tb>'
            f'<a class=brand href="../">⌨ {sb.TITEL}</a><a href="index.html">Review list</a></div></header>'
            f'{inhalt}</body></html>')


if __name__ == "__main__":
    main()
