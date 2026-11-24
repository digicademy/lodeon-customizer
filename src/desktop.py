"""Local settings and responses for the desktop app's own loopback origin."""

import hashlib
import sys
from base64 import b64encode
from functools import cache
from html import escape
from pathlib import Path
from string import Template
from threading import Thread
from urllib.parse import parse_qs, quote, urlsplit

import yaml

from .configuration import ConfigError, read_model_environment, resource_paths, save_instance
from .model_form import FIELDS, FormError, PROVIDERS, key_revision, render_fields, save_key, save_model, values_for
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


def model_list(contents):
    assistant = contents.get("assistant") or {}
    if not isinstance(assistant, dict):
        raise ConfigError("invalid_config")
    cards = []
    for section in ("modelProfiles", "modelBrokers"):
        items = assistant.get(section, {})
        if not isinstance(items, dict):
            raise ConfigError("invalid_config")
        for key, item in items.items():
            if not isinstance(key, str) or not isinstance(item, dict):
                raise ConfigError("invalid_config")
            label = escape(str(item.get("label") or key))
            broker = section == "modelBrokers"
            kind = "Broker" if broker else PROVIDERS.get(item.get("provider"), "")
            meta = kind + (" · Default" if assistant.get("defaultModel") == key else "")
            edit = "" if broker else f'<a href="/models/edit/{quote(key, safe="")}" aria-label="Edit {label}">Edit model</a>'
            cards.append(f'<div class="model model-entry"><div><div class="model-title">{label}</div>'
                         f'<small>{escape(meta)}</small></div>{edit}</div>')
    return "".join(cards) or '<div class="panel-body"><p>No personal models yet. Choose <strong>Add model</strong> to configure your first one.</p></div>'


def notice_html(message, status):
    if not message:
        return ""
    role, style = ("alert", "error") if status >= 400 else ("status", "success")
    return f'<p class="feedback {style}" role="{role}">{escape(message)}</p>'


def model_page(handler, key="", *, message="", status=200, submitted=None):
    config = handler.server.data / "config.yml"
    raw = config.read_bytes()
    revision = hashlib.sha256(raw).hexdigest()
    try:
        assistant = yaml.safe_load(raw).get("assistant", {})
        profiles = assistant.get("modelProfiles", {})
        if not isinstance(profiles, dict) or not all(isinstance(p, dict) for p in profiles.values()):
            raise ConfigError("invalid_config")
        profile = profiles.get(key, {})
        values = submitted if submitted is not None else values_for(key, profile, assistant.get("defaultModel"))
    except (AttributeError, TypeError, ValueError, yaml.YAMLError):
        return page(handler, "Check the model profile settings in the local config.yml file.", 400)
    if key and key not in profiles:
        return page(handler, "This model no longer exists.", 404)
    key_form = ""
    variable = profile.get("apiKeyEnv")
    if variable:
        path = config.parent / "models" / ".env"
        key_version = key_revision(path)
        try:
            configured = bool(read_model_environment(path).get(variable))
            key_hint = "A key is stored. Enter a new value to replace it." if configured else "Enter the provider key for this model."
            if not configured and status == 200 and message.startswith("Model saved."):
                message = "Model saved. Enter your provider API key, then reconnect your LODEON tab."
        except ConfigError:
            key_hint = "Check the syntax of your local models/.env file before saving."
        references = sum(other.get("apiKeyEnv") == variable for other in profiles.values())
        if references > 1:
            key_hint += f" This variable is shared by {references} profiles."
        key_form = f"""<form class="panel profile-editor key-entry" method="post" action="/model-key">
<input type="hidden" name="revision" value="{revision}">
<input type="hidden" name="keyRevision" value="{key_version}">
<input type="hidden" name="profile" value="{escape(key, quote=True)}">
<label>Provider API key<input name="secret" type="password" autocomplete="new-password" required></label>
<p class="hint">{escape(key_hint)}</p><footer><button>Save API key</button></footer></form>"""
    content = template("edit_model.html").substitute(
        title="Edit model" if key else "Add model", notice=notice_html(message, status),
        revision=revision, original=escape(key, quote=True), key_form=key_form,
        advanced_open="open" if submitted is not None else "", **render_fields(values),
    )
    return send_html(handler, layout(content, running=True), status)


