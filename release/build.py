"""Build, archive and exercise the native desktop app using one coordinated Core source."""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path
from venv import EnvBuilder

from smoke import check_archive

ROOT = Path(__file__).resolve().parents[1]
NAME = "LODEON Customizer"
SYSTEM = {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}[platform.system()]
MACHINE = platform.machine().lower()
ARCH = {"amd64": "x86_64", "aarch64": "arm64"}.get(MACHINE, MACHINE)


def run(*args, **kwargs):
    subprocess.run(list(map(str, args)), check=True, **kwargs)


def build(core, work, output, release):
    work.mkdir(parents=True, exist_ok=True)
    venv = work / "venv"
    if not (venv / "pyvenv.cfg").exists():
        EnvBuilder(with_pip=True).create(venv)
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    env = {**os.environ, "LODEON_CORE_ROOT": str(core), "LODEON_CUSTOMIZER_ROOT": str(ROOT),
           "PYTHONPATH": str(core / "config"), "LITELLM_LOCAL_MODEL_COST_MAP": "True"}
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
        run(python, "-m", "pip", "install", "--disable-pip-version-check", runtime, package,
            "pyinstaller==6.22.3")
        run(python, "-m", "pip", "check")
        run(python, "-m", "unittest", "discover", "-s", ROOT / "checks", env=env)
        dist = stage / "dist"
        flags = []
        if release and SYSTEM == "macos":
            flags += ["--codesign-identity", os.environ["MACOS_SIGN_IDENTITY"]]
        if SYSTEM == "macos":
            flags += ["--osx-bundle-identifier", "org.lodeon.customizer"]
        run(python, "-m", "PyInstaller", "--noconfirm", "--onedir", "--windowed", "--name", NAME,
            "--distpath", dist, "--workpath", stage / "work", "--specpath", stage,
            "--paths", core / "config", "--collect-data", "lodeon_model_runtime",
            "--collect-data", "litellm", "--recursive-copy-metadata", "litellm",
            "--collect-submodules", "tiktoken_ext",
            "--add-data", f"{core / 'config/config.yml'}:resources/core",
            "--add-data", f"{ROOT / 'config.yml'}:resources/package",
            "--add-data", f"{ROOT / 'lodeon.package.yml'}:resources/package",
            "--add-data", f"{core / 'LICENSE'}:resources/core",
            *flags, ROOT / "release/launch.py", env=env)
        label = f"LODEON-Customizer-{version}-{SYSTEM}-{ARCH}"
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
        check_archive(archive, stage / "Acceptance with spaces", SYSTEM)
        output.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archive, output / archive.name)
        print(f"Verified {output / archive.name}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=os.environ.get("LODEON_CORE_ROOT", ROOT.parent.parent))
    parser.add_argument("--work", type=Path, default=ROOT / "build")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--release", action="store_true", default=bool(os.environ.get("CI_COMMIT_TAG")))
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        parser.error("Use native CPython 3.12 to build the desktop app.")
    expected = os.environ.get("DESKTOP_TARGET")
    if expected and expected != f"{SYSTEM}-{ARCH}":
        parser.error(f"Expected {expected}, running on {SYSTEM}-{ARCH}")
    print(f"Building on {platform.platform()} with Python {platform.python_version()}", flush=True)
    build(args.core.resolve(), args.work.resolve(), args.output.resolve(), args.release)
