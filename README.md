# LODEON Customizer

**LODEON Customizer** is a planned user-controlled local component for sensitive
data and explicitly authorized connections to compatible running LODEON
instances. It runs as a small local service, initially delivered through Docker,
without requiring a complete local LODEON instance.

Sensitive data belongs to the local Customizer. A running LODEON application
links a connection through Settings and receives only the public information
and operation results that this connection permits. Connecting does not merge
the instance's configuration with the local secret store or expose its contents.

**Current status.** The [v1 protocol](PROTOCOL.md) defines the connection and
model-call exchange. A disposable test service demonstrates pairing and catalog
access from a real HTTPS page. The production service and the Settings action
are still pending. Browser results and review steps are in the
[Customizer roadmap](ROADMAP.md).

## First Capability: Personal Models

Users configure models through the existing LODEON model-profile YAML structure
and supply provider keys through local environment/secret inputs. In a
compatible LODEON application, **Settings → Connect personal models** pairs the
browser with the Customizer. Approved model offers appear in the model selector;
no model/key editing GUI is required for the first release.

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
