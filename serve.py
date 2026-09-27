#!/usr/bin/env python3
"""
Preview the whole site locally, the way GitHub Pages serves it:

    python serve.py            -> http://localhost:8000

  /                         this repo (landing page, /lyriq/ ...)
  /<repo-name>/...          a sibling project repo next to this folder (e.g. ../ecocar-vehicle-tracker)

Nothing is cached, so a browser refresh always shows your latest edits.
"""

import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
PORT = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 8000))


class PagesHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        parts = path.split("?", 1)[0].split("#", 1)[0].lstrip("/").split("/", 1)
        first = parts[0]
        sibling = PARENT / first
        # /<project>/... -> ../<project>/... when that folder is a sibling repo (and not a folder in this repo)
        if first and not (HERE / first).exists() and (sibling / ".git").exists():
            rest = "/" + (parts[1] if len(parts) > 1 else "")
            return str(Path(SimpleHTTPRequestHandler.translate_path(self, rest).replace(str(HERE), str(sibling), 1)))
        return SimpleHTTPRequestHandler.translate_path(self, path)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        if not str(args[1] if len(args) > 1 else "").startswith(("2", "3")):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), partial(PagesHandler, directory=str(HERE)))
    print(f"Serving the site at http://localhost:{PORT}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
