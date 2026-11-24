"""Build, archive and exercise the native desktop app using one coordinated Core source."""

import argparse
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path
from venv import EnvBuilder

from smoke import NAME, check_archive

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}[platform.system()]
MACHINE = platform.machine().lower()
ARCH = {"amd64": "x86_64", "aarch64": "arm64"}.get(MACHINE, MACHINE)


def run(*args, **kwargs):
    subprocess.run(list(map(str, args)), check=True, **kwargs)


def local_app_folder(name):
    return name + ".app" if SYSTEM == "macos" else name


def is_customizer_app(path, name):
    if path.is_symlink() or not path.is_dir():
        return False
    if SYSTEM == "macos":
        info = path / "Contents/Info.plist"
        if not info.is_file():
            return False
        try:
            metadata = plistlib.loads(info.read_bytes())
        except (plistlib.InvalidFileException, ValueError):
            return False
        return (isinstance(metadata, dict) and metadata.get("CFBundleIdentifier") == "org.lodeon.customizer"
                and metadata.get("CFBundleExecutable") == name)
    executable = name + ".exe" if SYSTEM == "windows" else name
    return (path / executable).is_file() and (path / "_internal").is_dir()


def publish_local_app(source, output):
    target = output / local_app_folder(NAME)
    if (target.exists() or target.is_symlink()) and not is_customizer_app(target, NAME):
        raise RuntimeError(f"Cannot replace unrelated file at {target}")
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        stage = Path(temporary)
        candidate = stage / "new"
        shutil.move(source, candidate)
        backup = stage / "old"
        if target.exists():
            target.rename(backup)
        try:
            candidate.rename(target)
        except OSError:
            if backup.exists():
                backup.rename(target)
            raise
    return target


