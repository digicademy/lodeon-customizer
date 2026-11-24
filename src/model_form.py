"""Local model form fields and edits to the canonical Core profile structure."""

import hashlib
import math
import os
import re
from html import escape
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit

import yaml
from dotenv import set_key
from lodeon_model_runtime.profiles import (
    ModelProfileContractError, PROVIDER_CAPABILITIES, validate_model_profile_contract,
)

from .configuration import ConfigError, config_revision, read_model_environment, update_settings


class FormError(ValueError):
    """A user-facing local error that contains no submitted value."""


PROVIDERS = {"ollama": "Ollama", "openai": "OpenAI", "anthropic": "Anthropic",
             "openai-compatible": "OpenAI-compatible"}
ENDPOINTS = {"ollama": "http://127.0.0.1:11434", "openai": "https://api.openai.com/v1",
             "anthropic": "https://api.anthropic.com"}
LIMITS = {"maxOutputTokens": "Output tokens", "maxInputCharacters": "Input characters",
          "modelRequestTimeoutSeconds": "Request timeout (seconds)", "maxToolCallsPerTurn": "Tool calls per turn",
          "maxUserMessageCharacters": "User message characters", "maxChatRequestsPerMinute": "Chat requests per minute"}
RATES = {"inputPerMillionTokens": "Input", "outputPerMillionTokens": "Output",
         "cachedInputPerMillionTokens": "Cached input", "cacheWritePerMillionTokens": "Cache writes"}
FIELDS = {"original", "revision", "id", "label", "description", "provider", "model", "endpoint", "endpointSource",
          "credential", "keyVariable", "default", "temperature", "topP", "reasoningEffort", "cache",
          "keepAlive", "currency", *LIMITS, *RATES}


def values_for(key, profile, default):
    fields = {name: profile.get(name, "") for name in ("label", "description", "model")}
    credential = "none" if key else "auto"
    if "apiKey" in profile:
        credential = "inline"
    elif "apiKeyEnv" in profile:
        credential = "personal"
    fields.update(id=key, original=key, provider=profile.get("provider", "ollama"),
                  endpointSource="baseURLEnv" if "baseURLEnv" in profile else "baseURL",
                  endpoint=profile.get("baseURLEnv", profile.get("baseURL", "")),
                  credential=credential,
                  keyVariable=profile.get("apiKeyEnv", ""), default="on" if key and key == default else "",
                  keepAlive=profile.get("ollama", {}).get("keepAlive", ""))
    caching = profile.get("promptCaching", {})
    fields["cache"] = caching.get("retention", "default") if caching.get("enabled") else "off"
    for group in ("generation", "limits", "cost"):
        fields.update(profile.get(group, {}))
    return fields


def _number(raw, label, convert):
    if not raw:
        return None
    try:
        value = convert(raw)
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError()
        return value
    except ValueError:
        raise FormError(f"Enter a valid number for {label}.") from None


def _set(mapping, field, value):
    if value is None or value == "":
        mapping.pop(field, None)
    elif mapping.get(field) != value:
        mapping[field] = value


def _group(profile, name, changes):
    values = profile.setdefault(name, {})
    for key, value in changes.items():
        _set(values, key, value)
    if not values:
        profile.pop(name)


