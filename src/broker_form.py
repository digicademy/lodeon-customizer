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
from .form_fields import DEFAULT_HELP, field_help, form_field
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
        if not workers:
            raise FormError(f"Assign {'a worker' if strategy == 'fixed' else 'at least one candidate'} to {task} before saving.")
        if strategy == "fixed":
            if len(workers) > 1:
                raise FormError(f"Choose one fixed worker for {task}.")
            target["model"] = workers[0]
        else:
            target["candidates"] = workers
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
    def field(name, label, explanation, **options):
        return form_field(name, label, explanation, value=form.get(name, ""), **options)

    current = {}
    for line in form["members"].splitlines():
        key, _, hint = line.partition("|")
        if key.strip():
            current[key.strip()] = hint.strip()
    rows_by_id = {**{k: choices.get(k, k) for k in current if ID.fullmatch(k)}, **choices}
    member_fields = []
    for key, label in rows_by_id.items():
        name = escape(key, quote=True)
        attrs = f'data-model-name="{escape(label, quote=True)}"' + (" checked" if key in current else "")
        member = form_field("member." + key, label, f"Make {key} available for assignment to this broker’s tasks.",
                            kind="checkbox", attrs=attrs)
        hint = form_field("hint." + key, "Routing hint", f"Tell the router when to choose {label}. For example, use this model for SPARQL queries.",
                          value=current.get(key, ""), attrs='placeholder="What does this model do well?"')
        member_fields.append(f'<div class="member-row">{member}<div class="member-hint">{hint}</div></div>')
    manual = "\n".join(f"{k} | {v}" for k, v in current.items() if k not in rows_by_id)
    options = "".join(f'<option value="{escape(k, quote=True)}">{escape(v)}</option>' for k,v in choices.items())
    rows = []
    for task in TASKS:
        routed = form[f"{task}-strategy"] == "routed"
        zones = []
        for role, label in (("workers", "Candidates" if routed else "Worker"), ("fallbacks", "Fallbacks")):
            zone_id = f"{task}-{role}"
            explanation = ("If the selected model fails, try these models in the order shown." if role == "fallbacks" else
                           "Assign one worker for a fixed task or the models the router may choose from for a routed task.")
            zones.append(f'''<div class="route-zone" data-role="{role}" role="group" aria-labelledby="{zone_id}-title" aria-describedby="help-{zone_id}">
<div class="zone-heading"><div class="field-caption"><strong id="{zone_id}-title">{label}</strong>{field_help(zone_id, task + " " + role, explanation)}</div><button type="button" data-assign hidden>Assign</button></div>
<div class="route-chips" data-assignments></div>
<label data-manual>{label} IDs<input name="{zone_id}" aria-describedby="help-{zone_id}" value="{escape(str(form[zone_id]), quote=True)}" list="member-ids"></label></div>''')
        strategy = form_field(f"{task}-strategy", "Strategy", "Fixed always uses the assigned worker. Routed asks the router to choose among the assigned candidates.",
                              value=form[f"{task}-strategy"], options={"fixed": "Fixed", "routed": "Routed"})
        rows.append(f'''<fieldset class="task-row" data-task="{task}"><legend>{task.capitalize()}</legend>
<div class="strategy">{strategy}</div>
<div class="task-zones">{"".join(zones)}</div></fieldset>''')
    identity = (field("label", "Display name", "Name shown in the Assistant model selector.", attrs="required") +
                field("id", "Broker ID", "Stable configuration ID. Leave blank to derive it from the display name.",
                      attrs="readonly" if form["original"] else 'placeholder="Generated from display name"') +
                field("description", "Description", "Describe when someone should select this broker.", kind="textarea", wide=True, attrs='rows="4"'))
    router = (field("router", "Router model", "Member that chooses among candidates for routed tasks. An empty value uses the first member as router.", attrs='list="member-ids" placeholder="First member"') +
              field("prompt", "Routing prompt ID", "Identifies the local Markdown routing prompt. Save the broker to edit that prompt.", attrs='placeholder="Assigned from broker ID"') +
              field("objective", "Routing objective", "Tell the router what to prioritise when choosing a candidate, for example query accuracy or response time.", kind="textarea", wide=True, attrs='rows="3" required'))
    manual_field = form_field("members", "Other members", "Use one line per model, with its ID and routing hint separated by |. Connect a LODEON tab to select available instance models by name.",
                              kind="textarea", value=manual, attrs='rows="3" placeholder="model-id | Routing hint"')
    default = field("default", "Use as my default model", DEFAULT_HELP, kind="checkbox", attrs="checked" if form.get("default") == "on" else "")
    return f'''<form class="panel profile-editor" method="post" action="/broker">
<input type="hidden" name="revision" value="{revision}"><input type="hidden" name="original" value="{escape(form["original"], quote=True)}">
<datalist id="member-ids">{options}</datalist>
<fieldset><legend>Broker profile</legend><div class="fields">{identity}</div>{default}</fieldset>
<fieldset class="broker-members"><legend>Broker members</legend>{"".join(member_fields)}
<details class="disclosure" {"open" if manual or not rows_by_id else ""}><summary>Enter model IDs manually</summary>{manual_field}</details></fieldset>
<fieldset><legend>Router</legend><div class="fields">{router}</div></fieldset>
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