def build(core, work, output, channel):
    release = channel == "release"
    work.mkdir(parents=True, exist_ok=True)
    venv = work / "venv"
    if not (venv / "pyvenv.cfg").exists():
        EnvBuilder(with_pip=True).create(venv)
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    with tempfile.TemporaryDirectory(dir=work) as tmp:
        stage = Path(tmp)
        # Stage only public build inputs. In particular, do not traverse personal data.
        runtime = stage / "runtime"
        shutil.copytree(core / "api/lodeon_model_runtime", runtime / "lodeon_model_runtime",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(core / "LICENSE", runtime)
        shutil.copy2(core / "api/pyproject.toml", runtime)
        package = stage / "customizer"
        shutil.copytree(ROOT / "src", package / "src", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(ROOT / "pyproject.toml", package)
        public = stage / "public"
        public.mkdir()
        for filename in ("config.yml", "lodeon.package.yml"):
            shutil.copy2(ROOT / filename, public)
        env = {**os.environ, "LODEON_CORE_ROOT": str(core), "LODEON_CUSTOMIZER_ROOT": str(public),
               "PYTHONPATH": str(core / "config"), "LITELLM_LOCAL_MODEL_COST_MAP": "True"}
        run(python, "-m", "pip", "install", "--disable-pip-version-check", runtime, package,
            "pyinstaller==6.22.3")
        run(python, "-m", "pip", "check")
        run(python, "-m", "unittest", "discover", "-s", ROOT / "checks", env=env)
        dist = stage / "dist"
        flags = []
        icons = core / "editor/public/assets"
        if release and SYSTEM == "macos":
            flags += ["--codesign-identity", os.environ["MACOS_SIGN_IDENTITY"]]
        if SYSTEM == "macos":
            iconset = stage / "Customizer.iconset"
            iconset.mkdir()
            for size in (16, 32, 128, 256, 512):
                for scale, suffix in ((1, ""), (2, "@2x")):
                    run("sips", "-z", size * scale, size * scale, icons / "apple-touch-icon.png",
                        "--out", iconset / f"icon_{size}x{size}{suffix}.png")
            run("iconutil", "-c", "icns", iconset)
            flags += ["--osx-bundle-identifier", "org.lodeon.customizer", "--icon", stage / "Customizer.icns"]
        elif SYSTEM == "windows":
            flags += ["--icon", icons / "favicon.ico"]
        run(python, "-m", "PyInstaller", "--noconfirm", "--onedir", "--windowed", "--name", NAME,
            "--distpath", dist, "--workpath", stage / "work", "--specpath", stage,
            "--paths", core / "config", "--collect-data", "lodeon_model_runtime", "--collect-data", "lodeon_customizer",
            "--collect-data", "litellm", "--recursive-copy-metadata", "litellm",
            "--collect-submodules", "tiktoken_ext",
            "--add-data", f"{core / 'config/config.yml'}:resources/core",
            "--add-data", f"{public}:resources/package",
            "--add-data", f"{core / 'resources/branding'}:resources/branding",
            "--add-data", f"{core / 'LICENSE'}:resources/core",
            *flags, ROOT / "release/launch.py", env=env)
        label = f"LODEON-Customizer-{version if release else channel}-{SYSTEM}-{ARCH}"
        if SYSTEM == "macos":
            bundle = dist / (NAME + ".app")
            archive = stage / (label + ".zip")
            def archive_mac():
                run("ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", bundle, archive)
            archive_mac()
            if release:
                import json
                result = subprocess.check_output([
                    "xcrun", "notarytool", "submit", str(archive), "--wait", "--keychain-profile",
                    os.environ["MACOS_NOTARY_PROFILE"], "--output-format", "json"])
                if json.loads(result)["status"] != "Accepted":
                    raise RuntimeError("macOS notarization failed")
                run("xcrun", "stapler", "staple", bundle)
                run("spctl", "--assess", "--type", "execute", bundle)
                archive.unlink()
                archive_mac()
        elif SYSTEM == "windows":
            if release:
                exe = dist / NAME / (NAME + ".exe")
                run("signtool", "sign", "/fd", "SHA256", "/sha1", os.environ["WINDOWS_SIGN_THUMBPRINT"],
                    "/tr", os.environ["WINDOWS_TIMESTAMP_URL"], "/td", "SHA256", exe)
                run("signtool", "verify", "/pa", exe)
            archive = Path(shutil.make_archive(str(stage / label), "zip", dist, NAME))
        else:
            archive = stage / (label + ".tar.gz")
            with tarfile.open(archive, "w:gz") as out:
                out.add(dist / NAME, arcname=NAME)
        extracted = stage / "Acceptance with spaces"
        check_archive(archive, extracted, SYSTEM)
        output.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output) as temporary:
            pending = Path(temporary) / archive.name
            shutil.copy2(archive, pending)
            if channel == "dev" and not os.environ.get("CI"):
                print(f"App: {publish_local_app(extracted / local_app_folder(NAME), output)}", flush=True)
            pending.replace(output / archive.name)
        print(f"Verified {output / archive.name}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=os.environ.get("LODEON_CORE_ROOT", ROOT.parent.parent))
    parser.add_argument("--work", type=Path, default=ROOT / "build")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    channels = parser.add_mutually_exclusive_group()
    channels.add_argument("--latest", dest="channel", action="store_const", const="latest",
                          help="Build a rolling download for the main branch.")
    channels.add_argument("--release", dest="channel", action="store_const", const="release",
                          help="Build the project version with native release signing.")
    parser.set_defaults(channel="dev")
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        parser.error("Use native CPython 3.12 to build the desktop app.")
    expected = os.environ.get("DESKTOP_TARGET")
    if expected and expected != f"{SYSTEM}-{ARCH}":
        parser.error(f"Expected {expected}, running on {SYSTEM}-{ARCH}")
    print(f"Building on {platform.platform()} with Python {platform.python_version()}", flush=True)
    build(args.core.resolve(), args.work.resolve(), args.output.resolve(), args.channel)
