"""Lokale Vorschau von tastaturen/web/dist/ mit vorkomprimierten .gz-Dateien (wie später auf dem Server).

Aufruf: python3 tastaturen/web/vorschau.py [Port]   (Standard 8765, nur localhost)
"""

import http.server
import mimetypes
import sys
from pathlib import Path

DIST = Path(__file__).resolve().parent / "dist"


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        pfad = self.path.split("?", 1)[0].split("#", 1)[0]
        if pfad.endswith("/"):
            pfad += "index.html"
        datei = (DIST / pfad.lstrip("/")).resolve()
        if DIST not in datei.parents or not datei.is_file():
            self.send_error(404)
            return
        typ = mimetypes.guess_type(datei.name)[0] or "application/octet-stream"
        if typ.startswith("text/") or typ.endswith(("json", "javascript")):
            typ += "; charset=utf-8"
        gz = datei.with_name(datei.name + ".gz")
        daten = datei.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", typ)
        if "gzip" in self.headers.get("Accept-Encoding", "") and gz.is_file():
            daten = gz.read_bytes()
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        # Index-Dateien tragen einen Hash im Namen und ändern sich nie
        self.send_header("Cache-Control", "public, max-age=31536000, immutable" if datei.name.startswith("idx.")
                         else "no-cache")
        self.send_header("Content-Length", str(len(daten)))
        self.end_headers()
        self.wfile.write(daten)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"http://localhost:{port}/")
    http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
