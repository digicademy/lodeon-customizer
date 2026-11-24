"""Load the user's private profiles and project only explicitly approved public offers."""

import json
from collections.abc import Collection, Mapping
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from lodeon_model_runtime.profiles import resolve_model_limits, validate_model_profile_contract
from lodeon_model_runtime.wire import validate_payload
from resolver.configuration_schema import validate_delegated_broker
from resolver.errors import ConfigResolverError

from .configuration import ConfigError, instance_origin, load_configuration, load_routing_prompts, read_model_environment


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

    def __init__(self, service_id, assistant, env_path, environment, instance=""):
        self.instance_settings = {}
        self.instance = instance
        self.origin = instance_origin(instance) if instance else None
        self._service_id = str(service_id)
        self.revision = uuid4().hex
        self._profiles = assistant["modelProfiles"] if assistant["enabled"] else {}
        self._limits = assistant["limits"]
        self._env_path = env_path
        self._environment = environment
        self.default_model = assistant.get("defaultModel")
        self.brokers = assistant["modelBrokers"] if assistant["enabled"] else {}
        self._routing_prompts = {}

    @classmethod
    def load(cls, path: Path, service_id: UUID, environment: Mapping[str, str] | None = None):
        try:
            config = load_configuration(path)
            assistant = config["assistant"]
            for profile_id, profile in assistant["modelProfiles"].items():
                validate_model_profile_contract(profile_id, profile)
            models = cls(service_id, assistant, path.parent / "models" / ".env", environment, config.get("instance", ""))
            models.instance_settings = config.get("instanceModelSettings", {}).get(models.instance, {})
            models._routing_prompts = load_routing_prompts(path.parent, assistant["promptRegistryFile"], models.brokers)
            return models
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
            offer["target"] = self.target(profile_id)
            offer["generation"] = deepcopy(profile.get("generation", {}))
            offer["limits"] = resolve_model_limits(self._limits, profile)
            models.append(offer)
        catalog = {"revision": self.revision, "models": models}
        validate_payload("catalog", catalog)
        return catalog

    def target(self, profile_id):
        return {"source": "personal", "serviceId": self._service_id, "profileId": profile_id}

    def _members(self, broker):
        return [
            self.target(member)
            if member in self._profiles
            else {"source": "instance", "profileId": member}
            for member in broker["members"]
        ]

    def targets(self, allowed_ids: Collection[str]) -> dict:
        """List granted targets without sending execution policy at connection time."""
        allowed = set(allowed_ids)
        if allowed - self._profiles.keys() - self.brokers.keys():
            raise ValueError("denied")
        catalog = self.catalog(allowed.intersection(self._profiles))
        catalog["brokers"] = [
            {
                "target": self.target(identifier),
                **{key: broker[key] for key in ("label", "description") if key in broker},
                "members": self._members(broker),
            }
            for identifier, broker in self.brokers.items()
            if identifier in allowed
        ]
        if self.default_model in allowed:
            catalog["defaultTarget"] = self.target(self.default_model)
        validate_payload("targets", catalog)
        return catalog

    def selected_broker(self, target: dict, allowed_ids: Collection[str]) -> dict:
        """Disclose only the selected granted broker and its granted local workers."""
        validate_payload("target", target)
        identifier = target["profileId"]
        if (
            target != self.target(identifier)
            or identifier not in allowed_ids
            or identifier not in self.brokers
        ):
            raise ValueError("denied")
        broker = self.brokers[identifier]
        local_members = self._profiles.keys() & broker["members"].keys()
        if local_members.difference(allowed_ids):
            raise ValueError("denied")
        policy = {
            key: deepcopy(broker[key])
            for key in ("label", "description", "router", "members", "tasks")
            if key in broker
        }
        validate_delegated_broker(policy)
        selection = {
            "target": target,
            "members": self._members(broker),
            "policy": policy,
            "models": self.catalog(local_members)["models"],
        }
        if any(task["strategy"] == "routed" for task in policy["tasks"].values()):
            template = self._routing_prompts.get(policy["router"]["prompt"])
            if template is None:
                raise ValueError("routing_prompt_unavailable")
            selection["routingPrompt"] = template
        validate_payload("selectedBroker", selection)
        return selection

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
