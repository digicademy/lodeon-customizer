"""Initialize the user's files and resolve the personal Package with LODEON Core."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID, uuid4

from dotenv.parser import parse_stream
from resolver.assembler import resolve_personal_model_configuration


CORE = Path("/opt/lodeon")
PACKAGE = Path("/opt/customizer")


class ConfigError(ValueError):
    """Expose only a stable diagnostic from the personal configuration."""


def _create_if_absent(path: Path, content: bytes) -> None:
    if path.exists():
        return
    with NamedTemporaryFile(dir=path.parent) as pending:
        pending.write(content)
        pending.flush()
        try:
            os.link(pending.name, path)
        except FileExistsError:
            pass


def initialize(data: Path) -> UUID:
    data.mkdir(mode=0o700, parents=True, exist_ok=True)
    (data / "models").mkdir(mode=0o700, exist_ok=True)
    _create_if_absent(data / "config.yml", (PACKAGE / "config.yml").read_bytes())
    identity = data / ".service-id"
    _create_if_absent(identity, (str(uuid4()) + "\n").encode())
    try:
        return UUID(identity.read_text().strip())
    except ValueError:
        raise ConfigError("invalid_service_identity") from None


def load_assistant(config: Path) -> dict:
    product = resolve_personal_model_configuration(
        core_config=CORE / "config/config.yml", package_root=PACKAGE, personal_config=config,
    )
    return product["assistant"]


def read_model_environment(path: Path) -> dict[str, str]:
    values = {}
    try:
        with path.open(encoding="utf-8") as stream:
            for binding in parse_stream(stream):
                if binding.error:
                    raise ConfigError("invalid_model_environment")
                if binding.key is not None and binding.value is not None:
                    values[binding.key] = binding.value
    except FileNotFoundError:
        pass
    except (OSError, UnicodeError):
        raise ConfigError("invalid_model_environment") from None
    return values
