# Testauftritt unter wunschzettel.familie-gasch.net/keyboard-test/

Stand: 17.11.2026. Die Domain zeigt auf den DecaSwift-Hub. Dort liefert der Container `wunschzettel` (nginx 1.27-alpine, hinter Traefik) die statische Seite aus `/srv/wunschzettel/site` aus. Container und Dateien verwaltet die Ansible-Rolle `wunschzettel` im Repository `soeren-gasch/infrastructure`. Die Dateien gehören root.

Damit der Benutzer `decaswift` den Entwurf ohne root und ohne Umweg über die docker-Gruppe ausspielen kann, braucht die Rolle eine kleine Erweiterung: ein eigenes Verzeichnis, das `decaswift` gehört, schreibgeschützt in den Container eingebunden.

## Änderungen an der Rolle `wunschzettel`

### 1. Verzeichnis anlegen (Task)

```yaml
- name: Verzeichnis für den Testauftritt der Tastatur-Datenbank
  ansible.builtin.file:
    path: /srv/keyboard-test/site
    state: directory
    owner: decaswift
    group: decaswift
    mode: "0755"
```

Das Elternverzeichnis `/srv/keyboard-test` genauso mit `owner: root`, `mode: "0755"`.

### 2. `docker-compose.yml`: zusätzliches Volume

```yaml
    volumes:
      - ./site:/usr/share/nginx/html:ro
      - ./nginx-default.conf:/etc/nginx/conf.d/default.conf:ro
      - /srv/keyboard-test/site:/usr/share/nginx/keyboard-test:ro
```

Das Volume liegt bewusst außerhalb von `html/`. Ein verschachtelter Bind-Mount würde sonst ein leeres Verzeichnis in `/srv/wunschzettel/site` anlegen.

### 3. `nginx-default.conf`: zusätzliche Locations im bestehenden `server`

```nginx
    absolute_redirect off;

    location = /keyboard-test {
        return 301 /keyboard-test/;
    }

    # Entwurf der Tastatur-Datenbank (tastaturen/ im Repo keyboard-layout); vorkomprimierte .gz-Dateien
    location /keyboard-test/ {
        alias /usr/share/nginx/keyboard-test/;
        index index.html;
        gzip_static on;
        add_header Cache-Control "no-cache" always;
        add_header X-Robots-Tag "noindex, nofollow" always;

        # Index-Dateien tragen einen Hash im Namen und ändern sich nie
        location ~ ^/keyboard-test/idx\.[0-9a-f]+\.json$ {
            add_header Cache-Control "public, max-age=31536000, immutable" always;
            add_header X-Robots-Tag "noindex, nofollow" always;
        }
    }
```

Hinweise:
- `add_header` in einer Location ersetzt die Header der Server-Ebene. Deshalb steht `Cache-Control` dort noch einmal.
- `gzip_static` ist im offiziellen nginx-Image enthalten.
- `absolute_redirect off` sorgt dafür, dass Umleitungen hinter Traefik nicht auf `http://…:80` zeigen.

## Ausspielen (ohne root)

```sh
python3 tastaturen/skripte/seite_ausspielen.py      # baut mit --noindex und kopiert nach /srv/keyboard-test/site
```

Das Skript kopiert nur geänderte Dateien, jede atomar: zuerst die neuen Index-Dateien, dann `index.html`, zuletzt löscht es veraltete Dateien. Insgesamt sind es rund 17.600 Dateien mit 85 MB, davon die Hälfte die `.gz`-Fassungen.

## Schutz des Testauftritts

- `noindex, nofollow` als Meta-Tag auf jeder Seite und als HTTP-Header.
- Die Fußzeile kennzeichnet die Seite als Entwurf.
- Die Daten von golem.hu und KBD.news sind öffentlich abrufbar, solange deren Zustimmung fehlt (siehe `../lizenzen.md`). Ist das nicht gewollt, hilft eine Basic-Auth vor `/keyboard-test/` oder ein Bau ohne diese Quellen.
