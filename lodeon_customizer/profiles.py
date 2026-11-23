"""Load the user's private profiles and project only explicitly approved public offers."""

import json
import os
import re
from collections.abc import Collection, Mapping
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import yaml
from lodeon_model_runtime.profiles import validate_model_profile_contract
from lodeon_model_runtime.wire import validate_payload


class ConfigError(ValueError):
    """Report configuration failure without disclosing a local path, value or environment name."""


class _UniqueKeysLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        mapping = super().construct_mapping(node, deep=deep)
        if len(mapping) != len(node.value):
            raise ConfigError("duplicate_config_key")
        return mapping


def _resolve(profile_id, configured, environment):
    validate_model_profile_contract(profile_id, configured)
    profile = deepcopy(configured)
    access = profile.pop("access", {})
    if access not in ({}, {"allowedGroups": []}):
        raise ConfigError("instance_access_policy_unsupported")
    for field in ("baseURL", "apiKey"):
        env_name = profile.pop(field + "Env", None)
        if env_name is not None:
            if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", env_name):
                raise ConfigError("invalid_environment_reference")
            value = environment.get(env_name)
            if not value or not value.strip():
                raise ConfigError("missing_local_setting")
            profile[field] = value

    endpoint = urlsplit(profile["baseURL"])
    if (
        endpoint.scheme not in {"https", "http"}
        or not endpoint.hostname
        or endpoint.username is not None
        or endpoint.fragment
    ):
        raise ConfigError("invalid_model_endpoint")
    if profile["provider"] in {"anthropic", "openai"} and not profile.get("apiKey"):
        raise ConfigError("missing_local_setting")
    return profile


class LocalModels:
    """Own a private snapshot for the lifetime of one configuration revision."""

    def __init__(self, service_id: UUID, profiles):
        self._service_id = str(service_id)
        self.revision = uuid4().hex
        self._profiles = profiles

    @classmethod
    def load(cls, path: Path, service_id: UUID, environment: Mapping[str, str] | None = None):
        try:
            document = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeysLoader)
            if not isinstance(document, dict) or set(document) != {"assistant"}:
                raise ConfigError("invalid_config")
            assistant = document["assistant"]
            if not isinstance(assistant, dict) or set(assistant) != {"modelProfiles"}:
                raise ConfigError("invalid_config")
            configured = assistant["modelProfiles"]
            if not isinstance(configured, dict):
                raise ConfigError("invalid_config")
            # Reject non-JSON YAML values before they can reach offers or provider options.
            json.dumps(configured, allow_nan=False)
            env = os.environ if environment is None else environment
            snapshot = cls(
                service_id,
                {
                    profile_id: _resolve(profile_id, profile, env)
                    for profile_id, profile in configured.items()
                },
            )
            snapshot.catalog(snapshot.profile_ids)
            return snapshot
        except ConfigError:
            raise
        except (OSError, ValueError, TypeError, RecursionError, yaml.YAMLError):
            raise ConfigError("invalid_config") from None

    @property
    def profile_ids(self):
        return tuple(self._profiles)

    def catalog(self, allowed_ids: Collection[str]) -> dict:
        allowed = set(allowed_ids)
        if not allowed.issubset(self._profiles):
            raise ValueError("denied")
        models = []
        for profile_id, profile in self._profiles.items():
            if profile_id not in allowed:
                continue
            offer = {
                key: deepcopy(profile[key])
                for key in ("label", "provider", "description", "cost", "promptCaching")
                if key in profile
            }
            offer["target"] = {
                "source": "personal",
                "serviceId": self._service_id,
                "profileId": profile_id,
            }
            for key in ("generation", "limits"):
                offer[key] = deepcopy(profile.get(key, {}))
            models.append(offer)
        catalog = {"revision": self.revision, "models": models}
        validate_payload("catalog", catalog)
        return catalog

    def prepare(self, profile_id, generation, bounds, messages, tools):
        """Prepare a trusted local call. Browser grant and operation checks belong to the transport."""
        from lodeon_model_runtime.providers import prepare_model_request
        from lodeon_model_runtime.wire import effective_limits

        profile = self._profiles.get(profile_id)
        if profile is None:
            raise ValueError("denied")
        validate_payload("generation", generation)
        validate_payload("bounds", bounds)
        if (
            generation != profile.get("generation", {})
            or effective_limits(bounds, profile.get("limits", {})) != bounds
        ):
            raise ValueError("conflict")
        request_body = json.dumps(
            {"messages": messages, "tools": tools},
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        if len(request_body) > bounds["maxInputCharacters"]:
            raise ValueError("assistant.model.context_limit_exceeded")
        return prepare_model_request(profile, bounds, messages, tools)
