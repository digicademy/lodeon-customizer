# LODEON Customizer

**LODEON Customizer** is a user-controlled local component for sensitive
data and explicitly authorized connections to compatible running LODEON
instances. It runs as a small local service, initially delivered through Docker,
without requiring a complete local LODEON instance.

Sensitive data belongs to the local Customizer. A running LODEON application
links a connection through Settings and receives only the public information
and operation results that this connection permits. Connecting does not merge
the instance's configuration with the local secret store or expose its contents.

## Start the Customizer

The release uses a single `docker-compose.yml` and a prebuilt image from the
[project's Container Registry](https://gitlab.rlp.net/adwmainz/digicademy/lodeon/lodeon-customizer/container_registry).
Image tag `0.1.0` supports anonymous pulls on AMD64 and ARM64. Download the
Compose file and start the service from a personal directory:

```sh
curl --fail --location --remote-name https://gitlab.rlp.net/adwmainz/digicademy/lodeon/lodeon-customizer/-/raw/main/docker-compose.yml
docker compose up -d
```

Open the local status page at <http://127.0.0.1:8765/>. On first start
the service creates `data/config.yml` from the root Package configuration.
An existing configuration and the service identity survive container
replacement. Zero configured models is a valid starting point.

Edit `assistant.modelProfiles`, `assistant.modelBrokers` and
`assistant.defaultModel` in `data/config.yml` using the regular LODEON syntax.
Place model keys in `data/models/.env` using `NAME=value` and reference the
name with `apiKeyEnv`. The service reads this file for each model invocation.
Keep this directory private. With rootful Docker on Linux, the files may be
owned by root. Give your local account ownership of the data directory for
manual editing. Use a clean Package checkout for hosted composition, separate
from the personal directory containing the downloaded Compose file.

To inspect the current ordinary model offers locally:

```sh
docker compose exec customizer lodeon-customizer catalog
```

The landing page currently reports service availability. The planned local
editor will update the same `data/config.yml` as manual edits, and will keep
key values in `data/models/.env`. Pairing, broker binding, and the hosted
Settings action are pending. See the [roadmap](ROADMAP.md#local-setup-and-configuration-editing).

## Build the release image

The release tag contains both `linux/amd64` and `linux/arm64`. Compose
selects the matching image automatically. The Python source files live directly
in `src/`. Installing the package provides the `lodeon-customizer` command.

To build and load both variants locally using a multi-platform builder and
a containerd image store, run this from `vendor/lodeon-customizer`:

```sh
docker buildx bake -f docker-bake.hcl --allow=fs.read=../.. --load
```

Bake uses the current Core checkout for both the Core-owned
`model-runtime-wheel` build target and the Package resolver. For a separate
checkout, set `CORE_ROOT` and grant Bake read access to that directory. No
separately downloaded wheel is needed. The local image has the exact name
and version used by Compose.

For publication, an authenticated maintainer can build and push the complete
index directly, then inspect the published platforms:

```sh
docker buildx bake -f docker-bake.hcl --allow=fs.read=../.. --push
docker buildx imagetools inspect registry.gitlab.rlp.net/adwmainz/digicademy/lodeon/lodeon-customizer:0.1.0
```

## First Capability: Personal Models

Users configure models through the existing LODEON model-profile YAML structure
and supply provider keys through local environment/secret inputs. In a
compatible LODEON application, **Settings → Connect personal models** pairs the
browser with the Customizer. The planned selector combines approved personal
and instance models and brokers alphabetically and applies an available
Customizer default immediately for the connected user.

```text
LODEON backend <-> browser <-> LODEON Customizer <-> provider or local Ollama
```

The Customizer resolves the local model configuration and executes individual
model calls. Provider credentials go only to the locally configured provider;
the hosted LODEON frontend and backend receive no personal provider key.

The LODEON backend continues to own orchestration, Tools, SPARQL, Query handoff
and final synthesis. Consequently, local model execution does not make a
server-orchestrated conversation private from that server.

## Common Connection Principle

Each connection is explicitly approved, scoped to a particular LODEON origin
and capability, and revocable. An authorization to invoke a model does not
grant access to unrelated sensitive data or permission to write a Git repository.
The local service performs a defined operation or returns an explicitly
permitted result; it does not offer a general API for reading stored secrets.

Personal model definitions, credentials and connection grants remain separate
from portable Story data. Importing a project cannot establish or broaden a
Customizer connection. A compatible Core integration is required; merely
starting Docker does not modify arbitrary existing LODEON versions.

## Future Scope

Personal models are the first capability, not the permanent scope of the
LODEON Customizer. The same connection principle may later support Git
credentials, Git import/export and other sensitive user data. Each capability
requires its own operation, disclosure and permission contract.

Future Git support may keep credentials and provider operations in the local
Customizer, with the LODEON instance backend excluded from credentials and
transfer. Its exact transport remains a separate decision. Git functionality
and a general-purpose vault are not implemented as part of the first
personal-model release.