def model_get(handler):
    url = urlsplit(handler.path)
    if url.path == "/models/new":
        return model_page(handler)
    if url.path.startswith("/models/edit/"):
        message = {"saved=model": "Model saved. Reconnect your LODEON tab to refresh its model list.",
                   "saved=key": "API key saved locally."}.get(url.query, "")
        return model_page(handler, url.path.removeprefix("/models/edit/"), message=message)
    return page(handler, "Model page not found.", 404)


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
        models_html = model_list(contents)
    except (ConfigError, yaml.YAMLError):
        contents = {}
        models_html = ""
        message, status = "Check the structure of the local config.yml file.", 400
    address = contents.get("instance", "")
    address = address if isinstance(address, str) else ""
    revision = hashlib.sha256(raw).hexdigest()
    notice = notice_html(message, status)
    state = ('<span class="state saved">Instance saved</span>' if address
             else '<span class="state">No instance saved</span>')
    content = template("settings.html").substitute(
        link_icon=icon("M10 13a5 5 0 0 0 7 .5l3-3a5 5 0 0 0-7-7l-2 2 M14 11a5 5 0 0 0-7-.5l-3 3a5 5 0 0 0 7 7l2-2"),
        models_icon=icon("m12 3 9 5-9 5-9-5z M3 12l9 5 9-5 M3 16l9 5 9-5"),
        folder_icon=icon("M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"),
        lock_icon=icon("M8 10V7a4 4 0 0 1 8 0v3 M6 10h12v10H6z"),
        address=escape(address, quote=True), notice=notice, instance_state=state, revision=revision,
        models=models_html, config_path=escape(str(config)),
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
    is_model = handler.path == "/model"
    if not 0 < size <= (65536 if is_model else 8192):
        raise ValueError("invalid_request")
    expected = {"/instance": {"instance", "revision"}, "/model": FIELDS,
                "/model-key": {"profile", "revision", "keyRevision", "secret"}}[handler.path]
    parsed = parse_qs(handler.rfile.read(size).decode("utf-8"), strict_parsing=True,
                      keep_blank_values=True, max_num_fields=len(expected))
    required = expected - {"default"} if is_model else expected
    if not required <= parsed.keys() <= expected or any(len(v) != 1 for v in parsed.values()):
        raise ValueError("invalid_request")
    fields = {name: values[0] for name, values in parsed.items()}
    config = server.data / "config.yml"
    with server.settings_lock:
        def check(path):
            return LocalModels.load(path, server.identity)

        try:
            if handler.path == "/instance":
                server.set_models(save_instance(config, fields["instance"].strip(), fields["revision"], check))
                return page(handler, "Instance saved.")
            if is_model:
                key, models = save_model(config, fields, check)
                server.set_models(models)
            else:
                key = fields["profile"]
                save_key(config, fields)
        except (ValueError, OSError) as error:
            if isinstance(error, ConfigError) and str(error) == "config_changed":
                return page(handler, "The configuration changed. Reopen the model or instance settings before saving again.", 409)
            if isinstance(error, ConfigError) and str(error) == "invalid_instance":
                return page(handler, "Enter an HTTPS instance URL, or use HTTP on localhost, "
                            "127.0.0.1 or [::1]. Include the deployment path and omit credentials, "
                            "query parameters and fragments.", 400)
            message = str(error) if isinstance(error, FormError) else "Check the submitted settings and the local configuration."
            if is_model:
                return model_page(handler, fields["original"], message=message, status=400, submitted=fields)
            if handler.path == "/model-key":
                return model_page(handler, fields["profile"], message=message, status=400)
            return page(handler, message, 400)
    handler.send_response(303)
    handler.send_header("Location", f"/models/edit/{quote(key, safe='')}?saved={'model' if is_model else 'key'}")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", "0")
    handler.end_headers()
