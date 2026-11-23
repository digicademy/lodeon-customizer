"""Load the user's private profiles and project only explicitly approved public offers."""

import json
from collections.abc import Collection, Mapping
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from lodeon_model_runtime.profiles import resolve_model_limits, validate_model_profile_contract
from lodeon_model_runtime.wire import validate_payload
from resolver.errors import ConfigResolverError

from .configuration import ConfigError, load_assistant, read_model_environment


def _resolve(configured, environment):
    profile = deepcopy(configured)
    profile.pop("access", None)
    for field in ("baseURL", "apiKey"):
        env_name = profile.pop(field + "Env", None)
        if env_name is not None:
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

    def __init__(self, service_id, assistant, env_path, environment):
        self._service_id = str(service_id)
        self.revision = uuid4().hex
        self._profiles = assistant["modelProfiles"] if assistant["enabled"] else {}
        self._limits = assistant["limits"]
        self._env_path = env_path
        self._environment = environment
        self.default_model = assistant.get("defaultModel")
        self.brokers = assistant["modelBrokers"] if assistant["enabled"] else {}

    @classmethod
    def load(cls, path: Path, service_id: UUID, environment: Mapping[str, str] | None = None):
        try:
            assistant = load_assistant(path)
            for profile_id, profile in assistant["modelProfiles"].items():
                validate_model_profile_contract(profile_id, profile)
            return cls(service_id, assistant, path.parent / "models" / ".env", environment)
        except (OSError, ValueError, ConfigResolverError, RecursionError):
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
            offer["generation"] = deepcopy(profile.get("generation", {}))
            offer["limits"] = resolve_model_limits(self._limits, profile)
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
            or effective_limits(bounds, resolve_model_limits(self._limits, profile)) != bounds
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
        environment = self._environment
        if environment is None and ("apiKeyEnv" in profile or "baseURLEnv" in profile):
            environment = read_model_environment(self._env_path)
        return prepare_model_request(_resolve(profile, environment or {}), bounds, messages, tools)