def save_model(path, fields, check):
    original = fields["original"]
    key = fields["id"].strip()
    if not key:
        key = re.sub(r"[^a-z0-9]+", "-", fields["label"].lower()).strip("-")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", key):
        raise FormError("Choose a profile ID starting with a letter, using letters, digits, hyphens or underscores.")
    if original and original != key:
        raise FormError("The ID of an existing profile is fixed.")

    def edit(settings):
        assistant = settings.setdefault("assistant", {})
        profiles = assistant.setdefault("modelProfiles", {})
        if original and original not in profiles:
            raise ConfigError("config_changed")
        if not original and (key in profiles or key in assistant.get("modelBrokers", {})):
            raise FormError("That profile ID is already in use. Choose another ID.")
        profile = profiles.setdefault(key, {})
        for name in ("label", "provider", "model"):
            if not fields[name].strip():
                raise FormError(f"Enter the model’s {name}.")
            profile[name] = fields[name].strip()
        provider = profile["provider"]
        if provider not in PROVIDER_CAPABILITIES:
            raise FormError("Choose a supported provider.")
        _set(profile, "description", fields["description"].strip())
        source = fields["endpointSource"]
        if source not in {"baseURL", "baseURLEnv"}:
            raise FormError("Select an endpoint source.")
        endpoint = fields["endpoint"].strip()
        if source == "baseURL":
            endpoint = endpoint or ENDPOINTS.get(provider, "")
            try:
                parsed = urlsplit(endpoint)
                if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None or parsed.fragment:
                    raise ValueError()
                _ = parsed.port
            except ValueError:
                raise FormError("Enter an absolute HTTP or HTTPS endpoint without credentials or a fragment.") from None
        elif not re.fullmatch(r"[A-Z_][A-Z0-9_]*", endpoint):
            raise FormError("Enter a valid uppercase endpoint variable name.")
        profile.pop("baseURL" if source == "baseURLEnv" else "baseURLEnv", None)
        profile[source] = endpoint

        mode = fields["credential"]
        if mode == "auto":
            mode = "personal" if provider in {"openai", "anthropic"} else "none"
        if mode == "personal":
            variable = fields["keyVariable"].strip() or profile.get("apiKeyEnv")
            if not variable:
                stem = "LODEON_" + key.upper().replace("-", "_") + "_API_KEY"
                reserved = set(read_model_environment(path.parent / "models" / ".env"))
                for other in profiles.values():
                    reserved.update((other.get("baseURLEnv"), other.get("apiKeyEnv")))
                variable = stem
                suffix = 2
                while variable in reserved:
                    variable = f"{stem}_{suffix}"
                    suffix += 1
            if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", variable):
                raise FormError("Enter a valid uppercase provider key variable name.")
            profile.pop("apiKey", None)
            profile["apiKeyEnv"] = variable
        elif mode == "none":
            if provider in {"openai", "anthropic"}:
                raise FormError("Choose a personal API key for this provider.")
            profile.pop("apiKeyEnv", None)
            profile.pop("apiKey", None)
        elif mode != "inline" or "apiKey" not in profile:
            raise FormError("Select a valid provider key option.")

        _group(profile, "generation", {"temperature": _number(fields["temperature"], "temperature", float),
                                      "topP": _number(fields["topP"], "top P", float),
                                      "reasoningEffort": fields["reasoningEffort"]})
        _group(profile, "limits", {k: _number(fields[k], label, int) for k, label in LIMITS.items()})
        _group(profile, "cost", {"currency": fields["currency"].strip().upper(),
                                 **{k: _number(fields[k], label, float) for k, label in RATES.items()}})
        _group(profile, "ollama", {"keepAlive": fields["keepAlive"].strip()})
        _group(profile, "promptCaching", {"enabled": fields["cache"] != "off",
                                         "retention": "default" if fields["cache"] == "off" else fields["cache"]})
        try:
            validate_model_profile_contract(key, profile)
        except ModelProfileContractError as error:
            field = str(error.variables.get("field", "")).removeprefix(f"assistant.modelProfiles.{key}.")
            raise FormError(f"Check {field} for the selected provider.") from None
        if fields.get("default") == "on":
            assistant["defaultModel"] = key
        elif assistant.get("defaultModel") == key:
            assistant.pop("defaultModel")

    return key, update_settings(path, fields["revision"], check, edit)


def key_revision(path):
    try:
        info = path.stat()
        stamp = f"{info.st_ino}-{info.st_mtime_ns}-{info.st_size}"
        return hashlib.sha256(stamp.encode()).hexdigest()
    except FileNotFoundError:
        return "absent"


