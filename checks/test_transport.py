"""Exercise the production loopback service with a local grant and one provider fixture."""

import json
import threading
import unittest
from http.client import HTTPConnection
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from lodeon_customizer.http_service import ModelService
from lodeon_customizer.profiles import LocalModels


class TransportTest(unittest.TestCase):
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
        models = LocalModels(
            uuid4(),
            {
                "enabled": True,
                "modelProfiles": {
                    "local": {
                        "provider": "ollama",
                        "label": "Local",
                        "model": "private-native",
                        "baseURL": "http://localhost:11434",
                        "promptCaching": {"enabled": False, "retention": "default"},
                    }
                },
                "modelBrokers": {"mixed": broker, "other": {**broker, "label": "Other"}},
                "limits": limits,
                "defaultModel": "mixed",
            },
            None,
            {},
        )
        origin = "https://lodeon.example"
        models.origin = origin
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
        choice = {"target": catalog["defaultTarget"], "revision": catalog["revision"]}
        status, selected = request("broker", token, choice)
        self.assertEqual(status, 200)
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
