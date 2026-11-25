"""Local settings and responses for the desktop app's own loopback origin."""

import sys
from base64 import b64encode
from functools import cache
from hashlib import sha256
from html import escape
from pathlib import Path
from string import Template
from threading import Thread
from urllib.parse import parse_qs, quote, urlsplit

import yaml

from .configuration import (ConfigError, PRIVATE_SETTINGS, config_revision, read_manifest,
                            read_model_environment, resource_paths, save_instance, update_settings)
from . import broker_form
from .instance_form import render_instance, save_sampling
from .folders import open_folder, pick_folder
from .form_fields import field_help, form_field
from .model_form import (FIELDS, FormError, PROVIDERS, dependent_brokers, key_revision,
                         remove_profile, render_fields, save_key, save_model, values_for)
from .profiles import LocalModels

PERSONAL_SECTIONS = {"models": ("modelProfiles", "model"), "brokers": ("modelBrokers", "broker")}


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

    ui = Path(__file__).resolve().parent
    if not (ui / "desktop-theme.js").is_file() and not getattr(sys, "frozen", False):
        ui = ui.parent / "build/ui/compiled"
    return dict(theme_script=(ui / "desktop-theme.js").read_text(encoding="utf-8"),
                css=(ui / "desktop.css").read_text(encoding="utf-8"),
                logo_light=svg("logo-light.svg"), logo_dark=svg("logo-dark.svg"),
                favicon=svg("favicon-light.svg"), favicon_dark=svg("favicon-dark.svg"))


def icon(paths):
    return (f'<svg class="ld-lucide-icon" aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="{paths}"/></svg>')


def instance_form(server):
    private = server.data / PRIVATE_SETTINGS
    revision = config_revision(private, private.read_bytes())
    address = server.models.instance
    connected = server.grants.connected()
    help_text = field_help("instance", "Instance connection",
                           "Enter the URL from your LODEON tab, including its deployment path. Save it here, then choose Settings → Customize Workbench in that tab.")
    value = escape(address, quote=True) if isinstance(address, str) else ""
    return (f'<form id="instance-link" class="instance-connection ld-project-switcher" method="post" action="/instance">'
            f'<div class="instance-label"><label for="field-instance">Instance connection</label>{help_text}</div>'
            f'<input class="instance-url" id="field-instance" name="instance" type="url" aria-describedby="help-instance" '
            f'value="{value}" placeholder="https://example.org/lodeon/" required>'
            f'<span class="link-status" role="status" data-connection-status data-connected="{str(connected).lower()}" '
            f'data-instance="{value}">{"Connected" if connected else "Disconnected"}</span>'
            f'<input type="hidden" name="revision" value="{revision}"></form>')


def layout(content, *, server=None):
    connection = ""
    action = ""
    if server is not None:
        if not server.folder_warning and (server.data / PRIVATE_SETTINGS).is_file():
            connection = instance_form(server)
        save = ""
        if connection:
            disk = icon("M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z M7 3v6h9V3 M7 21v-8h10v8")
            save = f'<button class="ld-button" type="submit" form="instance-link" aria-label="Save instance">{disk}Save</button>'
        power = icon("M12 2v10 M6 5.5a9 9 0 1 0 12 0")
        action = (f'<div class="ld-action-group">{save}<form method="post" action="/quit">'
                  f'<button class="ld-button" type="submit" aria-label="Quit Customizer">{power}Quit</button></form></div>')
    return template("desktop.html").substitute(content=content, action=action, connection=connection, **shell_assets())


def message_page(title, explanation):
    return layout(f'<section class="panel notice-page"><h1>{escape(title)}</h1><p>{escape(explanation)}</p></section>')


