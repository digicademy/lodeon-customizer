"""Select a local settings directory without copying credentials between folders."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID

from .configuration import ConfigError, initialize
from .profiles import LocalModels


def pick_folder():
    if sys.platform == "darwin":
        command = ["osascript", "-e", 'POSIX path of (choose folder with prompt "Choose a LODEON settings folder")']
    elif os.name == "nt":
        command = ["powershell.exe", "-NoProfile", "-STA", "-Command",
                   "Add-Type -AssemblyName System.Windows.Forms; "
                   "$d = New-Object Windows.Forms.FolderBrowserDialog; "
                   "if ($d.ShowDialog() -eq 'OK') { [Console]::OutputEncoding = [Text.Encoding]::UTF8; "
                   "[Console]::WriteLine($d.SelectedPath) }"]
    elif shutil.which("zenity"):
        command = ["zenity", "--file-selection", "--directory", "--title=Choose a LODEON settings folder"]
    elif shutil.which("kdialog"):
        command = ["kdialog", "--getexistingdirectory"]
    else:
        raise ConfigError("folder_picker_unavailable")
    result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace")
    return result.stdout.rstrip("\r\n") if result.returncode == 0 else ""


def load_folder(data):
    data = data.resolve()
    if ".git" in {part.casefold() for part in data.parts}:
        raise ConfigError("folder_invalid")
    for name in ("config.yml", ".service-id", "models", "models/.env"):
        if (data / name).is_symlink():
            raise ConfigError("folder_invalid")
    config = data / "config.yml"
    if config.exists() and not ((data / ".service-id").is_file() and (data / "models").is_dir()):
        # Validate the owner's existing YAML before creating a new identity or files.
        LocalModels.load(config, UUID(int=0))
    identity = initialize(data)
    return identity, LocalModels.load(config, identity)


def open_folder(server, value):
    data = Path(value).expanduser()
    if not value or not data.is_absolute() or not data.is_dir():
        raise ConfigError("folder_invalid")
    data = data.resolve()
    identity, models = load_folder(data)
    if server.folder_preference:
        preference = server.folder_preference
        preference.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=preference.parent, delete=False) as pending:
            pending.write(os.fsencode(data))
        candidate = Path(pending.name)
        try:
            candidate.replace(preference)
        finally:
            candidate.unlink(missing_ok=True)
    server.data, server.identity = data, identity
    server.set_models(models)
    server.folder_warning = ""
