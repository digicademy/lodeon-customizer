# LODEON Customizer

**LODEON Customizer** is a user-controlled local component for sensitive
data and explicitly authorized connections to compatible running LODEON
instances. It runs as a small local service, initially delivered through Docker,
without requiring a complete local LODEON instance.

Sensitive data belongs to the local Customizer. A running LODEON application
links a connection through Settings and receives only the public information
and operation results that this connection permits. Connecting does not merge
the instance's configuration with the local secret store or expose its contents.

**Current status.** The local catalog command and Python model executor use the
pinned Core runtime. A local Ollama model has completed a call from the standalone
image. The HTTP relay, production pairing and Settings action are pending.
The [roadmap](ROADMAP.md) records the checks against the [v1 protocol](PROTOCOL.md).

## Planned user setup

Download the release's `docker-compose.yml` and run `docker compose up -d`.
Compose will pull the prebuilt GitLab Registry image and mount `./data/`.
On the first start the Customizer will initialize `data/config.yml` from its
Package configuration. Subsequent starts and updates will keep the user's file.
Model credentials will be optional and read locally from `data/models/.env`.

The planned small local UI will save model definitions, brokers and the
default directly to the same `data/config.yml` used for manual edits. For
example, changing a model's temperature will update its existing
`assistant.modelProfiles` entry. Replacing a key will update its value in
`data/models/.env`. The hosted Settings dialog pairs with this service.
The [roadmap](ROADMAP.md#local-setup-and-configuration-editing) records the
approved file layout and ownership.

## Developer check for the current prototype

Produce the wheel once from the LODEON Core checkout. Use an empty wheelhouse
directory. Anyone who already has the pinned wheel can start at the second command.

```sh
docker build -f api/Dockerfile --target model-runtime-wheel \
  --output type=local,dest=/tmp/lodeon-wheelhouse .
```

From the Customizer checkout, build the CLI and inspect the example profile.
The image build verifies the wheel against `runtime.lock`. Catalog inspection
performs no inference.

```sh
docker build --build-context model_runtime=/tmp/lodeon-wheelhouse -t lodeon-customizer .
docker run --rm --network=none -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  lodeon-customizer catalog --config /examples/ollama.yml \
  --service-id 866af3ff-f622-48e6-8660-25e10bac2fec
```

The UUID above is an example. Generate one UUID for your service
(`python3 -c 'import uuid; print(uuid.uuid4())'`) and reuse it across starts.
The public target combines this UUID and your YAML profile ID. Each load creates
a fresh catalog revision, including when private configuration changes.

Supply your own file with a read-only bind mount and pass its container path
to `--config`. The accepted root is `assistant.modelProfiles`. Instance
settings such as `defaultModel`, Brokers or KG sections are rejected. Two
examples show [Ollama](examples/ollama.yml) and a
[native keyed provider](examples/anthropic.yml). For the latter, set
`PERSONAL_ANTHROPIC_API_KEY` in your local environment and pass its name with
`docker run -e PERSONAL_ANTHROPIC_API_KEY …`. Keep personal files outside the
image. The build context admits only the two distributed example files as YAML.

| Profile data | Treatment |
| --- | --- |
| Profile ID, label, optional description, provider, generation, prompt caching, optional limits and cost | Public catalog fields. Choose labels and descriptions suitable for disclosure to a connected instance. |
| Native model ID, endpoint, Ollama settings and provider credential | Private execution inputs. Environment references resolve on the user's machine or in the local container. Missing referenced values stop configuration loading. |
| `access.allowedGroups` | A nonempty instance group restriction is rejected. Local origin and model grants are a separate boundary. |

For an actual Ollama call from Docker Desktop, use the host address from the
example without `--network=none`. The CLI available at this stage inspects
catalogs. The Python executor accepts prepared model calls from trusted local
code. The browser transport will add origin, grant and operation checks.

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
