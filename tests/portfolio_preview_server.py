"""Loopback-only portfolio preview with isolated JSON response modes.

The mode file contains one word: ready, error, invalid, empty, or slow.
No website file is changed, and private directories are never served.
"""

from __future__ import annotations

import argparse
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import time
from urllib.parse import unquote, urlsplit


PRIVATE_PARTS = frozenset({"_개발준비", ".git", "tests"})
MODES = frozenset({"ready", "error", "invalid", "empty", "slow"})


class PortfolioPreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str, mode_file: Path, **kwargs):
        self.web_root = Path(directory).resolve()
        self.mode_file = mode_file.resolve()
        self.projects_file = (self.web_root / "assets" / "projects.json").resolve()
        super().__init__(*args, directory=str(self.web_root), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def _safe_path(self) -> Path | None:
        try:
            raw_path = unquote(urlsplit(self.path).path).replace("\\", "/")
            parts = [part for part in raw_path.split("/") if part not in ("", ".")]
            if any(
                part == ".." or part != part.rstrip(" .") or ":" in part or "\x00" in part
                or part.casefold() in PRIVATE_PARTS
                for part in parts
            ):
                return None
            target = self.web_root.joinpath(*parts).resolve()
            relative = target.relative_to(self.web_root)
            if any(part.casefold() in PRIVATE_PARTS for part in relative.parts):
                return None
            if target == self.mode_file:
                return None
            return target
        except (OSError, RuntimeError, ValueError):
            return None

    def _response(self, status: int, body: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        return None

    def send_head(self):
        target = self._safe_path()
        if target is None:
            self.send_error(404, "Not found")
            return None

        if target == self.projects_file:
            try:
                mode = self.mode_file.read_text(encoding="utf-8-sig").strip().lower()
            except (OSError, UnicodeError):
                mode = "unavailable"
            if mode not in MODES:
                return self._response(503, b"Preview mode unavailable.\n", "text/plain; charset=utf-8")
            if mode == "error":
                return self._response(503, b"Preview: projects unavailable.\n", "text/plain; charset=utf-8")
            if mode == "invalid":
                return self._response(200, b'{"projects": ', "application/json; charset=utf-8")
            if mode == "empty":
                body = json.dumps({"schemaVersion": 1, "replaceExisting": True, "projects": []}).encode("utf-8")
                return self._response(200, body, "application/json; charset=utf-8")
            if mode == "slow":
                time.sleep(2)

        try:
            if target.is_dir():
                # Serve a homepage, but never expose a directory listing.
                target = next(
                    (candidate for name in ("index.html", "index.htm")
                     if (candidate := target / name).is_file()),
                    None,
                )
                if target is None:
                    self.send_error(404, "Not found")
                    return None
                target = target.resolve()
                relative = target.relative_to(self.web_root)
                if target == self.mode_file or any(part.casefold() in PRIVATE_PARTS for part in relative.parts):
                    self.send_error(404, "Not found")
                    return None
            if not target.is_file():
                self.send_error(404, "Not found")
                return None
            stream = target.open("rb")
        except (OSError, RuntimeError, ValueError):
            self.send_error(404, "Not found")
            return None

        try:
            stat = os.fstat(stream.fileno())
            self.send_response(200)
            self.send_header("Content-Type", self.guess_type(str(target)))
            self.send_header("Content-Length", str(stat.st_size))
            self.send_header("Last-Modified", self.date_time_string(stat.st_mtime))
            self.end_headers()
            return stream
        except BaseException:
            stream.close()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path, help="Actual website root")
    parser.add_argument("--port", type=int, default=8876)
    parser.add_argument("--mode-file", required=True, type=Path, help="Absolute path to the mode text file")
    args = parser.parse_args()
    web_root = args.directory.expanduser().resolve()
    mode_file = args.mode_file.expanduser()
    if not web_root.is_dir():
        parser.error("--directory must be an existing directory")
    if not mode_file.is_absolute():
        parser.error("--mode-file must be an absolute path")
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")

    def handler(*handler_args, **handler_kwargs):
        return PortfolioPreviewHandler(
            *handler_args, directory=str(web_root), mode_file=mode_file, **handler_kwargs
        )

    with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        server.daemon_threads = True
        print(f"Portfolio preview: http://127.0.0.1:{server.server_port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
