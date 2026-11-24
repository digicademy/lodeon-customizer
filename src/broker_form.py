"""Local forms for canonical Assistant broker policies and their routing prompts."""

import hashlib
import re
from html import escape
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from resolver.configuration_schema import validate_delegated_broker
from resolver.errors import ConfigResolverError
from resolver.resource_schemas import BROKER_ROUTING_VARIABLES, valid_broker_routing_prompt, validate_prompt_registry
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .configuration import ConfigError, config_revision, load_configuration, update_settings
from .model_form import FormError


TASKS = ("plan", "query", "retry", "propose", "answer", "probe", "suggest")
FIELDS = {"revision", "original", "id", "label", "description", "default", "members",
          "router", "prompt", "objective"} | {f"{task}-{k}" for task in TASKS for k in ("strategy", "workers", "fallbacks")}
ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")


def values_for(key, broker, default):
    router = broker.get("router", {})
    values = dict(id=key, original=key, label=broker.get("label", ""), description=broker.get("description", ""),
                  default="on" if key and default == key else "", router=router.get("model", ""),
                  prompt=router.get("prompt", ""), objective=router.get("objective", ""),
                  members="\n".join(f"{k} | {v['routingHint']}" for k, v in broker.get("members", {}).items()))
    for task in TASKS:
        policy = broker.get("tasks", {}).get(task, {})
        values[f"{task}-strategy"] = policy.get("strategy", "fixed")
        values[f"{task}-workers"] = policy.get("model") or ", ".join(policy.get("candidates", []))
        values[f"{task}-fallbacks"] = ", ".join(policy.get("fallbacks", []))
    return values


def save_broker(config, form, check):
    key = form["id"].strip() or re.sub(r"[^a-z0-9]+", "-", form["label"].lower()).strip("-")
    if not ID.fullmatch(key) or (form["original"] and key != form["original"]):
        raise FormError("Choose a stable profile ID starting with a letter.")
    members = {}
    for line in form["members"].splitlines():
        if not line.strip():
            continue
        name, _, hint = line.partition("|")
        name = name.strip()
        if not ID.fullmatch(name) or name in members:
            raise FormError("Use one distinct model ID per member line.")
        members[name] = {"routingHint": hint.strip() or name}
    if not members or not form["label"].strip():
        raise FormError("Enter a broker name and at least one member.")
    router = form["router"].strip() or next(iter(members))
    policy = {"label": form["label"].strip(), "members": members, "tasks": {},
              "router": {"model": router, "objective": form["objective"].strip(),
                         "prompt": form["prompt"].strip() or f"{key}-routing"}}
    if not ID.fullmatch(policy["router"]["prompt"]):
        raise FormError("Choose a routing prompt ID starting with a letter.")
    if form["description"].strip():
        policy["description"] = form["description"].strip()
    for task in TASKS:
        strategy = form[f"{task}-strategy"]
        workers = [x.strip() for x in form[f"{task}-workers"].split(",") if x.strip()]
        target = {"strategy": strategy, "fallbacks": [x.strip() for x in form[f"{task}-fallbacks"].split(",") if x.strip()]}
        if strategy == "fixed":
            if len(workers) > 1:
                raise FormError(f"Choose one fixed worker for {task}.")
            target["model"] = workers[0] if workers else router
        else:
            target["candidates"] = workers or list(members)
        policy["tasks"][task] = target
    try:
        validate_delegated_broker(policy)
    except ConfigResolverError as error:
        raise FormError(f"Check {error.variables.get('path', 'the broker settings')} ({error.variables.get('reason', 'invalid value')}).") from None

    def edit(settings):
        assistant = settings.setdefault("assistant", {})
        brokers = assistant.setdefault("modelBrokers", {})
        if form["original"] and key not in brokers:
            raise ConfigError("config_changed")
        if not form["original"] and (key in brokers or key in assistant.get("modelProfiles", {})):
            raise FormError("That profile ID is already in use.")
        entry = brokers.setdefault(key, {})
        if "description" not in policy:
            entry.pop("description", None)
        entry.update(policy)
        if form.get("default") == "on":
            assistant["defaultModel"] = key
        elif assistant.get("defaultModel") == key:
            assistant.pop("defaultModel")
    return key, update_settings(config, form["revision"], check, edit)


