"""Public instance model information and private, per-instance sampling settings."""

from html import escape
import re

from resolver.configuration_schema import validate_instance_model_settings
from resolver.errors import ConfigResolverError

from .configuration import update_settings
from .model_form import FormError, PROVIDERS


def read_catalog(body):
    if not isinstance(body, dict) or set(body) != {"models"} or not isinstance(body["models"], list):
        raise ValueError("invalid_request")
    models = {}
    for item in body["models"]:
        if not isinstance(item, dict) or set(item) != {"id", "label", "provider", "sampling"}:
            raise ValueError("invalid_request")
        key = item["id"]
        if (not isinstance(key, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", key)
                or key in models or not isinstance(item["label"], str) or not item["label"].strip()
                or item["provider"] not in PROVIDERS):
            raise ValueError("invalid_request")
        try:
            validate_instance_model_settings({key: item["sampling"]})
        except ConfigResolverError:
            raise ValueError("invalid_request") from None
        models[key] = item
    return models


def render_instance(model, overrides, revision):
    key = escape(model["id"], quote=True)
    fields = []
    for name, label, minimum, maximum in (("temperature", "Temperature", "0", "2"), ("topP", "Top P", "0.000001", "1")):
        inherited = model["sampling"].get(name, "Provider default")
        value = escape(str(overrides.get(name, "")), quote=True)
        fields.append(f'<label>{label}<input type="number" step="any" min="{minimum}" max="{maximum}" '
                      f'name="{name}" value="{value}" placeholder="{inherited}"><small>Instance setting: {inherited}</small></label>')
    return f'''<form class="panel profile-editor" action="/instance-model" method="post">
<input type="hidden" name="profile" value="{key}"><input type="hidden" name="revision" value="{revision}">
<p>{escape(PROVIDERS[model["provider"]])} · {key}</p><div class="fields">{"".join(fields)}</div>
<p class="hint">Leave a field empty to inherit the instance setting. This model runs on the connected instance.</p>
<footer><button class="primary">Save settings</button><a href="/">Back to settings</a></footer></form>'''


def save_sampling(config, form, models, check):
    key = form["profile"]
    try:
        patch = {k: float(form[k]) for k in ("temperature", "topP") if form[k].strip()}
        validate_instance_model_settings({key: patch})
    except (ValueError, ConfigResolverError):
        raise FormError("Enter a temperature from 0 to 2 and Top P from 0.000001 to 1.") from None

    def edit(doc):
        instances = doc.setdefault("instanceModelSettings", {})
        settings = instances.setdefault(models.instance, {})
        if patch:
            settings[key] = patch
        else:
            settings.pop(key, None)
            if not settings:
                del instances[models.instance]
            if not instances:
                del doc["instanceModelSettings"]
    return update_settings(config, form["revision"], check, edit)