def model_list(contents):
    assistant = contents.get("assistant") or {}
    if not isinstance(assistant, dict):
        raise ConfigError("invalid_config")
    cards = []
    for group, (section, _) in PERSONAL_SECTIONS.items():
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
            target = quote(key, safe="")
            edit = f'<a class="ld-button" href="/{group}/edit/{target}" aria-label="Edit {label}">Edit</a>'
            remove = f'<a class="ld-button danger" href="/{group}/remove/{target}" aria-label="Remove {label}">Remove</a>'
            cards.append(f'<div class="model model-entry"><div><div class="model-title">{label}</div>'
                         f'<small>{escape(meta)}</small></div><div class="actions">{edit}{remove}</div></div>')
    return "".join(cards) or '<div class="panel-body"><p>No local models or brokers configured.</p></div>'


def notice_html(message, status):
    if not message:
        return ""
    role, style = ("alert", "error") if status >= 400 else ("status", "success")
    return f'<p class="feedback {style}" role="{role}">{escape(message)}</p>'


def model_page(handler, key="", *, message="", status=200, submitted=None):
    config = handler.server.data / "config.yml"
    raw = config.read_bytes()
    revision = config_revision(config, raw)
    try:
        settings = yaml.safe_load(raw)
        assistant = settings.get("assistant", {})
        profiles = assistant.get("modelProfiles", {})
        if not isinstance(profiles, dict) or not all(isinstance(p, dict) for p in profiles.values()):
            raise ConfigError("invalid_config")
        profile = profiles.get(key, {})
        values = submitted if submitted is not None else values_for(key, profile, assistant.get("defaultModel"))
        if submitted is None and not key and not profiles and not assistant.get("modelBrokers"):
            values["default"] = "on"
    except (AttributeError, TypeError, ValueError, yaml.YAMLError):
        return page(handler, "Check the model profile settings in the local config.yml file.", 400)
    if key and key not in profiles:
        return page(handler, "This model no longer exists.", 404)
    key_form = ""
    variable = profile.get("apiKeyEnv")
    if variable:
        path = config.parent / ".env"
        key_version = key_revision(path)
        try:
            configured = bool(read_model_environment(path).get(variable))
            key_hint = "A key is stored. Enter a new value to replace it." if configured else "Enter the provider key for this model."
            if not configured and status == 200 and message.startswith("Model saved."):
                message = "Model saved. Enter your provider API key, then reconnect your LODEON tab."
        except ConfigError:
            key_hint = "Check the syntax of your local .env file before saving."
        references = sum(other.get("apiKeyEnv") == variable for other in profiles.values())
        if references > 1:
            key_hint += f" This variable is shared by {references} profiles."
        secret = form_field("secret", "Provider API key", "Stored in the local .env file. A saved key can be replaced here.", kind="password", attrs='autocomplete="new-password" required')
        key_form = f"""<form class="panel profile-editor key-entry" method="post" action="/model-key">
<input type="hidden" name="revision" value="{revision}">
<input type="hidden" name="keyRevision" value="{key_version}">
<input type="hidden" name="profile" value="{escape(key, quote=True)}">
{secret}
<p class="hint">{escape(key_hint)}</p><footer><button class="ld-button">Save API key</button></footer></form>"""
    content = template("edit_model.html").substitute(
        title="Edit model" if key else "Add model", notice=notice_html(message, status),
        revision=revision, original=escape(key, quote=True), key_form=key_form,
        advanced_open="open" if submitted is not None else "", **render_fields(values),
    )
    return send_editor(handler, content, status)


def editor_page(handler, title, form, message="", status=200, *, routing=False):
    content = (f'<a class="back" href="/#models-heading">← Models</a><header class="page-title"><h1>{escape(title)}</h1></header>'
               + notice_html(message, status) + form)
    return send_editor(handler, content, status, routing=routing)


def send_editor(handler, content, status, *, routing=False):
    script, digest = editor_script(routing)
    html = layout(content + f'<script>{script}</script>', server=handler.server)
    return send_html(handler, html, status, script_hash=digest)


@cache
def editor_script(routing):
    scripts = ["broker-routing.js", "instance-form.js"] if routing else ["instance-form.js"]
    script = "\n".join(Path(__file__).with_name(name).read_text(encoding="utf-8") for name in scripts)
    return script, b64encode(sha256(script.encode()).digest()).decode("ascii")


