"""Initialize desktop data and resolve personal models against the bundled Core package."""

import hashlib
import os
import re
import sys
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID, uuid4

import yaml
from dotenv.parser import parse_stream
from resolver.assembler import resolve_personal_model_configuration
from resolver.configuration_schema import validate_instance_model_settings
from resolver.contract_validation import load_package_manifest
from resolver.contracts import PACKAGE_MANIFEST_NAME
from resolver.errors import ConfigResolverError
from resolver.product_validation import ResolvedPackageReader
from resolver.schema_validation import personal_instance_origin
from resolver.resource_schemas import (
    BROKER_ROUTING_VARIABLES,
    valid_broker_routing_prompt,
    validate_prompt_registry,
)
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError


class ConfigError(ValueError):
    """Expose only a stable diagnostic from the personal configuration."""


def data_directory():
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        base = Path(os.environ["LOCALAPPDATA"])
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "LODEON-Customizer" / "data"


def resource_paths():
    if getattr(sys, "frozen", False):
        assets = Path(__file__).resolve().parent.parent / "resources"
        return assets / "core" / "config.yml", assets / "package"
    package = Path(os.environ["LODEON_CUSTOMIZER_ROOT"])
    return Path(os.environ["LODEON_CORE_ROOT"]) / "config" / "config.yml", package


def _create_if_absent(path, content):
    if path.exists():
        return
    with NamedTemporaryFile(dir=path.parent, delete=False) as pending:
        pending.write(content)
    try:
        # Publish complete bytes exclusively. Close the temporary file first on Windows.
        os.link(pending.name, path)
    except FileExistsError:
        pass
    finally:
        Path(pending.name).unlink()


PRIVATE_SETTINGS = Path(".data/customizer.yml")
IGNORE_RULES = (".env", ".data/", ".runtime/", "__pycache__/", ".pytest_cache/", ".ruff_cache/", ".DS_Store")


def ensure_gitignore(path):
    original = path.read_bytes() if path.exists() else b""
    rules = [rule.encode() for rule in IGNORE_RULES]
    # Put required exclusions after existing negations, retaining all owner rules.
    lines = original.splitlines()
    last_negation = max((i for i, line in enumerate(lines) if line.startswith(b"!")), default=-1)
    missing = [rule for rule in rules if rule not in lines[last_negation + 1:]]
    if missing:
        with path.open("ab") as stream:
            if original and not original.endswith(b"\n"):
                stream.write(b"\n")
            stream.write(b"\n".join(missing) + b"\n")


def read_manifest(path):
    try:
        return load_package_manifest(path)
    except ConfigResolverError:
        raise ConfigError("invalid_manifest") from None


def read_private_settings(path):
    try:
        doc = yaml.safe_load(path.read_bytes())
        if not isinstance(doc, dict) or doc.keys() - {"serviceId", "instance", "instanceModelSettings"}:
            raise ConfigError("invalid_private_settings")
        UUID(doc["serviceId"])
        if "instance" in doc:
            instance_origin(doc["instance"])
        for address, overrides in doc.get("instanceModelSettings", {}).items():
            instance_origin(address)
            validate_instance_model_settings(overrides)
        return doc
    except (KeyError, ValueError, TypeError, AttributeError, ConfigResolverError, yaml.YAMLError):
        raise ConfigError("invalid_private_settings") from None


def initialize(data: Path) -> UUID:
    data.mkdir(mode=0o700, parents=True, exist_ok=True)
    _, template = resource_paths()
    manifest = data / PACKAGE_MANIFEST_NAME
    config = data / "config.yml"
    private = data / PRIVATE_SETTINGS
    if manifest.exists():
        read_manifest(manifest)
    if config.exists():
        # Check an existing folder before adding any package or private files.
        load_configuration(config, package=data if manifest.exists() else template)
    if private.exists():
        read_private_settings(private)
    slug = re.sub(r"[^a-z0-9_-]+", "-", data.name.lower()).strip("-") or "package"
    ensure_gitignore(data / ".gitignore")
    _create_if_absent(manifest, yaml.safe_dump({"schemaVersion": 1, "id": f"local/{slug}", "version": "0.1.0"}, sort_keys=False).encode())
    _create_if_absent(config, (template / "config.yml").read_bytes())
    private.parent.mkdir(mode=0o700, exist_ok=True)
    _create_if_absent(private, f"serviceId: {uuid4()}\n".encode())
    return UUID(read_private_settings(private)["serviceId"])


def load_configuration(config: Path, *, package=None) -> dict:
    core_config, _ = resource_paths()
    try:
        return resolve_personal_model_configuration(
            core_config=core_config, package_root=package or config.parent, personal_config=config,
        )
    except ConfigResolverError:
        raise ConfigError("invalid_config") from None


def load_routing_prompts(data: Path, registry_file: str, brokers: dict) -> dict[str, str]:
    """Snapshot only the Markdown explicitly referenced by personal routed brokers."""
    ids = {
        broker["router"]["prompt"] for broker in brokers.values()
        if any(task["strategy"] == "routed" for task in broker["tasks"].values())
    }
    if not ids:
        return {}
    reader = ResolvedPackageReader(data)
    try:
        registry_path = reader.path(registry_file)
        if not registry_path.is_file() or registry_path.suffix.lower() not in {".yaml", ".yml"}:
            return {}
        registry = reader.load_yaml(registry_file)
        # Only prompt definitions execute here. Package chains can refer to hosted entries.
        validate_prompt_registry({**registry, "chains": {}})
    except (ConfigResolverError, OSError, ValueError, RecursionError):
        return {}

    prompts = {}
    for prompt_id in ids:
        entry = registry["prompts"].get(prompt_id)
        if not entry or not BROKER_ROUTING_VARIABLES.issubset(entry["variables"]):
            continue
        try:
            path = reader.path(Path(registry_file).parent / entry["file"])
            if not path.is_file() or path.suffix.lower() != ".md":
                continue
            content = path.read_text(encoding="utf-8").strip()
        except (ConfigResolverError, OSError, ValueError):
            continue
        if valid_broker_routing_prompt(content):
            prompts[prompt_id] = content
    return prompts


def instance_origin(address):
    try:
        return personal_instance_origin(address)
    except ConfigResolverError:
        raise ConfigError("invalid_instance") from None


def save_instance(path, address, revision, check):
    """Preserve edited YAML and publish a validated replacement on the same filesystem."""
    instance_origin(address)
    return update_settings(path, revision, check, lambda settings: settings.update(instance=address))


def config_revision(path, raw):
    return hashlib.sha256(os.fsencode(path.resolve()) + b"\0" + raw).hexdigest()


def update_settings(path, revision, check, edit):
    original = path.read_bytes()
    if config_revision(path, original) != revision:
        raise ConfigError("config_changed")
    yaml = YAML()
    yaml.preserve_quotes = True
    try:
        settings = yaml.load(original.decode("utf-8"))
    except YAMLError:
        raise ConfigError("invalid_config") from None
    if not isinstance(settings, dict):
        raise ConfigError("invalid_config")
    edit(settings)
    output = StringIO()
    yaml.dump(settings, output)
    with NamedTemporaryFile(dir=path.parent, delete=False) as pending:
        pending.write(output.getvalue().encode("utf-8"))
    candidate = Path(pending.name)
    try:
        models = check(candidate)
        if path.read_bytes() != original:
            raise ConfigError("config_changed")
        os.replace(candidate, path)
        return models
    finally:
        candidate.unlink(missing_ok=True)


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
