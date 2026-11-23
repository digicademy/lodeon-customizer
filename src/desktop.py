"""The local settings page is accessible only on the app's own loopback origin."""

import hashlib
from html import escape
from threading import Thread
from urllib.parse import parse_qs

import yaml

from .configuration import ConfigError, save_instance, save_temperature
from .profiles import LocalModels


def temperature_forms(contents, revision):
    assistant = contents.get("assistant") if isinstance(contents, dict) else None
    profiles = assistant.get("modelProfiles") if isinstance(assistant, dict) else None
    if not isinstance(profiles, dict):
        return ""
    forms = []
    for key, profile in profiles.items():
        if not isinstance(key, str) or not isinstance(profile, dict):
            continue
        label = escape(str(profile.get("label") or key))
        generation = profile.get("generation")
        temperature = generation.get("temperature", "") if isinstance(generation, dict) else ""
        forms.append(f'''<form method="post" action="/model">
<label>{label} — temperature
<input type="number" min="0" max="2" step="any" name="temperature"
placeholder="Provider default" value="{escape(str(temperature), quote=True)}"></label>
<input type="hidden" name="profile" value="{escape(key, quote=True)}">
<input type="hidden" name="revision" value="{revision}"><button>Save temperature</button></form>''')
    return "".join(forms)


def page(handler, message="", status=200):
    server = handler.server
    config = server.data / "config.yml"
    raw = config.read_bytes()
    revision = hashlib.sha256(raw).hexdigest()
    try:
        contents = yaml.safe_load(raw)
        address = contents.get("instance", "") if isinstance(contents, dict) else ""
    except yaml.YAMLError:
        contents = {}
        address = ""
        message = "Check the syntax of the local config.yml file."
    address = escape(address if isinstance(address, str) else "", quote=True)
    html = f"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>LODEON Customizer</title>
<style>body{{font:1rem/1.55 system-ui,sans-serif;color:#203139;max-width:40rem;margin:8vh auto;padding:0 1.5rem}}
input,button{{font:inherit;padding:.45rem .65rem}}input{{width:90%;margin:.4rem 0 1rem}}
code{{overflow-wrap:anywhere}}button{{cursor:pointer}}</style>
<h1>LODEON Customizer</h1><p>{escape(message)}</p>
<p>The saved instance can invoke your configured personal models. Keys go only to their configured provider.</p>
<form method="post" action="/instance"><label for="url">LODEON instance URL</label><br>
<input id="url" name="instance" type="url" placeholder="https://stories.example.org/" required value="{address}">
<input type="hidden" name="revision" value="{revision}"><br><button>Save instance</button></form>
{temperature_forms(contents, revision)}
<p>Edit models and brokers in <code>{escape(str(config))}</code>.
Store provider keys in <code>{escape(str(server.data / 'models' / '.env'))}</code>.</p>
<form method="post" action="/quit"><button>Quit Customizer</button></form></html>"""
    body = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-LODEON-Customizer", "desktop")
    handler.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def local_action(handler):
    server = handler.server
    if handler.headers.get_all("Origin") != ["http://" + handler.headers["Host"]]:
        raise ValueError("denied")
    if handler.path == "/quit":
        handler._reply(200, {"status": "stopped"})
        Thread(target=server.shutdown, daemon=True).start()
        return
    if (handler.headers.get_content_type() != "application/x-www-form-urlencoded"
        or "Transfer-Encoding" in handler.headers or len(handler.headers.get_all("Content-Length", [])) != 1):
        raise ValueError("invalid_request")
    size = int(handler.headers["Content-Length"])
    if not 0 < size <= 8192:
        raise ValueError("invalid_request")
    fields = parse_qs(handler.rfile.read(size).decode("utf-8"), strict_parsing=True,
                      keep_blank_values=True, max_num_fields=3)
    instance_form = handler.path == "/instance"
    expected = {"instance", "revision"} if instance_form else {"profile", "temperature", "revision"}
    if set(fields) != expected or any(len(v) != 1 for v in fields.values()):
        raise ValueError("invalid_request")
    config = server.data / "config.yml"
    revision = fields["revision"][0]
    with server.settings_lock:
        def check(path):
            return LocalModels.load(path, server.identity)

        try:
            if instance_form:
                models = save_instance(config, fields["instance"][0].strip(), revision, check)
            else:
                models = save_temperature(config, fields["profile"][0], fields["temperature"][0],
                                          revision, check)
        except (ValueError, OSError) as error:
            if isinstance(error, ConfigError) and str(error) == "config_changed":
                return page(handler, "The configuration changed. Review it before saving again.", 409)
            return page(handler, "Check the submitted value and the local configuration.", 400)
        server.set_models(models)
    page(handler, "Instance saved." if instance_form else "Temperature saved.")