def broker_page(handler, key="", *, message="", status=200, submitted=None):
    server = handler.server
    config = server.data / "config.yml"
    raw = config.read_bytes()
    revision = config_revision(config, raw)
    settings = yaml.safe_load(raw)
    assistant = settings.get("assistant", {})
    broker = assistant.get("modelBrokers", {}).get(key, {})
    if key and not broker:
        return page(handler, "This broker no longer exists.", 404)
    fields = submitted or broker_form.values_for(key, broker, assistant.get("defaultModel"))
    if submitted is None and not key and not assistant.get("modelProfiles") and not assistant.get("modelBrokers"):
        fields["default"] = "on"
    choices = {k: m["label"] for k, m in server.grants.visible_models().items()}
    choices.update({k: m["label"] for k, m in assistant.get("modelProfiles", {}).items()})
    form = broker_form.render_broker(fields, choices, revision)
    if key and any(task["strategy"] == "routed" for task in broker["tasks"].values()):
        try:
            prompt = broker["router"]["prompt"]
            _, _, _, content, stamp = broker_form.prompt_files(config, prompt)
            if not content.strip() and status == 200:
                message = "Save a routing prompt below before using this broker."
            variables = ", ".join("{{" + v + "}}" for v in sorted(broker_form.BROKER_ROUTING_VARIABLES))
            prompt_field = form_field("content", prompt, "Markdown template sent to this broker’s router when it chooses a worker. Use the available variables below.", kind="textarea", attrs='required rows="8"', value=content)
            form += f'''<form class="panel profile-editor" method="post" action="/broker-prompt">
<h2>Routing prompt</h2>{prompt_field}
<p class="hint">Available variables: {escape(variables)}</p>
<input type="hidden" name="profile" value="{escape(key, quote=True)}"><input type="hidden" name="revision" value="{revision}">
<input type="hidden" name="promptRevision" value="{stamp}"><footer><button class="ld-button">Save prompt</button></footer></form>'''
        except (ValueError, OSError) as error:
            message = str(error) if isinstance(error, FormError) else "Check the local routing prompt files."
            status = 400
    return editor_page(handler, "Edit broker" if key else "Add broker", form, message, status, routing=True)


def instance_page(handler, key, message="", status=200):
    server = handler.server
    model = server.grants.visible_models().get(key)
    if not model:
        return page(handler, "Reconnect your LODEON tab to load its available models.", 409)
    private = server.data / PRIVATE_SETTINGS
    revision = config_revision(private, private.read_bytes())
    form = render_instance(model, server.models.instance_settings.get(key, {}), revision)
    return editor_page(handler, model["label"], form, message, status)


def removal_page(handler, group, key):
    section, noun = PERSONAL_SECTIONS[group]
    config = handler.server.data / "config.yml"
    raw = config.read_bytes()
    settings = yaml.safe_load(raw)
    assistant = settings.get("assistant", {})
    revision = config_revision(config, raw)
    item = assistant.get(section, {}).get(key)
    if item is None:
        return page(handler, f"This personal {noun} no longer exists.", 404)
    label = item.get("label") or key
    dependencies = dependent_brokers(assistant, key) if group == "models" else []
    if dependencies:
        links = "".join(f'<li><a href="/brokers/edit/{quote(name, safe="")}">{escape(broker.get("label") or name)}</a></li>'
                        for name, broker in assistant["modelBrokers"].items() if name in dependencies)
        content = f'<div class="panel profile-editor"><p>Remove this model from the following brokers first.</p><ul>{links}</ul><a class="ld-button" href="/">Back to models</a></div>'
    else:
        default = " This also clears your personal default." if assistant.get("defaultModel") == key else ""
        files = "Routing prompt files stay in this folder." if group == "brokers" else "Provider keys stay in the local keys file."
        content = f'''<form method="post" action="/{group}/remove" class="panel profile-editor">
<p>Remove <strong>{escape(label)}</strong> ({escape(key)}) from your personal configuration?{default} {files}</p>
<input type="hidden" name="revision" value="{revision}"><input type="hidden" name="profile" value="{escape(key, quote=True)}">
<footer><button class="ld-button danger">Remove {noun}</button><a class="ld-button" href="/">Cancel</a></footer></form>'''
    return editor_page(handler, f"Remove {noun}", content)


