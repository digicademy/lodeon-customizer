"""Exercise the extracted app, personal files and a real LiteLLM HTTP request."""

import hashlib
import html
import json
import os
import shutil
import subprocess
import tarfile
import threading
import time
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

NAME = "LODEON-Customizer"
LOCAL = "http://127.0.0.1:8765"
ORIGIN = "https://stories.example.org"
KEY = "fixture-only-desktop-secret"


class Provider(BaseHTTPRequestHandler):
    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if (self.path != "/v1/chat/completions" or self.headers.get("Authorization") != "Bearer " + KEY
                or payload["model"] != "fixture" or payload["messages"][-1]["content"] != "ping"):
            self.send_error(400)
            return
        self.server.calls += 1
        result = {"id": "fixture", "object": "chat.completion", "created": 1234, "model": "fixture",
                  "choices": [{"index": 0, "message": {"role": "assistant", "content": "pong"},
                               "finish_reason": "stop"}]}
        body = json.dumps(result).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def request(method, path, body=None, *, origin=None, grant=None, status=200, form=False):
    conn = HTTPConnection("127.0.0.1", 8765, timeout=45)
    try:
        headers = {}
        if origin:
            headers["Origin"] = origin
        if grant:
            headers["Authorization"] = "Bearer " + grant
        if body is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
            body = urlencode(body) if form else json.dumps(body)
        conn.request(method, path, body, headers)
        res = conn.getresponse()
        raw = res.read()
        if res.status != status:
            raise RuntimeError(f"{method} {path} returned {res.status}, expected {status}")
        if KEY.encode() in raw:
            raise RuntimeError("Credential in a public response")
        if res.getheader("Content-Type", "").startswith("application/json") and raw:
            return json.loads(raw)
        return raw.decode()
    finally:
        conn.close()


def check_archive(archive, scratch, system):
    scratch.mkdir(parents=True)
    if system == "macos":
        subprocess.run(["ditto", "-x", "-k", archive, scratch], check=True)
        exe = scratch / (NAME + ".app") / "Contents/MacOS" / NAME
    elif system == "windows":
        shutil.unpack_archive(archive, scratch)
        exe = scratch / NAME / (NAME + ".exe")
    else:
        with tarfile.open(archive) as package:
            package.extractall(scratch, filter="data")
        exe = scratch / NAME / NAME
    # Use the normal desktop data path in a fresh home. No source checkout or Python path.
    home = scratch / "User Renée"
    home.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "LODEON_", "VIRTUAL_ENV"))}
    env.update(HOME=str(home), USERPROFILE=str(home), LOCALAPPDATA=str(home / "local"),
               XDG_DATA_HOME=str(home / "xdg"), TOKENIZERS_PARALLELISM="false")
    data_base = {"windows": home / "local", "linux": home / "xdg",
                 "macos": home / "Library/Application Support"}[system]
    data = data_base / "LODEON Customizer" / "data"
    config = data / "config.yml"
    proc = None

    def launch():
        nonlocal proc
        proc = subprocess.Popen([exe, "--no-browser"], cwd=home, env=env)
        until = time.monotonic() + 60
        while time.monotonic() < until and proc.poll() is None:
            try:
                page = request("GET", "/")
                if str(config) not in html.unescape(page):
                    raise RuntimeError("Unexpected data folder or another instance on port 8765")
                return
            except ConnectionRefusedError:
                time.sleep(0.15)
        raise RuntimeError(f"Desktop startup failed, exit status {proc.poll()}")

    def quit_app():
        request("POST", "/quit", origin=LOCAL)
        if proc.wait(timeout=15) != 0:
            raise RuntimeError("Desktop did not quit cleanly")

    with ThreadingHTTPServer(("127.0.0.1", 0), Provider) as provider:
        provider.calls = 0
        threading.Thread(target=provider.serve_forever, daemon=True).start()
        try:
            launch()
            subprocess.run([exe, "--no-browser"], cwd=home, env=env, timeout=15, check=True)
            identity = (data / ".service-id").read_bytes()
            request("POST", "/v1/connect", origin=ORIGIN, status=403)
            form = {"instance": ORIGIN + "/lodeon/", "revision": hashlib.sha256(config.read_bytes()).hexdigest()}
            request("POST", "/instance", form, origin=ORIGIN, form=True, status=403)
            request("POST", "/instance", form, origin=LOCAL, form=True)
            request("POST", "/v1/connect", origin="https://other.example.org", status=403)
            pair = request("POST", "/v1/connect", origin=ORIGIN)
            catalog = request("GET", "/v1/targets", origin=ORIGIN, grant=pair["grant"])
            if catalog["models"]:
                raise RuntimeError("Expected an empty first-run catalog")
            quit_app()
            config.write_text(f"""instance: {ORIGIN}/lodeon/
assistant:
  defaultModel: sample
  modelProfiles:
    sample:
      label: Desktop test
      provider: openai-compatible
      model: fixture
      baseURL: http://127.0.0.1:{provider.server_port}/v1
      apiKeyEnv: TEST_MODEL_KEY
      promptCaching: {{enabled: false, retention: default}}
""", encoding="utf-8")
            keyfile = data / "models" / ".env"
            keyfile.write_text("TEST_MODEL_KEY=" + KEY + "\n", encoding="utf-8")
            original = config.read_bytes(), keyfile.read_bytes(), identity
            launch()
            if (config.read_bytes(), keyfile.read_bytes(), (data / ".service-id").read_bytes()) != original:
                raise RuntimeError("Desktop restart changed personal data")
            request("GET", "/v1/targets", origin=ORIGIN, grant=pair["grant"], status=403)
            pair = request("POST", "/v1/connect", origin=ORIGIN)
            access = {"origin": ORIGIN, "grant": pair["grant"]}
            catalog = request("GET", "/v1/targets", **access)
            call = {"operationId": "desktop", "callId": "one", "connectionId": pair["connectionId"],
                    "revision": catalog["revision"], "target": catalog["models"][0]["target"],
                    "task": "answer", "generation": {}, "tools": [], "messages": [{"role":"user","content":"ping"}],
                    "bounds": {"maxInputCharacters": 1024, "maxOutputTokens": 8, "modelRequestTimeoutSeconds": 30}}
            result = request("POST", "/v1/invoke", call, **access)
            if result.get("completion", {}).get("content") != "pong" or provider.calls != 1:
                raise RuntimeError(f"Packaged model call failed: {result.get('error')}")
            quit_app()
        finally:
            if proc and proc.poll() is None:
                proc.kill()
                proc.wait()
            provider.shutdown()
    print(f"{system}: extracted app passed first launch, local setup, restart and provider invocation")
