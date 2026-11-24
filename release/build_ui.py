"""Compile the desktop assets with the selected Core editor's pinned frontend tools."""

import hashlib
import json
import os
import shutil
import subprocess


def build_ui(core, root, work, python):
    editor = core / "editor"
    work.mkdir(parents=True, exist_ok=True)
    # Node is a build tool. The packaged desktop app contains the compiled files.
    env = {**os.environ, "PATH": str(python.parent) + os.pathsep + os.environ["PATH"]}
    npm = shutil.which("npm", path=str(python.parent))
    if not npm:
        subprocess.run([python, "-m", "pip", "install", "--disable-pip-version-check",
                        "nodejs-wheel==22.20.0"], check=True)
        npm = shutil.which("npm", path=str(python.parent))
        if not npm:
            raise RuntimeError("npm is missing from the Customizer build environment")

    # npm ci uses Core's lock, with only the packages required to render the desktop UI.
    lock_bytes = (editor / "package-lock.json").read_bytes()
    packages = json.loads(lock_bytes)["packages"]
    tools = ("@tailwindcss/postcss", "@tailwindcss/typography", "esbuild", "lucide", "postcss", "tailwindcss")
    deps = {name: packages["node_modules/" + name]["version"] for name in tools}
    source = json.loads((editor / "package.json").read_bytes())
    manifest = json.dumps({"private": True, "type": "module", "dependencies": deps,
                           "overrides": source.get("overrides", {})}, sort_keys=True)
    signature = hashlib.sha256(lock_bytes + manifest.encode()).hexdigest()
    stamp = work / "installed"
    if not (work / "node_modules").is_dir() or not stamp.exists() or stamp.read_text() != signature:
        stamp.unlink(missing_ok=True)
        (work / "package.json").write_text(manifest, encoding="utf-8")
        (work / "package-lock.json").write_bytes(lock_bytes)
        subprocess.run([npm, "ci", "--no-audit", "--no-fund", "--ignore-scripts"], cwd=work, env=env, check=True)
        stamp.write_text(signature, encoding="ascii")

    (work / "src/ui").mkdir(parents=True, exist_ok=True)
    for path in ("tailwind.config.js", "postcss.config.js", "src/styles.css", "src/ui/theme.ts", "src/ui/icons.ts"):
        shutil.copyfile(editor / path, work / path)
    shutil.copyfile(root / "src/desktop-theme.ts", work / "src/desktop-theme.ts")
    shutil.copyfile(root / "release/compile-ui.mjs", work / "compile-ui.mjs")
    assets = work / "compiled"
    assets.mkdir(exist_ok=True)
    subprocess.run(["node", "compile-ui.mjs", root / "src/desktop.css", assets], cwd=work, env=env, check=True)
    return assets