def model_get(handler):
    url = urlsplit(handler.path)
    for group in PERSONAL_SECTIONS:
        prefix = f"/{group}/remove/"
        if url.path.startswith(prefix):
            return removal_page(handler, group, url.path.removeprefix(prefix))
    if url.path == "/brokers/new":
        return broker_page(handler)
    if url.path.startswith("/brokers/edit/"):
        return broker_page(handler, url.path.removeprefix("/brokers/edit/"),
                           message="Saved. Reconnect your LODEON tab to use these changes." if url.query == "saved" else "")
    if url.path.startswith("/instance-models/edit/"):
        return instance_page(handler, url.path.removeprefix("/instance-models/edit/"),
                             "Settings saved. Reconnect your LODEON tab to apply them." if url.query == "saved" else "")
    if url.path == "/models/new":
        return model_page(handler)
    if url.path.startswith("/models/edit/"):
        message = {"saved=model": "Model saved. Reconnect your LODEON tab to refresh its model list.",
                   "saved=key": "API key saved locally."}.get(url.query, "")
        return model_page(handler, url.path.removeprefix("/models/edit/"), message=message)
    return page(handler, "Model page not found.", 404)


def send_html(handler, html, status=200, *, script_hash=None):
    body = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-LODEON-Customizer", "desktop")
    theme_hash = b64encode(sha256(shell_assets()["theme_script"].encode()).digest()).decode("ascii")
    script_policy = f"; script-src 'sha256-{theme_hash}'"
    if script_hash:
        script_policy += f" 'sha256-{script_hash}'"
    handler.send_header("Content-Security-Policy", "default-src 'none'; img-src data:; style-src 'unsafe-inline'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'" + script_policy)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def page(handler, message="", status=200):
    config = handler.server.data / "config.yml"
    try:
        contents = yaml.safe_load(config.read_bytes())
        if not isinstance(contents, dict):
            raise yaml.YAMLError()
        models_html = model_list(contents)
    except (OSError, ConfigError, yaml.YAMLError):
        models_html = ""
        message, status = "Check the structure of the local config.yml file.", 400
    notice = notice_html(message or handler.server.folder_warning, 409 if handler.server.folder_warning else status)
    installed = handler.server.grants.visible_models()
    remote = "".join(
        f'<div class="model model-entry"><div><div class="model-title">{escape(item["label"])}</div>'
        f'<small>Instance · {escape(PROVIDERS[item["provider"]])}</small></div>'
        f'<a class="ld-button" href="/instance-models/edit/{quote(key, safe="")}" aria-label="Edit settings for {escape(item["label"], quote=True)}">Edit settings</a></div>'
        for key, item in sorted(installed.items(), key=lambda pair: pair[1]["label"].casefold())
    )
    folder_form = template("folder.html").substitute(
        folder_field=form_field("folder", "Package folder", "Choose a package folder or enter its absolute path. An empty folder starts a new package.",
                                value=str(config.parent) if not handler.server.folder_warning else ""),
        current=escape(str(config.parent), quote=True),
        folder_action="Use folder" if handler.server.folder_warning else "Reload configuration")
    if handler.server.folder_warning:
        content = ('<header class="page-title"><h1>LODEON Customizer</h1></header>' + notice +
                   '<section class="panel"><div class="panel-head"><h2>Local package</h2></div>' + folder_form + '</section>')
        return send_html(handler, layout(content, server=handler.server), status)
    manifest = config.parent / "lodeon.package.yml"
    try:
        package = read_manifest(manifest)
        metadata = (form_field("packageId", "Package ID", "Unique ID in the instance package registry.", value=package.package_id, attrs="required")
                    + form_field("version", "Version", "Version recorded in the package manifest.", value=package.version, attrs="required"))
        manifest_form = (f'<form class="panel-body package-metadata" method="post" action="/package">{metadata}'
                         f'<input type="hidden" name="revision" value="{config_revision(manifest, manifest.read_bytes())}">'
                         '<button class="ld-button">Save package</button></form>')
    except (OSError, ConfigError):
        manifest_form = notice_html("Check lodeon.package.yml and reload the configuration.", 400)
    content = template("settings.html").substitute(
        models_icon=icon("m12 3 9 5-9 5-9-5z M3 12l9 5 9-5 M3 16l9 5 9-5"),
        folder_icon=icon("M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"),
        notice=notice,
        instance_models=remote or '<p class="panel-body">Connect your LODEON tab, then refresh this list to see its available models.</p>',
        models=models_html, folder_form=folder_form, manifest_form=manifest_form,
    )
    send_html(handler, layout(content, server=handler.server), status)


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
    if server.folder_warning and handler.path != "/folder":
        return page(handler, status=409)
    if (handler.headers.get_content_type() != "application/x-www-form-urlencoded"
        or "Transfer-Encoding" in handler.headers or len(handler.headers.get_all("Content-Length", [])) != 1):
        raise ValueError("invalid_request")
    size = int(handler.headers["Content-Length"])
    is_model = handler.path == "/model"
    if not 0 < size <= (65536 if handler.path in {"/model", "/broker", "/broker-prompt"} else 8192):
        raise ValueError("invalid_request")
    expected = {"/models/remove": {"profile", "revision"}, "/brokers/remove": {"profile", "revision"},
                "/broker": broker_form.FIELDS, "/broker-prompt": {"profile", "revision", "promptRevision", "content"},
                "/instance-model": {"profile", "revision", "temperature", "topP"}, "/folder": {"folder", "method", "current"}, "/package": {"packageId", "version", "revision"}, "/instance": {"instance", "revision"}, "/model": FIELDS,
                "/model-key": {"profile", "revision", "keyRevision", "secret"}}[handler.path]
    parsed = parse_qs(handler.rfile.read(size).decode("utf-8"), strict_parsing=True,
                      keep_blank_values=True, max_num_fields=None if handler.path == "/broker" else len(expected))
    if handler.path == "/broker":
        # The field names are public profile IDs. The resolver validates every submitted member.
        members = []
        for field in list(parsed):
            prefix, _, key = field.partition(".")
            if prefix == "member" and broker_form.ID.fullmatch(key):
                if parsed.pop(field) != ["on"]:
                    raise ValueError("invalid_request")
                hint = parsed.get("hint." + key, [""])[0].strip()
                if "\r" in hint or "\n" in hint:
                    raise ValueError("invalid_request")
                members.append(f"{key} | {hint}")
        for field in list(parsed):
            if field.startswith("hint.") and broker_form.ID.fullmatch(field[5:]) and len(parsed[field]) == 1:
                del parsed[field]
        if members and len(parsed.get("members", [])) == 1:
            parsed["members"] = ["\n".join([*members, parsed["members"][0]])]
    required = expected - {"default"}
    if not required <= parsed.keys() <= expected or any(len(v) != 1 for v in parsed.values()):
        raise ValueError("invalid_request")
    fields = {name: values[0] for name, values in parsed.items()}
    if handler.path == "/folder" and fields["method"] not in {"browse", "load"}:
        raise ValueError("invalid_request")
    if handler.path == "/folder" and fields["method"] == "browse":
        try:
            fields["folder"] = pick_folder()
        except (OSError, ConfigError):
            return page(handler, "Enter the absolute folder path below.", 400)
        if not fields["folder"]:
            return page(handler)
    with server.settings_lock:
        config = server.data / "config.yml"
        private = server.data / PRIVATE_SETTINGS

        def check_private(candidate):
            return LocalModels.load(config, server.identity, private_path=candidate)

        def check(path):
            return LocalModels.load(path, server.identity)

        try:
            if handler.path == "/folder":
                if str(server.data) != fields["current"]:
                    raise ConfigError("config_changed")
                reloaded = open_folder(server, fields["folder"])
                message = "Configuration reloaded from disk." if reloaded else "Package folder selected."
                return page(handler, message + " Reconnect your LODEON tab.")
            if handler.path == "/package":
                update_settings(server.data / "lodeon.package.yml", fields["revision"], read_manifest,
                                lambda doc: doc.update(id=fields["packageId"].strip(), version=fields["version"].strip()))
                return page(handler, "Package details saved.")
            if handler.path == "/instance":
                server.set_models(save_instance(private, fields["instance"].strip(), fields["revision"], check_private))
                return page(handler, "Instance saved.")
            if handler.path in ("/models/remove", "/brokers/remove"):
                group = handler.path.split("/")[1]
                section, noun = PERSONAL_SECTIONS[group]
                server.set_models(remove_profile(config, section, fields["profile"], fields["revision"], check))
                location = f"/?removed={noun}"
            elif handler.path == "/instance-model":
                key = fields["profile"]
                if key not in server.grants.visible_models():
                    return page(handler, "Reconnect your LODEON tab to load its available models.", 409)
                saved = save_sampling(private, fields, server.models, check_private)
                server.models.instance_settings = saved.instance_settings
                location = f"/instance-models/edit/{quote(key, safe='')}?saved"
            elif handler.path == "/broker":
                key, models = broker_form.save_broker(config, fields, check)
                server.set_models(models)
                location = f"/brokers/edit/{quote(key, safe='')}?saved"
            elif handler.path == "/broker-prompt":
                key = fields["profile"]
                broker = server.models.brokers.get(key)
                if (not broker or config_revision(config, config.read_bytes()) != fields["revision"]
                        or not any(t["strategy"] == "routed" for t in broker["tasks"].values())):
                    raise ConfigError("config_changed")
                broker_form.save_prompt(config, broker["router"]["prompt"], fields["content"], fields["promptRevision"])
                server.set_models(check(config))
                location = f"/brokers/edit/{quote(key, safe='')}?saved"
            elif is_model:
                key, models = save_model(config, fields, check)
                server.set_models(models)
                location = f"/models/edit/{quote(key, safe='')}?saved=model"
            else:
                key = fields["profile"]
                save_key(config, fields)
                location = f"/models/edit/{quote(key, safe='')}?saved=key"
        except (ValueError, OSError) as error:
            if isinstance(error, ConfigError) and str(error) == "config_changed":
                return page(handler, "The configuration changed. Reopen the model or instance settings before saving again.", 409)
            if handler.path == "/folder":
                message = ("Enter the absolute folder path below." if str(error) == "folder_picker_unavailable"
                           else "Choose an accessible folder containing valid Customizer settings, or a folder for new settings.")
                return page(handler, message, 400)
            if isinstance(error, ConfigError) and str(error) == "invalid_instance":
                return page(handler, "Enter an HTTPS instance URL, or use HTTP on localhost, "
                            "127.0.0.1 or [::1]. Include the deployment path and omit credentials, "
                            "query parameters and fragments.", 400)
            message = str(error) if isinstance(error, FormError) else "Check the submitted settings and the local configuration."
            if handler.path == "/broker":
                return broker_page(handler, fields["original"], message=message, status=400, submitted=fields)
            if handler.path == "/instance-model":
                return instance_page(handler, fields["profile"], message, 400)
            if is_model:
                return model_page(handler, fields["original"], message=message, status=400, submitted=fields)
            if handler.path == "/model-key":
                return model_page(handler, fields["profile"], message=message, status=400)
            return page(handler, message, 400)
    handler.send_response(303)
    handler.send_header("Location", location)
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", "0")
    handler.end_headers()
