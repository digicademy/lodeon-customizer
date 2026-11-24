"""Exercise the production loopback service with a local grant and one provider fixture."""

import hashlib
import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlencode
from uuid import uuid4

import yaml
from resolver.resource_schemas import BROKER_ROUTING_VARIABLES

from lodeon_customizer.http_service import ModelService
from lodeon_customizer.profiles import LocalModels


class TransportTest(unittest.TestCase):
    def test_save_local_instance_and_connect_from_its_origin(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        data = Path(directory.name)
        config = data / "config.yml"
        config.write_text("assistant: {modelProfiles: {}}\n", encoding="utf-8")
        identity = uuid4()
        server = ModelService(("127.0.0.1", 0), LocalModels.load(config, identity),
                              data=data, identity=identity)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def request(method, route, *, origin=None, form=None):
            connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            headers = {"Origin": origin} if origin else {}
            if form:
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            try:
                connection.request(method, route, urlencode(form) if form else None, headers)
                response = connection.getresponse()
                return response.status, response.read().decode()
            finally:
                connection.close()

        def save(address):
            return request("POST", "/instance", origin=f"http://127.0.0.1:{server.server_port}",
                           form={"instance": address, "revision": hashlib.sha256(config.read_bytes()).hexdigest()})

        origin = "http://localhost:7014"
        address = origin + "/lodeon/"
        status, html = save(address)
        self.assertEqual(status, 200)
        self.assertIn("Instance saved.", html)
        self.assertIn('href="/models/new"', html)
        for route in ("/model", "/model-key"):
            self.assertEqual(request("POST", route, origin=origin, form={"secret": "fixture"})[0], 403)
        self.assertEqual(yaml.safe_load(config.read_bytes())["instance"], address)
        status, html = save("http://stories.example.org/lodeon/")
        self.assertEqual(status, 400)
        self.assertIn("Enter an HTTPS instance URL", html)
        self.assertIn(f'value="{address}"', request("GET", "/")[1])
        server.set_models(LocalModels.load(config, identity))
        self.assertEqual(request("POST", "/v1/connect", origin=origin)[0], 200)
        for other in ("http://localhost:7015", "http://127.0.0.1:7014", "https://localhost:7014"):
            with self.subTest(origin=other):
                self.assertEqual(request("POST", "/v1/connect", origin=other)[0], 403)

    def test_scoped_model_and_selected_broker(self):
        tasks = {
            k: {"strategy": "fixed", "model": "local", "fallbacks": ["hosted"]}
            for k in ("plan", "query", "answer", "propose", "probe", "suggest", "retry")
        }
        broker = {
            "label": "Mixed",
            "router": {"model": "hosted", "prompt": "router", "objective": "private goal"},
            "members": {
                "local": {"routingHint": "private hint"},
                "hosted": {"routingHint": "query"},
            },
            "tasks": tasks,
        }
        limits = {
            "maxInputCharacters": 2048,
            "maxOutputTokens": 32,
            "modelRequestTimeoutSeconds": 5,
        }
        origin = "https://lodeon.example"
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        data = Path(directory.name)
        root = data / "runtime/prompts"
        root.mkdir(parents=True)
        (root / "registry.yml").write_text(yaml.safe_dump({
            "schemaVersion": 1,
            "prompts": {"router": {"file": "route.md", "variables": sorted(BROKER_ROUTING_VARIABLES)}},
            "chains": {"chat": [{"prompt": "assistant-guidance", "role": "system"}]},
        }), encoding="utf-8")
        template = "Private routing instructions for {{candidates}}"
        prompt_file = root / "route.md"
        prompt_file.write_text(template, encoding="utf-8")
        config = data / "config.yml"
        routed = {**broker, "tasks": {**tasks, "query": {
            "strategy": "routed", "candidates": ["hosted"], "fallbacks": ["local"],
        }}}
        config.write_text(yaml.safe_dump({"instance": origin, "assistant": {
            "enabled": True,
            "modelProfiles": {"local": {
                "provider": "ollama", "label": "Local", "model": "private-native",
                "baseURL": "http://localhost:11434",
                "promptCaching": {"enabled": False, "retention": "default"},
            }},
            "modelBrokers": {"mixed": routed, "other": {**broker, "label": "Other"}},
            "limits": limits, "defaultModel": "mixed",
        }}), encoding="utf-8")
        identity = uuid4()
        models = LocalModels.load(config, identity)
        self.assertNotIn("routingPrompt", models.selected_broker(models.target("other"), {"local", "other"}))
        prompt_file.unlink()
        reloaded = LocalModels.load(config, identity)
        with self.assertRaisesRegex(ValueError, "routing_prompt_unavailable"):
            reloaded.selected_broker(reloaded.target("mixed"), {"local", "mixed"})
        server = ModelService(("127.0.0.1", 0), models)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        from lodeon_customizer.grants import Grants
        server.grants = Grants(origin, {"local", "mixed"}, calls=2, tokens=64, lifetime=60)

        def request(route, token=None, payload=None, **overrides):
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            try:
                method = "GET" if route in ("catalog", "targets") else "POST"
                conn.request(
                    method,
                    "/v1/" + route,
                    None if payload is None else json.dumps(payload),
                    {
                        "Origin": origin,
                        "Content-Type": "application/json",
                        **({"Authorization": "Bearer " + token} if token else {}),
                        **overrides,
                    },
                )
                response = conn.getresponse()
                body = response.read()
                return response.status, json.loads(body) if body else None
            finally:
                conn.close()

        self.assertEqual(request("connect", Origin="https://foreign.example")[0], 403)
        status, pair = request("connect")
        self.assertEqual(status, 200, pair)
        token = pair["grant"]
        self.assertEqual(request("targets", token, Host="foreign.example")[0], 403)
        status, catalog = request("targets", token)
        self.assertEqual(status, 200, catalog)
        self.assertEqual([b["target"]["profileId"] for b in catalog["brokers"]], ["mixed"])
        self.assertEqual(catalog["defaultTarget"], catalog["brokers"][0]["target"])
        self.assertNotIn("private", json.dumps(catalog))
        self.assertNotIn(template, json.dumps(catalog))
        choice = {"target": catalog["defaultTarget"], "revision": catalog["revision"]}
        status, selected = request("broker", token, choice)
        self.assertEqual(status, 200)
        self.assertEqual(selected["routingPrompt"], template)
        self.assertNotIn(str(root), json.dumps(selected))
        self.assertEqual(selected["policy"]["router"]["objective"], "private goal")
        self.assertEqual(
            request(
                "broker", token, {**choice, "target": {**choice["target"], "profileId": "other"}}
            )[0],
            403,
        )
        call = {
            "target": catalog["models"][0]["target"],
            "revision": catalog["revision"],
            "generation": {},
            "bounds": limits,
            "messages": [{"role": "user", "content": "Hello"}],
            "tools": [],
            "connectionId": pair["connectionId"],
            "operationId": "op",
            "callId": "call",
            "task": "answer",
        }
        with patch("lodeon_customizer.execution._call_provider") as provider:
            provider.return_value = SimpleNamespace(
                choices=[SimpleNamespace(message={"content": "Ready"}, finish_reason="stop")]
            )
            self.assertEqual(request("invoke", token, {**call, "baseURL": "bogus"})[0], 400)
            status, result = request("invoke", token, call)
            self.assertEqual(status, 200, result)
            self.assertEqual(result["completion"]["content"], "Ready")
            self.assertEqual(request("invoke", token, call)[0], 409)
            cancellation = {
                "operationId": "op",
                "callId": "other",
                "connectionId": pair["connectionId"],
            }
            self.assertEqual(request("cancel", token, cancellation)[0], 204)
            self.assertEqual(request("invoke", token, {**call, **cancellation})[0], 409)
            self.assertEqual(request("invoke", token, {**call, "callId": "over-budget"})[0], 429)
            provider.assert_called_once()
        self.assertEqual(request("disconnect", token)[0], 204)
        self.assertEqual(request("targets", token)[0], 403)
