"""Publish the reviewed desktop downloads for an existing GitLab tag."""

import hashlib
import json
import os
import tomllib
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


def public_digest(url):
    try:
        with urlopen(url, timeout=120) as response:
            return hashlib.file_digest(response, "sha256").digest()
    except HTTPError as error:
        if error.code != 404:
            raise
        return None


def publish():
    project = f"{os.environ['CI_API_V4_URL']}/projects/{os.environ['CI_PROJECT_ID']}"
    tag = os.environ["CI_COMMIT_TAG"]
    version = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    if tag.removeprefix("v") != version:
        raise ValueError(f"Release tag {tag} must match the app version {version}")
    registry = f"{project}/packages/generic/lodeon-customizer/{version}"
    targets = {
        "Windows · x64": "windows-x86_64.zip",
        "macOS · Apple silicon": "macos-arm64.zip",
        "macOS · Intel": "macos-x86_64.zip",
        "Linux · x64": "linux-x86_64.tar.gz",
        "Linux · ARM64": "linux-arm64.tar.gz",
    }
    files = {label: f"LODEON-Customizer-{version}-{suffix}" for label, suffix in targets.items()}
    files.update({"SHA256 checksums": "SHA256SUMS", "Core revision": "CORE-REVISION"})

    def send(request):
        request.add_unredirected_header("JOB-TOKEN", os.environ["CI_JOB_TOKEN"])
        return urlopen(request, timeout=300)

    links = []
    for label, filename in files.items():
        path = Path("dist") / filename
        url = f"{registry}/{filename}"
        with path.open("rb") as stream:
            expected = hashlib.file_digest(stream, "sha256").digest()
            actual = public_digest(url)
            if actual is None:
                stream.seek(0)
                upload = Request(url, data=stream, method="PUT", headers={
                    "Content-Type": "application/octet-stream", "Content-Length": str(path.stat().st_size),
                })
                with send(upload):
                    pass
                actual = public_digest(url)
            if actual != expected:
                raise ValueError(f"Public download differs from the accepted file: {filename}")
        links.append({"name": label, "url": url, "link_type": "package"})

    release_url = f"{project}/releases/{quote(tag, safe='')}"
    try:
        with urlopen(release_url, timeout=30) as response:
            release = json.load(response)
    except HTTPError as error:
        if error.code != 404:
            raise
        guide = "https://adwmainz.pages.gitlab.rlp.net/digicademy/lodeon/lodeon-documentation/user-guide/customizer/"
        payload = {"tag_name": tag, "name": f"LODEON Customizer {version}",
                   "description": f"Choose the download for your computer below. [Setup and user guide]({guide}).",
                   "assets": {"links": links}}
        with send(Request(f"{project}/releases", data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"})):
            pass
        with urlopen(release_url, timeout=30) as response:
            release = json.load(response)
    published = {(link["name"], link["url"]) for link in release["assets"]["links"]}
    if any((link["name"], link["url"]) not in published for link in links):
        raise ValueError(f"Public GitLab release {tag} is missing accepted download links")
    print(f"Verified public release {tag} with {len(links)} downloads.")


if __name__ == "__main__":
    publish()
