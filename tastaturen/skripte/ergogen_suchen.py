"""Sucht Ergogen-Konfigurationen in den GitHub-Repositories, die in der Datenbank vorkommen.

Aufruf (aus dem Repo-Wurzelverzeichnis, nach datenbank_bauen.py):
    python3 tastaturen/skripte/ergogen_suchen.py            # alle noch nicht geprüften Repositories
    python3 tastaturen/skripte/ergogen_suchen.py --neu      # alle erneut prüfen

Je Repository: Klon ohne Dateiinhalte (--filter=blob:none, --depth 1), Suche im Dateibaum nach *.yaml/*.yml, Laden nur
dieser Dateien, Prüfung auf Ergogen-Merkmale (Schlüssel "points" mit "zones"). Treffer werden unter
~/keyboard/tastatur-quellen/ergogen/<besitzer>__<repo>/<pfad> abgelegt und mit Commit in tastaturen/ergogen.json
festgehalten (Manifest für reproduzierbares Laden). Geprüfte Repositories ohne Treffer stehen ebenfalls darin.
"""

import json
import re
import sqlite3
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from basis import DB, ORDNER, QUELLEN  # noqa: E402

MANIFEST = ORDNER / "ergogen.json"
ZIEL = QUELLEN / "ergogen"
FREMD = {"qmk/qmk_firmware", "zmkfirmware/zmk", "vial-kb/vial-qmk", "jhelvy/splitkbcompare", "precondition/keymapdb"}


def repos_aus_db():
    db = sqlite3.connect(DB)
    erg = set()
    for (name,) in db.execute("SELECT quell_id FROM datensatz WHERE quelle = 'github'"):
        erg.add(name)
    for q, url, weitere in db.execute("SELECT quelle, url, weitere_urls FROM datensatz"):
        for u in [url or ""] + ([] if q == "keymapdb" else json.loads(weitere or "[]")):
            m = re.search(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", u or "")
            if m:
                r = f"{m.group(1)}/{m.group(2)}".removesuffix(".git")
                if r.lower() not in FREMD:
                    erg.add(r)
    return sorted(erg, key=str.lower)


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=180)


def ist_ergogen(text):
    return bool(re.search(r"(?m)^points\s*:", text) and re.search(r"(?m)^\s+zones\s*[.:]", text))


def pruefe(repo):
    with tempfile.TemporaryDirectory() as tmp:
        r = git("clone", "-q", "--filter=blob:none", "--depth", "1", "--no-checkout",
                f"https://github.com/{repo}", tmp)
        if r.returncode:
            return repo, {"fehler": r.stderr.strip()[-200:]}
        commit = git("rev-parse", "HEAD", cwd=tmp).stdout.strip()
        dateien = [p for p in git("ls-tree", "-r", "--name-only", "HEAD", cwd=tmp).stdout.splitlines()
                   if p.lower().endswith((".yaml", ".yml")) and not p.startswith(".github/")]
        treffer = []
        dateien.sort(key=lambda p: (0 if "ergogen" in p.lower() else 1 if "config" in p.lower() else 2, p))
        for p in dateien[:400]:
            inhalt = git("show", f"HEAD:{p}", cwd=tmp)
            if inhalt.returncode == 0 and ist_ergogen(inhalt.stdout):
                ziel = ZIEL / repo.replace("/", "__") / p
                ziel.parent.mkdir(parents=True, exist_ok=True)
                ziel.write_text(inhalt.stdout, encoding="utf-8")
                treffer.append(p)
        lizenz = [p for p in git("ls-tree", "--name-only", "HEAD", cwd=tmp).stdout.splitlines()
                  if re.match(r"(?i)(licen[cs]e|copying)", p)]
        return repo, {"commit": commit, "ergogen": treffer, "lizenzdateien": lizenz}


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"repositories": {}}
    alle = repos_aus_db()
    alt = manifest["repositories"]
    if "--neu" in sys.argv:
        offen = alle
    elif "--ohne-treffer" in sys.argv:
        offen = [r for r in alle if r not in alt or not alt[r].get("ergogen")]
    else:
        offen = [r for r in alle if r not in alt]
    print(f"{len(alle)} Repositories, {len(offen)} zu prüfen")
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i, (repo, erg) in enumerate(pool.map(pruefe, offen), 1):
            manifest["repositories"][repo] = erg
            if erg.get("ergogen"):
                print(f"  {repo}: {len(erg['ergogen'])} Ergogen-Datei(en)")
            if i % 25 == 0:
                MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                    encoding="utf-8")
    manifest["beschreibung"] = ("Ergogen-Konfigurationen in Repositories aus der Tastatur-Datenbank, mit Commit. "
                                "Erzeugt von tastaturen/skripte/ergogen_suchen.py.")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    mit = sum(1 for e in manifest["repositories"].values() if e.get("ergogen"))
    print(f"fertig: {mit} Repositories mit Ergogen-Dateien")


if __name__ == "__main__":
    main()