def save_key(config, fields):
    raw = config.read_bytes()
    if config_revision(config, raw) != fields["revision"]:
        raise ConfigError("config_changed")
    profile = yaml.safe_load(raw)["assistant"]["modelProfiles"].get(fields["profile"], {})
    variable = profile.get("apiKeyEnv")
    if not isinstance(variable, str) or not re.fullmatch(r"[A-Z_][A-Z0-9_]*", variable):
        raise FormError("Save a personal key reference for this model first.")
    value = fields["secret"]
    if not value.strip() or any(c in value for c in "\r\n\0"):
        raise FormError("Enter a non-empty, single-line API key.")
    path = config.parent / "models" / ".env"
    revision = fields["keyRevision"]
    if key_revision(path) != revision:
        raise ConfigError("config_changed")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as pending:
        if path.exists():
            pending.write(path.read_bytes())
    candidate = Path(pending.name)
    try:
        read_model_environment(candidate)
        set_key(candidate, variable, value)
        if key_revision(path) != revision or config.read_bytes() != raw:
            raise ConfigError("config_changed")
        os.replace(candidate, path)
    finally:
        candidate.unlink(missing_ok=True)


def render_fields(values):
    """Render the same editable values for a fresh profile, a saved profile or a rejected edit."""
    def field(name, label, *, options=None, kind="text", attrs=""):
        current = str(values.get(name, ""))
        if options is not None:
            choices = "".join(f'<option value="{escape(v, quote=True)}"{" selected" if current == v else ""}>{escape(t)}</option>'
                              for v, t in options.items())
            control = f'<select name="{name}">{choices}</select>'
        elif name == "description":
            control = f'<textarea name="{name}" rows="2">{escape(current)}</textarea>'
        else:
            control = f'<input type="{kind}" name="{name}" value="{escape(current, quote=True)}" {attrs}>'
        return f'<label>{escape(label)}{control}</label>'

    def choices(items):
        return {x: x for x in items}

    credentials = {"auto": "Use provider default", "personal": "Use a personal API key", "none": "No API key"}
    if values.get("credential") == "inline":
        credentials["inline"] = "Keep the configured key"
    return {
        "basic": field("label", "Display name", attrs='required placeholder="My Ollama"') +
                 field("provider", "Provider", options=PROVIDERS) +
                 field("model", "Provider model name", attrs='required placeholder="gemma4:12b"') +
                 field("endpoint", "Endpoint URL or variable", attrs='placeholder="Provider default"') +
                 field("credential", "Provider authentication", options=credentials) +
                 field("description", "Description"),
        "default_checked": "checked" if values.get("default") == "on" else "",
        "generation": field("temperature", "Temperature", kind="number", attrs='min="0" max="2" step="any"') +
                      field("topP", "Top P", kind="number", attrs='min="0.000001" max="1" step="any"') +
                      field("reasoningEffort", "Reasoning effort", options={"": "Provider default", **choices(("none","minimal","low","medium","high","xhigh","max"))}) +
                      field("cache", "Prompt cache retention", options={"off": "Caching disabled", **choices(("default","5m","1h","24h"))}) +
                      field("keepAlive", "Ollama keep-alive", attrs='placeholder="e.g. 5m"'),
        "limits": "".join(field(k, label, kind="number", attrs='min="1" step="1"') for k, label in LIMITS.items()),
        "pricing": field("currency", "Currency", attrs='maxlength="3" placeholder="USD"') +
                   "".join(field(k, label, kind="number", attrs='min="0" step="any"') for k, label in RATES.items()),
        "identifiers": field("id", "Profile ID", attrs="readonly" if values.get("original") else 'placeholder="Generated from display name"') +
                       field("endpointSource", "Endpoint source", options={"baseURL": "URL", "baseURLEnv": "Environment variable"}) +
                       field("keyVariable", "API key variable", attrs='placeholder="Assigned automatically"'),
    }