def render_broker(form, choices, revision):
    def value(name):
        return escape(str(form.get(name, "")), quote=True)
    current = {}
    for line in form["members"].splitlines():
        key, _, hint = line.partition("|")
        if key.strip():
            current[key.strip()] = hint.strip()
    rows_by_id = {**{k: choices.get(k, k) for k in current if ID.fullmatch(k)}, **choices}
    member_fields = []
    for key, label in rows_by_id.items():
        name = escape(key, quote=True)
        hint = escape(current.get(key, ""), quote=True)
        member_fields.append(f'''<div class="member-row"><label class="check"><input type="checkbox" data-model-name="{escape(label, quote=True)}" name="member.{name}" {"checked" if key in current else ""}>
{escape(label)} <small>{name}</small></label><label>Routing hint<input name="hint.{name}" value="{hint}" placeholder="What this model does well"></label></div>''')
    manual = "\n".join(f"{k} | {v}" for k, v in current.items() if k not in rows_by_id)
    options = "".join(f'<option value="{escape(k, quote=True)}">{escape(v)}</option>' for k,v in choices.items())
    rows = []
    for task in TASKS:
        routed = form[f"{task}-strategy"] == "routed"
        zones = []
        for role, label in (("workers", "Candidates" if routed else "Worker"), ("fallbacks", "Fallbacks")):
            field = f"{task}-{role}"
            zones.append(f'''<div class="route-zone" data-role="{role}" role="group" aria-labelledby="{field}-title">
<div class="zone-heading"><strong id="{field}-title">{label}</strong><button type="button" data-assign hidden>Assign</button></div>
<div class="route-chips" data-assignments></div>
<label data-manual>{label} IDs<input name="{field}" value="{value(field)}" list="member-ids"></label></div>''')
        rows.append(f'''<fieldset class="task-row" data-task="{task}"><legend>{task.capitalize()}</legend>
<label class="strategy">Strategy<select name="{task}-strategy"><option value="fixed">Fixed</option><option value="routed" {"selected" if routed else ""}>Routed</option></select></label>
<div class="task-zones">{"".join(zones)}</div></fieldset>''')
    return f'''<form class="panel profile-editor" method="post" action="/broker">
<input type="hidden" name="revision" value="{revision}"><input type="hidden" name="original" value="{value("original")}">
<datalist id="member-ids">{options}</datalist>
<div class="fields"><label>Display name<input name="label" required value="{value("label")}"></label>
<label>Broker ID<input name="id" {"readonly" if form["original"] else ""} value="{value("id")}" placeholder="Generated from display name"></label>
<label>Description<textarea name="description">{value("description")}</textarea></label>

<label>Router model<input name="router" list="member-ids" value="{value("router")}" placeholder="First member"></label>
<label>Routing objective<input required name="objective" value="{value("objective")}"></label>
<label>Routing prompt ID<input name="prompt" value="{value("prompt")}" placeholder="Assigned from broker ID"></label></div>
<fieldset class="broker-members"><legend>Broker members</legend>{"".join(member_fields)}
<details {"open" if manual or not rows_by_id else ""}><summary>Enter model IDs manually</summary>
<label>Other members<textarea rows="2" name="members" placeholder="model-id | Routing hint">{escape(manual)}</textarea></label>
<p class="hint">Use one line per model. Connect your LODEON tab to select available instance models by name.</p></details></fieldset>
<label class="check"><input type="checkbox" name="default" {"checked" if form.get("default")=="on" else ""}>Use as my default model</label>
<section class="task-routing" aria-labelledby="task-routing-heading"><h2 id="task-routing-heading">Task routing</h2>
<div class="member-palette" data-pool hidden><h3>Selected models</h3>
<p class="hint">Drag a model into a task, or select it and choose Assign. Drag an assignment back here to remove it.</p>
<div class="route-chips" data-palette></div></div>
<p class="sr-only" aria-live="polite" data-routing-status></p>
{"".join(rows)}</section>
<footer><button class="primary">Save broker</button><a href="/">Back to settings</a></footer></form>'''


def _local_path(root, relative, extensions):
    path = (root / relative).resolve()
    if path.suffix not in extensions or path == (root / "config.yml").resolve() or root.resolve() not in path.parents or ".git" in {part.casefold() for part in path.relative_to(root.resolve()).parts}:
        raise FormError("Use a prompt path inside the settings folder.")
    return path


def prompt_files(config, prompt):
    if not ID.fullmatch(prompt):
        raise FormError("Choose a valid routing prompt ID.")
    registry = _local_path(config.parent, load_configuration(config)["assistant"]["promptRegistryFile"], {".yml", ".yaml"})
    raw = registry.read_bytes() if registry.exists() else b""
    try:
        doc = YAML().load(raw.decode()) if raw else {"schemaVersion": 1, "prompts": {}, "chains": {}}
        validate_prompt_registry({**doc, "chains": {}})
    except (ConfigResolverError, TypeError, ValueError, YAMLError):
        raise FormError("Check the local prompt registry.") from None
    entry = doc["prompts"].get(prompt)
    if entry and not BROKER_ROUTING_VARIABLES.issubset(entry["variables"]):
        raise FormError("This prompt ID is already used by a different kind of prompt.")
    target = _local_path(config.parent, registry.parent / (entry["file"] if entry else f"broker/{prompt}.md"), {".md"})
    content = target.read_bytes() if target.is_file() else b""
    if not entry and target.exists():
        raise FormError("An unregistered file already uses this prompt path. Choose another prompt ID.")
    stamp = hashlib.sha256(raw).digest() + hashlib.sha256(content).digest()
    return registry, doc, target, content.decode("utf-8"), config_revision(target, stamp)


def _write(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        stream.write(contents.encode())
    temp = Path(stream.name)
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def save_prompt(config, prompt, content, revision):
    registry, doc, target, _, stamp = prompt_files(config, prompt)
    if stamp != revision:
        raise ConfigError("config_changed")
    if not valid_broker_routing_prompt(content):
        raise FormError("Enter prompt text using the supported broker variables.")
    if prompt not in doc["prompts"]:
        doc["prompts"][prompt] = {"file": target.relative_to(registry.parent).as_posix(), "variables": sorted(BROKER_ROUTING_VARIABLES)}
        stream = StringIO()
        YAML().dump(doc, stream)
        _write(target, content)
        try:
            _write(registry, stream.getvalue())
        except OSError:
            target.unlink()
            raise
    else:
        _write(target, content)
