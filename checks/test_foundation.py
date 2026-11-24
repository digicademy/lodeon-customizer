"""Verify the wheel consumer and the public boundary using only synthetic credentials."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

import yaml
from lodeon_model_runtime.wire import effective_limits, validate_payload
from lodeon_customizer.configuration import data_directory
from lodeon_customizer.model_form import FIELDS, FormError, key_revision, save_key, save_model, values_for
from lodeon_customizer.execution import execute_model
from lodeon_customizer.profiles import ConfigError, LocalModels

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
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.ollama = self.config("local-gemma", {
            "label": "Local Gemma", "provider": "ollama", "model": "gemma4:12b",
            "baseURLEnv": "OLLAMA_BASE_URL", "generation": {"temperature": 0},
            "limits": {"maxOutputTokens": 256, "modelRequestTimeoutSeconds": 90},
            "access": {"allowedGroups": ["staff"]},
        })
        self.keyed = self.config("personal-sonnet", {
            "label": "Personal Sonnet", "provider": "anthropic", "model": "claude-sonnet",
            "baseURL": "https://api.anthropic.com", "apiKeyEnv": "PERSONAL_ANTHROPIC_API_KEY",
        })

    def config(self, model_id, profile):
        profile["promptCaching"] = {"enabled": False, "retention": "default"}
        path = self.root / (model_id + ".yml")
        path.write_text(yaml.safe_dump({"assistant": {
            "defaultModel": model_id, "modelProfiles": {model_id: profile},
        }}))
        return path

    def test_private_configuration_and_strict_projection(self):
        ollama = LocalModels.load(
            self.ollama, SERVICE, {"OLLAMA_BASE_URL": "http://127.0.0.1:11434"}
        )
        keyed = LocalModels.load(
            self.keyed, SERVICE, {"PERSONAL_ANTHROPIC_API_KEY": SENTINEL}
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

    def test_configuration_uses_core_schema_and_model_file(self):
        path = self.root / "config.yml"
        path.write_text("assistant: {enabled: true, modelProfiles: {}}\nknowledgeGraph: {}\n")
        self.assertEqual(LocalModels.load(path, SERVICE).profile_ids, ())
        path.write_text("assistant: {unsupportedField: true}\n")
        with self.assertRaises(ConfigError):
            LocalModels.load(path, SERVICE)
        models = LocalModels.load(self.keyed, SERVICE)
        env_path = self.root / "models" / ".env"
        env_path.parent.mkdir()
        for key in [SENTINEL, "rotated-test-value"]:
            env_path.write_text("PERSONAL_ANTHROPIC_API_KEY=" + key + "\n")
            request = models.prepare("personal-sonnet", {}, CALL["bounds"], CALL["messages"], [])
            self.assertEqual(request.kwargs["api_key"], key)
        env_path.unlink()
        with self.assertRaisesRegex(ConfigError, "^missing_local_setting$"):
            models.prepare("personal-sonnet", {}, CALL["bounds"], CALL["messages"], [])

    def test_form_edits_preserve_yaml_and_detect_a_stale_form(self):
        path = self.ollama
        path.write_text("# Personal configuration\n" + path.read_text())
        key = "local-gemma"
        original = yaml.safe_load(path.read_bytes())["assistant"]["modelProfiles"][key]
        fields = dict.fromkeys(FIELDS, "")
        fields.update({k: str(v) for k, v in values_for(key, original, key).items()})
        fields.update(revision=hashlib.sha256(path.read_bytes()).hexdigest(), temperature="0.65")
        def check(candidate):
            return LocalModels.load(candidate, SERVICE)

        _, models = save_model(path, fields, check)
        self.assertEqual(models.catalog(models.profile_ids)["models"][0]["generation"]["temperature"], 0.65)
        self.assertIn("# Personal configuration", path.read_text())
        saved = path.read_bytes()
        with self.assertRaisesRegex(ConfigError, "config_changed"):
            save_model(path, fields, check)
        self.assertEqual(saved, path.read_bytes())
        fields.update(revision=hashlib.sha256(saved).hexdigest(), temperature="")
        _, models = save_model(path, fields, check)
        self.assertNotIn("temperature", models.catalog(models.profile_ids)["models"][0]["generation"])
        stored = yaml.safe_load(path.read_bytes())["assistant"]["modelProfiles"][key]
        for name in ("access", "baseURLEnv", "limits", "promptCaching"):
            self.assertEqual(stored[name], original[name])

    def test_create_keyed_profile_and_rotate_credential_without_exposing_it(self):
        path = self.root / "config.yml"
        path.write_text("assistant: {modelProfiles: {}}\n")
        form = dict.fromkeys(FIELDS, "")
        form.update(values_for("", {}, None), label="Research model", provider="anthropic", model="test",
                    topP="0.8", default="on", revision=hashlib.sha256(path.read_bytes()).hexdigest())
        key, models = save_model(path, form, lambda candidate: LocalModels.load(candidate, SERVICE))
        self.assertEqual(models.default_model, key)
        content = path.read_bytes()
        form["revision"] = hashlib.sha256(content).hexdigest()
        with self.assertRaises(FormError):
            save_model(path, form, lambda candidate: LocalModels.load(candidate, SERVICE))
        self.assertEqual(path.read_bytes(), content)
        env = self.root / "models/.env"
        env.parent.mkdir()
        env.write_text("# Retain unrelated settings\nOTHER=ok\n")
        submission = {"profile": key, "revision": form["revision"], "keyRevision": key_revision(env), "secret": SENTINEL}
        save_key(path, submission)
        with self.assertRaisesRegex(ConfigError, "config_changed"):
            save_key(path, submission)
        submission.update(keyRevision=key_revision(env), secret="rotated-'token")
        save_key(path, submission)
        reloaded = LocalModels.load(path, SERVICE)
        req = reloaded.prepare(key, {"topP": 0.8}, CALL["bounds"], CALL["messages"], [])
        self.assertEqual(req.kwargs["api_key"], submission["secret"])
        self.assertIn("# Retain unrelated settings\nOTHER=ok", env.read_text())
        self.assertEqual(path.read_bytes(), content)
        self.assertNotIn(submission["secret"], json.dumps(reloaded.targets({key})))

    def test_default_data_folder_has_the_application_filename(self):
        with patch("pathlib.Path.home", return_value=self.root), patch.dict(
            "os.environ", XDG_DATA_HOME=str(self.root), LOCALAPPDATA=str(self.root)
        ):
            self.assertEqual(data_directory().parts[-2:], ("LODEON-Customizer", "data"))

    def test_keyed_completion_and_safe_failure(self):
        models = LocalModels.load(
            self.keyed, SERVICE, {"PERSONAL_ANTHROPIC_API_KEY": SENTINEL}
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
            self.ollama, SERVICE, {"OLLAMA_BASE_URL": "http://localhost:11434"}
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
