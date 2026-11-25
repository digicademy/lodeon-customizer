"""Exercise the extracted app, personal files and a real LiteLLM HTTP request."""

import re
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


def request(method, path, body=None, *, origin=None, grant=None, status=200, form=False, timeout=45):
    conn = HTTPConnection("127.0.0.1", 8765, timeout=timeout)
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
    data = data_base / NAME / "data"
    config = data / "config.yml"
    proc = None
    desktop_args = [exe, "--no-browser"]
    if system == "linux":
        browser = home / "smoke-browser"
        browser.write_text(
            """#!/bin/sh
printf '%s\\n' "$1" "${LD_LIBRARY_PATH-<unset>}" > "$HOME/browser-launch"
""",
            encoding="utf-8",
        )
        browser.chmod(0o700)
        env.update(BROWSER="smoke-browser %s", PATH=str(home) + os.pathsep + env["PATH"])
        env.pop("LD_LIBRARY_PATH", None)
        env.pop("LD_LIBRARY_PATH_ORIG", None)
        desktop_args = [exe]

    def launch(phase):
        nonlocal proc
        proc = subprocess.Popen(desktop_args, cwd=home, env=env)
        until = time.monotonic() + 60
        last_error = None
        while proc.poll() is None:
            remaining = until - time.monotonic()
            if remaining <= 0:
                raise RuntimeError(f"{phase}: {LOCAL} was not ready within 60 seconds") from last_error
            try:
                page = request("GET", "/", timeout=min(2, remaining))
            except (ConnectionRefusedError, TimeoutError) as error:
                last_error = error
                time.sleep(0.15)
                continue
            if f'name="current" value="{data.resolve()}"' not in html.unescape(page):
                raise RuntimeError(f"{phase}: unexpected data folder or another instance on port 8765")
            return
        raise RuntimeError(f"{phase}: desktop exited with status {proc.returncode} before it was ready")

    def quit_app():
        request("POST", "/quit", origin=LOCAL)
        if proc.wait(timeout=15) != 0:
            raise RuntimeError("Desktop did not quit cleanly")

    with ThreadingHTTPServer(("127.0.0.1", 0), Provider) as provider:
        provider.calls = 0
        threading.Thread(target=provider.serve_forever, daemon=True).start()
        try:
            launch("First launch")
            if system == "linux":
                record = home / "browser-launch"
                if record.read_text().splitlines() != [LOCAL + "/", "<unset>"]:
                    raise RuntimeError("Browser inherited the bundled library path on first launch")
                record.unlink()
                env["LD_LIBRARY_PATH"] = str(home / "host libraries")
            subprocess.run(desktop_args, cwd=home, env=env, timeout=15, check=True)
            if system == "linux" and record.read_text().splitlines() != [LOCAL + "/", env["LD_LIBRARY_PATH"]]:
                raise RuntimeError("Browser did not receive the original host library path on relaunch")
            if not (data / "lodeon.package.yml").is_file() or ".env" not in (data / ".gitignore").read_text().splitlines() or (data / "models").exists():
                raise RuntimeError("First launch did not create the expected local package")
            request("POST", "/v1/connect", origin=ORIGIN, status=403)
            form = {"instance": ORIGIN + "/lodeon/", "revision": re.search(r'name="revision" value="([a-f0-9]+)"', request("GET", "/"))[1]}
            request("POST", "/instance", form, origin=ORIGIN, form=True, status=403)
            request("POST", "/instance", form, origin=LOCAL, form=True)
            request("POST", "/v1/connect", origin="https://other.example.org", status=403)
            pair = request("POST", "/v1/connect", {"models": True}, origin=ORIGIN)
            catalog = request("GET", "/v1/targets", origin=ORIGIN, grant=pair["grant"])
            if catalog["models"]:
                raise RuntimeError("Expected an empty first-run catalog")
            quit_app()
            config.write_text(f"""assistant:
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
            keyfile = data / ".env"
            keyfile.write_text("TEST_MODEL_KEY=" + KEY + "\n", encoding="utf-8")
            private = data / ".data/customizer.yml"
            original = config.read_bytes(), keyfile.read_bytes(), private.read_bytes()
            launch("Restart")
            if (config.read_bytes(), keyfile.read_bytes(), private.read_bytes()) != original:
                raise RuntimeError("Desktop restart changed personal data")
            request("GET", "/v1/targets", origin=ORIGIN, grant=pair["grant"], status=403)
            pair = request("POST", "/v1/connect", {"models": True}, origin=ORIGIN)
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
