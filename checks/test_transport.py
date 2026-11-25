"""Exercise the production loopback service with a local grant and one provider fixture."""

import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlencode

import yaml
from resolver.resource_schemas import BROKER_ROUTING_VARIABLES

from lodeon_customizer.configuration import PRIVATE_SETTINGS, config_revision, initialize
from lodeon_customizer import broker_form, cli
from lodeon_customizer.http_service import ModelService
from lodeon_customizer.profiles import LocalModels


class TransportTest(unittest.TestCase):
    def test_save_local_instance_and_connect_from_its_origin(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        data = Path(directory.name)
        config = data / "config.yml"
        config.write_text("assistant: {modelProfiles: {}}\n", encoding="utf-8")
        identity = initialize(data)
        private = data / PRIVATE_SETTINGS
        server = ModelService(("127.0.0.1", 0), LocalModels.load(config, identity),
                              data=data, identity=identity)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def request(method, route, *, origin=None, form=None, payload=None, token=None):
            connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            headers = {"Origin": origin} if origin else {}
            body = json.dumps(payload) if payload is not None else None
            if token:
                headers["Authorization"] = "Bearer " + token
            if payload is not None:
                headers["Content-Type"] = "application/json"
            if form:
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            try:
                connection.request(method, route, urlencode(form) if form else body, headers)
                response = connection.getresponse()
                return response.status, response.read().decode()
            finally:
                connection.close()

        def save(address):
            return request("POST", "/instance", origin=f"http://127.0.0.1:{server.server_port}",
                           form={"instance": address, "revision": config_revision(private, private.read_bytes())})

        origin = "http://localhost:7014"
        address = origin + "/lodeon/"
        status, html = save(address)
        self.assertEqual(status, 200)
        self.assertIn("Instance saved.", html)
        self.assertIn('href="/models/new"', html)
        for route in ("/model", "/model-key", "/models/remove", "/brokers/remove"):
            self.assertEqual(request("POST", route, origin=origin, form={"secret": "fixture"})[0], 403)
        self.assertEqual(yaml.safe_load(private.read_bytes())["instance"], address)
        self.assertNotIn("instance", yaml.safe_load(config.read_bytes()))
        status, html = save("http://stories.example.org/lodeon/")
        self.assertEqual(status, 400)
        self.assertIn("Enter an HTTPS instance URL", html)
        self.assertIn(f'value="{address}"', request("GET", "/")[1])
        server.set_models(LocalModels.load(config, identity))
        status, result = request("POST", "/v1/connect", origin=origin, payload={"models": False})
        self.assertEqual(status, 200)
        basic = json.loads(result)["grant"]
        self.assertTrue(json.loads(request("GET", "/connection-status")[1])["connected"])
        self.assertNotEqual(request("GET", "/connection-status", origin=origin)[0], 200)
        for method, route in (("GET", "catalog"), ("GET", "targets"), ("POST", "instance-models"),
                              ("POST", "broker"), ("POST", "invoke"), ("POST", "cancel")):
            with self.subTest(route=route):
                self.assertEqual(request(method, "/v1/" + route, origin=origin, token=basic)[0], 403)
        self.assertEqual(request("POST", "/v1/disconnect", origin=origin, token=basic)[0], 204)
        self.assertFalse(json.loads(request("GET", "/connection-status")[1])["connected"])
        for invalid in (None, {}, {"models": 1}, {"models": True, "git": True}):
            self.assertEqual(request("POST", "/v1/connect", origin=origin, payload=invalid)[0], 400)
        for other in ("http://localhost:7015", "http://127.0.0.1:7014", "https://localhost:7014"):
            with self.subTest(origin=other):
                self.assertEqual(request("POST", "/v1/connect", origin=other)[0], 403)

        local = f"http://127.0.0.1:{server.server_port}"
        token = json.loads(request("POST", "/v1/connect", origin=origin, payload={"models": True})[1])["grant"]
        shared = {"models": [{"id": "worker", "label": "Hosted model", "provider": "ollama", "sampling": {"topP": 1}}]}
        def share(grant):
            return request("POST", "/v1/instance-models", origin=origin, payload=shared, token=grant)
        self.assertEqual(share(token), (200, "{}"))
        self.assertIn("Hosted model", request("GET", "/")[1])
        self.assertNotIn(">Customized<", request("GET", "/")[1])
        revision = lambda: config_revision(config, config.read_bytes())
        form = {"profile": "worker", "temperature": "0", "topP": "", "revision": config_revision(private, private.read_bytes())}
        self.assertEqual(request("POST", "/instance-model", origin=origin, form=form)[0], 403)
        self.assertEqual(request("POST", "/instance-model", origin=local, form=form)[0], 303)
        self.assertEqual(json.loads(share(token)[1]), {"worker": {"temperature": 0}})
        self.assertIn(">Customized<", request("GET", "/")[1])
        broker = broker_form.values_for("", {}, None)
        broker.update(label="Catalog broker", members="worker | Hosted model", objective="Choose a worker",
                      revision=revision(), **{"query-strategy": "routed"})
        for task in broker_form.TASKS:
            broker[f"{task}-workers"] = "worker"
        for task in ("plan", "query"):
            response, body = request("POST", "/broker", origin=local, form={**broker, f"{task}-workers": ""})
            self.assertEqual(response, 400)
            self.assertIn(f"to {task} before saving", body)
            self.assertEqual(broker["revision"], revision())
        self.assertEqual(request("POST", "/broker", origin=local, form=broker)[0], 303)
        self.assertEqual(share(token)[0], 403)
        prompt_page = request("GET", "/brokers/edit/catalog-broker")
        self.assertEqual(prompt_page[0], 200, prompt_page[1][:200])
        self.assertIn('action="/broker-prompt"', prompt_page[1])
        *_, stamp = broker_form.prompt_files(config, "catalog-broker-routing")
        prompt = {"profile": "catalog-broker", "revision": revision(), "promptRevision": stamp,
                  "content": "Choose one of {{candidates}}."}
        self.assertEqual(request("POST", "/broker-prompt", origin=local, form=prompt)[0], 303)
        self.assertEqual(server.models.selected_broker(server.models.target("catalog-broker"), {"catalog-broker"})["routingPrompt"], prompt["content"])
        other = data / "other folder"
        other.mkdir()
        server.folder_preference = data / "preference"
        def switch(folder):
            return request("POST", "/folder", origin=local, form={"method": "load", "folder": str(folder), "current": str(server.data)})
        self.assertEqual(switch(other)[0], 200)
        self.assertFalse(server.models.brokers)
        self.assertEqual(server.folder_preference.read_text(), str(other.resolve()))
        self.assertEqual(request("POST", "/broker", origin=local, form=broker)[0], 409)
        self.assertEqual(switch(data)[0], 200)
        self.assertIn("catalog-broker", server.models.brokers)
        self.assertEqual(server.models.instance_settings["worker"], {"temperature": 0})

        # Removal changes only the named private definition. Instance-only IDs cannot be removed.
        self.assertEqual(request("GET", "/models/remove/worker")[0], 404)
        self.assertEqual(request("POST", "/models/remove", origin=local,
                                 form={"profile": "worker", "revision": revision()})[0], 409)
        doc = yaml.safe_load(config.read_bytes())
        assistant = doc["assistant"]
        assistant["modelProfiles"]["worker"] = {"label": "Personal worker", "model": "example",
            "provider": "ollama", "baseURL": "http://localhost:11434", "apiKeyEnv": "MODEL_KEY",
            "promptCaching": {"enabled": False, "retention": "default"}}
        assistant["defaultModel"] = "worker"
        config.write_text(yaml.safe_dump(doc))
        env = data / ".env"
        env.write_text("MODEL_KEY=fixture\n")
        server.set_models(LocalModels.load(config, identity))
        manifest = data / "lodeon.package.yml"
        fields = {"packageId": "test/package", "version": "1.0.0", "revision": config_revision(manifest, manifest.read_bytes())}
        self.assertEqual(request("POST", "/package", origin=local, form=fields)[0], 200)
        self.assertEqual(yaml.safe_load(manifest.read_bytes()), {"schemaVersion": 1, "id": "test/package", "version": "1.0.0"})
        self.assertEqual(request("POST", "/package", origin=local, form=fields)[0], 409)
        model_snapshot = server.models
        config.rename(data / "config.backup")
        self.assertEqual(switch(data)[0], 400)
        self.assertIs(server.models, model_snapshot)
        self.assertFalse(config.exists())
        (data / "config.backup").rename(config)
        self.assertIn("Configuration reloaded from disk.", switch(data)[1])
        self.assertNotIn("instanceModelSettings", yaml.safe_load(config.read_bytes()))
        before = revision()
        self.assertIn('/brokers/edit/catalog-broker', request("GET", "/models/remove/worker")[1])
        def remove(group, key, stamp):
            return request("POST", f"/{group}/remove", origin=local, form={"profile": key, "revision": stamp})[0]
        self.assertEqual(remove("models", "worker", before), 400)
        self.assertEqual(revision(), before)
        self.assertEqual(remove("brokers", "catalog-broker", before), 303)
        self.assertEqual(remove("models", "worker", before), 409)
        self.assertIn("clears your personal default", request("GET", "/models/remove/worker")[1])
        self.assertEqual(remove("models", "worker", revision()), 303)
        self.assertFalse(server.models.profile_ids)
        self.assertFalse(server.models.default_model)
        self.assertEqual(env.read_text(), "MODEL_KEY=fixture\n")
        self.assertEqual(server.models.instance_settings, {"worker": {"temperature": 0}})

    def test_launch_remembers_folder_and_handles_an_unavailable_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            selected = base / "My settings"
            selected.mkdir()
            initialize(selected)
            with (selected / PRIVATE_SETTINGS).open("a") as stream:
                stream.write("instance: https://example.org/lodeon/\n")
            preference = base / "settings-folder"
            preference.write_text(str(selected))
            observed = []
            service = ModelService
            def start(address, models, **args):
                server = service(("127.0.0.1", 0), models, **args)
                server.serve_forever = lambda: observed.append((server.data, models.instance, server.folder_warning))
                return server
            with (patch.object(cli, "data_directory", return_value=base / "data"),
                  patch.object(cli, "ModelService", side_effect=start), patch("sys.argv", ["customizer", "--no-browser"])):
                self.assertEqual(cli.main(), 0)
                self.assertEqual(observed[-1], (selected.resolve(), "https://example.org/lodeon/", ""))
                selected.rename(base / "disconnected")
                self.assertEqual(cli.main(), 0)
                self.assertTrue(observed[-1][2])
                self.assertEqual(observed[-1][1], "")
                self.assertEqual(preference.read_text(), str(selected))
                self.assertFalse((base / "data").exists())

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
        identity = initialize(data)
        with (data / PRIVATE_SETTINGS).open("a") as stream:
            stream.write(f"instance: {origin}\n")
        config.write_text(yaml.safe_dump({"assistant": {
            "enabled": True,
            "modelProfiles": {"local": {
                "provider": "ollama", "label": "Local", "model": "private-native",
                "baseURL": "http://localhost:11434",
                "promptCaching": {"enabled": False, "retention": "default"},
            }},
            "modelBrokers": {"mixed": routed, "other": {**broker, "label": "Other"}},
            "limits": limits, "defaultModel": "mixed",
        }}), encoding="utf-8")
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
        status, pair = request("connect", payload={"models": True})
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
