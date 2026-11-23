"""Inspect the validated public catalog from the local command line."""

import argparse
import json
import sys
from pathlib import Path
from uuid import UUID

from .profiles import ConfigError, LocalModels


def main() -> int:
    parser = argparse.ArgumentParser(prog="lodeon-customizer")
    catalog = parser.add_subparsers(dest="command", required=True).add_parser("catalog")
    catalog.add_argument("--config", type=Path, required=True)
    catalog.add_argument("--service-id", type=UUID, required=True)
    args = parser.parse_args()
    try:
        models = LocalModels.load(args.config, args.service_id)
        print(json.dumps(models.catalog(models.profile_ids), ensure_ascii=False, indent=2))
    except ConfigError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
