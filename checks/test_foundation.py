"""Verify the wheel consumer and the public boundary using only synthetic credentials."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

import yaml
from lodeon_model_runtime.wire import effective_limits, validate_payload
from lodeon_customizer.execution import execute_model
from lodeon_customizer.profiles import ConfigError, LocalModels

ROOT = Path(__file__).resolve().parents[1]
SERVICE = UUID("866af3ff-f622-48e6-8660-25e10bac2fec")
SENTINEL = "test-only-private-token"
CALL = dict(
    operation_id="op",
    connection_id="connection",
    call_id="call",
    messages=[{"role": "user", "content": "Hello"}],
    tools=[],
    generation={},
    bounds={"maxInputCharacters": 2048, "maxOutputTokens": 16, "modelRequestTimeoutSeconds": 10},
)


class FoundationTest(unittest.TestCase):
    def test_private_configuration_and_strict_projection(self):
        ollama = LocalModels.load(
            ROOT / "examples/ollama.yml", SERVICE, {"OLLAMA_BASE_URL": "http://127.0.0.1:11434"}
        )
        keyed = LocalModels.load(
            ROOT / "examples/anthropic.yml", SERVICE, {"PERSONAL_ANTHROPIC_API_KEY": SENTINEL}
        )
        self.assertEqual(ollama.catalog([])["models"], [])
        for models, private_values in [
            (ollama, ["127.0.0.1", "OLLAMA_BASE_URL", "gemma4:12b"]),
            (keyed, [SENTINEL, "PERSONAL_ANTHROPIC_API_KEY", "api.anthropic.com", "claude-sonnet"]),
        ]:
            catalog = models.catalog(models.profile_ids)
            self.assertEqual(len(catalog["models"]), 1)
            self.assertTrue(all(value not in json.dumps(catalog) for value in private_values))
            catalog["models"][0]["limits"]["apiKey"] = SENTINEL
            with self.assertRaisesRegex(ValueError, "^invalid_request$"):
                validate_payload("catalog", catalog)
        with self.assertRaisesRegex(ConfigError, "^missing_local_setting$"):
            LocalModels.load(ROOT / "examples/anthropic.yml", SERVICE, {})

    def test_config_rejection(self):
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "models.yml"
            for extra in [
                "knowledgeGraph: {}\n",
                "assistant: {modelProfiles: {}, enabled: true}\n",
                "assistant: {modelProfiles: {}, modelProfiles: {}}\n",
            ]:
                path.write_text(extra)
                with self.assertRaises(ConfigError):
                    LocalModels.load(path, SERVICE, {})
            config = yaml.safe_load((ROOT / "examples/ollama.yml").read_text())
            config["assistant"]["modelProfiles"]["local-gemma"]["access"] = {
                "allowedGroups": ["staff"]
            }
            path.write_text(yaml.safe_dump(config))
            with self.assertRaisesRegex(ConfigError, "instance_access_policy_unsupported"):
                LocalModels.load(path, SERVICE, {})

    def test_keyed_completion_and_safe_failure(self):
        models = LocalModels.load(
            ROOT / "examples/anthropic.yml", SERVICE, {"PERSONAL_ANTHROPIC_API_KEY": SENTINEL}
        )
        message = {
            "content": "ok",
            "reasoning": "private reasoning",
            "tool_calls": [
                {"id": "tool-1", "function": {"name": "lookup", "arguments": '{"q":"item"}'}}
            ],
        }
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=message, finish_reason="tool_use")],
            usage={"completion_tokens": 2},
        )
        with patch("lodeon_customizer.execution._call_provider", return_value=response) as provider:
            result = execute_model(models, "personal-sonnet", **CALL)
            self.assertEqual(provider.call_args.args[0]["api_key"], SENTINEL)
            self.assertEqual(
                result["completion"],
                {
                    "content": "ok",
                    "finishReason": "tool_calls",
                    "usage": {"outputTokens": 2},
                    "toolCalls": [{"id": "tool-1", "name": "lookup", "arguments": {"q": "item"}}],
                },
            )
            provider.side_effect = RuntimeError("invalid api key " + SENTINEL)
            failure = execute_model(models, "personal-sonnet", **CALL)
            self.assertEqual(failure["error"], {"code": "assistant.model.credentials_rejected"})
            self.assertNotIn(SENTINEL, json.dumps(failure))
            validate_payload("result", failure)
            with self.assertRaises(ValueError):
                validate_payload("result", {**result, "error": failure["error"]})

    def test_bounds_are_enforced_before_provider_execution(self):
        models = LocalModels.load(
            ROOT / "examples/ollama.yml", SERVICE, {"OLLAMA_BASE_URL": "http://localhost:11434"}
        )
        bounds = CALL["bounds"]
        self.assertEqual(
            effective_limits(bounds, {"maxOutputTokens": 8}), {**bounds, "maxOutputTokens": 8}
        )
        with patch("lodeon_customizer.execution._call_provider") as provider:
            for changes, code in [
                ({"generation": {}}, "conflict"),
                ({"bounds": {**bounds, "maxOutputTokens": 257}}, "conflict"),
                (
                    {"bounds": {**bounds, "maxInputCharacters": 2}},
                    "assistant.model.context_limit_exceeded",
                ),
                ({"bounds": {**bounds, "baseURL": "invalid"}}, "invalid_request"),
            ]:
                call = {**CALL, "generation": {"temperature": 0}, **changes}
                self.assertEqual(
                    execute_model(models, "local-gemma", **call)["error"]["code"], code
                )
            provider.assert_not_called()


if __name__ == "__main__":
    unittest.main()
