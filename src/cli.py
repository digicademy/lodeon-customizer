"""Start the local Customizer or inspect its configured model catalog."""

import argparse
import json
import sys
from pathlib import Path
from uuid import UUID

from .configuration import initialize
from .http_service import ModelService
from .profiles import ConfigError, LocalModels


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
            models = LocalModels.load(args.data / "config.yml", identity)
            with ModelService(("0.0.0.0", 8765), models) as server:
                server.serve_forever()
        else:
            identity = args.service_id or UUID(
                (args.config.parent / ".service-id").read_text().strip()
            )
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
