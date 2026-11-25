"""Accessible controls shared by the local settings forms."""

from html import escape


def field_help(name, label, explanation):
    return (f'<details class="field-help"><summary aria-label="Help for {escape(label, quote=True)}">'
            '<svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round">'
            '<circle cx="12" cy="12" r="9"/><path d="M12 11v5m0-9v.1"/></svg></summary>'
            f'<p id="help-{escape(name, quote=True)}">{escape(explanation)}</p></details>')


def form_field(name, label, explanation, *, value="", kind="text", options=None,
               attrs="", wide=False, note=""):
    key = escape(name, quote=True)
    caption = escape(label)
    descriptions = f"help-{key} note-{key}" if note else f"help-{key}"
    control = f'id="field-{key}" name="{key}" aria-describedby="{descriptions}"'
    current = str(value)
    if kind == "checkbox":
        check = f'<input type="checkbox" {control} {attrs}>'
        heading = f'<label class="check" for="field-{key}">{check}{caption}</label>'
        element = ""
    else:
        heading = f'<label for="field-{key}">{caption}</label>'
        if options is not None:
            choices = "".join(f'<option value="{escape(k, quote=True)}"{" selected" if current == k else ""}>{escape(v)}</option>'
                              for k, v in options.items())
            element = f'<select class="ld-metadata-input" {control} {attrs}>{choices}</select>'
        elif kind == "textarea":
            element = f'<textarea class="ld-metadata-input ld-metadata-textarea" {control} {attrs}>{escape(current)}</textarea>'
        else:
            element = f'<input class="ld-metadata-input" type="{kind}" {control} value="{escape(current, quote=True)}" {attrs}>'
    hint = f'<small id="note-{key}">{escape(note)}</small>' if note else ""
    return (f'<div class="field{" wide" if wide else ""}"><div class="field-caption">{heading}'
            f'{field_help(name, label, explanation)}</div>{element}{hint}</div>')


DEFAULT_HELP = "Select this target when connecting and when installing this package. The first target is preselected. A package without a default needs an instance package that supplies one."
TEMPERATURE_HELP = "Lower values favour more predictable wording. Higher values allow more variation."
TOP_P_HELP = "Limit selection to the most likely tokens whose cumulative probability reaches this value. A value of 1 keeps the full distribution."
