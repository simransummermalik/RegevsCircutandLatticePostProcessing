#!/usr/bin/env python3
"""Serve the hand-controlled circuit demo from the repository root.

The server uses only Python's standard library.  Serving the repository root
keeps the demo's relative "View implementation" links functional while the
browser opens directly on the isolated demo directory.
"""

from __future__ import annotations

import argparse
import functools
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


DEMO_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_ROOT = DEMO_DIRECTORY.parent
DEMO_PATH = f"/{DEMO_DIRECTORY.name}/"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


class DemoRequestHandler(SimpleHTTPRequestHandler):
    """Static handler with presentation-friendly caching and safety headers."""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve the Regev hand-circuit presentation demo locally."
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"interface to bind (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        default=DEFAULT_PORT,
        type=int,
        help=f"port to bind (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        dest="open_browser",
        help="open the demo in the default browser after the server starts",
    )
    return parser.parse_args()


def demo_url(host: str, port: int) -> str:
    """Return a browser URL; wildcard binds still open through localhost."""

    browser_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    return f"http://{browser_host}:{port}{DEMO_PATH}"


def main() -> int:
    args = parse_args()
    handler = functools.partial(DemoRequestHandler, directory=str(REPOSITORY_ROOT))

    try:
        server = ThreadingHTTPServer((args.host, args.port), handler)
    except OSError as error:
        raise SystemExit(
            f"Could not start the demo on {args.host}:{args.port}: {error}\n"
            "Try another port, for example: --port 8080"
        ) from error

    url = demo_url(args.host, server.server_port)
    print("Regev hand-circuit demo is ready:")
    print(f"  {url}")
    print("Press Ctrl+C to stop. Camera frames remain in the browser tab.")

    if args.open_browser:
        threading.Timer(0.25, webbrowser.open, args=(url,)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping demo server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

