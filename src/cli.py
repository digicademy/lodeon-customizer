"""Start the local Customizer or inspect its configured model catalog."""

import argparse
import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from uuid import UUID

from .configuration import initialize
from .profiles import ConfigError, LocalModels


class _LandingPage(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get("Host") not in {"127.0.0.1:8765", "localhost:8765"}:
            self.send_error(403)
            return
        if self.path != "/":
            self.send_error(404)
            return
        body = (
            "<!doctype html><html lang=en><meta charset=utf-8>"
            "<title>LODEON Customizer</title><h1>LODEON Customizer</h1>"
            "<p>The local service is running.</p>"
            "<p>Edit your models and brokers in <code>data/config.yml</code>. "
            "Store model keys in <code>data/models/.env</code>.</p></html>"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Do not log arbitrary request paths into Docker logs.
        pass


def main() -> int:
    parser = argparse.ArgumentParser(prog="lodeon-customizer")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve")
    serve.add_argument("--data", type=Path, default=Path("/data"))
    catalog = commands.add_parser("catalog")
    catalog.add_argument("--config", type=Path, default=Path("/data/config.yml"))
    catalog.add_argument("--service-id", type=UUID)
    args = parser.parse_args()
    try:
        if args.command == "serve":
            identity = initialize(args.data)
            LocalModels.load(args.data / "config.yml", identity)
            with HTTPServer(("0.0.0.0", 8765), _LandingPage) as server:
                server.serve_forever()
        else:
            identity = args.service_id or UUID((args.config.parent / ".service-id").read_text().strip())
            models = LocalModels.load(args.config, identity)
            print(json.dumps(models.catalog(models.profile_ids), ensure_ascii=False, indent=2))
    except ConfigError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, ValueError):
        print("customizer_start_or_catalog_failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
