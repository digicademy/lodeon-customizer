"""Local settings and responses for the desktop app's own loopback origin."""

import hashlib
import sys
from base64 import b64encode
from functools import cache
from html import escape
from pathlib import Path
from string import Template
from threading import Thread
from urllib.parse import parse_qs

import yaml

from .configuration import ConfigError, resource_paths, save_instance, save_temperature
from .profiles import LocalModels


@cache
def template(name):
    return Template(Path(__file__).with_name(name).read_text(encoding="utf-8"))


@cache
def shell_assets():
    core_config, _ = resource_paths()
    # The desktop archive puts Core's branding next to its core configuration folder.
    resources = core_config.parent.parent
    if not getattr(sys, "frozen", False):
        resources = resources / "resources"
    branding = resources / "branding"

    def svg(name):
        return "data:image/svg+xml;base64," + b64encode((branding / name).read_bytes()).decode("ascii")

    return dict(css=Path(__file__).with_name("desktop.css").read_text(encoding="utf-8"),
                logo_light=svg("logo-light.svg"), logo_dark=svg("logo-dark.svg"),
                favicon=svg("favicon-light.svg"), favicon_dark=svg("favicon-dark.svg"))


def icon(paths):
    return (f'<svg class="icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="{paths}"/></svg>')


def layout(content, *, running=False):
    action = ""
    if running:
        power = icon("M12 2v10 M6 5.5a9 9 0 1 0 12 0")
        action = (f'<form method="post" action="/quit"><button aria-label="Quit Customizer">{power} '
                  '<span>Quit<span class="wide-label"> Customizer</span></span></button></form>')
    return template("desktop.html").substitute(content=content, action=action, **shell_assets())


def message_page(title, explanation):
    return layout(f'<section class="panel notice-page"><h1>{escape(title)}</h1><p>{escape(explanation)}</p></section>')


def model_forms(contents, revision):
    assistant = contents.get("assistant")
    if not isinstance(assistant, dict):
        assistant = {}
    profiles = assistant.get("modelProfiles", {})
    brokers = assistant.get("modelBrokers", {})
    cards = []
    for key, profile in profiles.items() if isinstance(profiles, dict) else ():
        if not isinstance(key, str) or not isinstance(profile, dict):
            continue
        label = escape(str(profile.get("label") or key))
        meta = escape(str(profile.get("provider") or ""))
        if key == assistant.get("defaultModel"):
            meta = f"{meta} · Default" if meta else "Default"
        generation = profile.get("generation")
        temperature = generation.get("temperature", "") if isinstance(generation, dict) else ""
        field = f"temperature-{len(cards)}"
        cards.append(f"""<form class="model" method="post" action="/model">
<div class="model-title">{label}</div><small>{meta}</small>
<label for="{field}">Temperature <span class="sr-only">for {label}</span></label>
<div class="input-row"><input id="{field}" type="number" min="0" max="2" step="any" name="temperature"
placeholder="Provider default" value="{escape(str(temperature), quote=True)}">
<input type="hidden" name="profile" value="{escape(key, quote=True)}">
<input type="hidden" name="revision" value="{revision}"><button>Save temperature</button></div></form>""")
    for key, broker in brokers.items() if isinstance(brokers, dict) else ():
        if isinstance(broker, dict):
            label = escape(str(broker.get("label") or key))
            kind = "Broker · Default" if key == assistant.get("defaultModel") else "Broker"
            cards.append(f'<div class="model"><div class="model-title">{label}</div><small>{kind}</small></div>')
    if cards:
        return "".join(cards)
    return """<div class="panel-body"><div class="empty"><strong>No personal models yet</strong>
<p>Add a profile to your local <code>config.yml</code> to make it available in LODEON.</p>
<details><summary>Configure an Ollama model</summary>
<p>In a fresh configuration, replace the empty <code>assistant</code> section with the example below.
Use the name of an installed model, save the file and reopen the Customizer.</p>
<pre>assistant:
  defaultModel: local-ollama
  modelProfiles:
    local-ollama:
      label: My Ollama
      provider: ollama
      model: gemma4:12b
      baseURL: http://127.0.0.1:11434
      promptCaching: {enabled: false, retention: default}</pre></details></div></div>"""


def send_html(handler, html, status=200):
    body = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-LODEON-Customizer", "desktop")
    handler.send_header("Content-Security-Policy", "default-src 'none'; img-src data:; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def page(handler, message="", status=200):
    config = handler.server.data / "config.yml"
    raw = config.read_bytes()
    try:
        contents = yaml.safe_load(raw)
        if not isinstance(contents, dict):
            raise yaml.YAMLError()
    except yaml.YAMLError:
        contents = {}
        message, status = "Check the syntax of the local config.yml file.", 400
    address = contents.get("instance", "")
    address = address if isinstance(address, str) else ""
    revision = hashlib.sha256(raw).hexdigest()
    notice = ""
    if message:
        role, style = ("alert", "error") if status >= 400 else ("status", "success")
        notice = f'<p class="feedback {style}" role="{role}">{escape(message)}</p>'
    state = ('<span class="state saved">Instance saved</span>' if address
             else '<span class="state">No instance saved</span>')
    content = template("settings.html").substitute(
        link_icon=icon("M10 13a5 5 0 0 0 7 .5l3-3a5 5 0 0 0-7-7l-2 2 M14 11a5 5 0 0 0-7-.5l-3 3a5 5 0 0 0 7 7l2-2"),
        models_icon=icon("m12 3 9 5-9 5-9-5z M3 12l9 5 9-5 M3 16l9 5 9-5"),
        folder_icon=icon("M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"),
        lock_icon=icon("M8 10V7a4 4 0 0 1 8 0v3 M6 10h12v10H6z"),
        address=escape(address, quote=True), notice=notice, instance_state=state, revision=revision,
        models=model_forms(contents, revision), config_path=escape(str(config)),
        keys_path=escape(str(config.parent / "models" / ".env")),
    )
    send_html(handler, layout(content, running=True), status)


def local_action(handler):
    server = handler.server
    if handler.headers.get_all("Origin") != ["http://" + handler.headers["Host"]]:
        raise ValueError("denied")
    if handler.path == "/quit":
        if "text/html" in handler.headers.get("Accept", ""):
            send_html(handler, message_page("Customizer stopped", "You can close this tab. Reopen the app to use your personal models again."))
        else:
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
            if isinstance(error, ConfigError) and str(error) == "invalid_instance":
                return page(handler, "Enter an HTTPS instance URL, or use HTTP on localhost, "
                            "127.0.0.1 or [::1]. Include the deployment path and omit credentials, "
                            "query parameters and fragments.", 400)
            return page(handler, "Check the submitted value and the local configuration.", 400)
        server.set_models(models)
    page(handler, "Instance saved." if instance_form else "Temperature saved.")
