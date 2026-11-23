# LODEON Customizer Roadmap

Implementation requested on 2026-11-22. The Step 1 browser check is complete
for individual model offers. The published Step 2 image passed anonymous pulls
on both platforms and a fresh Compose start. Public delivery of the standalone
Compose file is still open. The [Step 3 proposal](PROTOCOL.md#step-3-proposal-for-review)
on broker policies and the connected user's default is ready for review. This is
the authoritative feature plan in the user-created lodeon-customizer repository. It owns all seven
coordinated review steps, including component delivery and Core integration.

LODEON Customizer is the fixed product/component name. Its first release
provides personal model connections; its longer-term role is a user-controlled
home for sensitive data and explicitly granted operations. Broader capabilities
are recorded as direction, not as permission to implement them in this release.
After every step, report actual changes, focused verification, limitations and
the next step. Planning is not implementation evidence.

## Release Scope

A user starts an optional local Docker model service, configures personal
models through the existing model-profile YAML structure and supplies secrets
locally. In a compatible LODEON instance, **Settings → Connect personal
models** explicitly connects that service. Its approved model offers appear
alongside installed targets. Both Ollama and personal hosted-provider access
are included. No separate Editor, KG service or renderer runs locally.

```text
LODEON backend <-> browser <-> LODEON Customizer <-> provider or Ollama
  orchestration     relay       profiles/credentials     model inference
  tools/evidence
```

The browser relays individual model invocations and results. The backend keeps
prompt composition, task dispatch, the Tool Loop, Query handoff, SPARQL/MCP,
Follow-Ups, proposals and the mandatory final Answer Stage. The local service
executes model calls only. Model computation can be local without making the
server-orchestrated conversation private from the instance operator.

Personal brokers may combine local and instance model profiles from the first
release. The local management UI is part of the design from the outset.
Git transfer, hosted project parameter-editing forms, a browser secret vault,
multiple simultaneous service connections in one tab, provider token streaming
and a general runtime Package/plugin loader are outside this release.
Installed Brokers and Virtual Models retain their current behavior. Personal
targets require a client with the browser relay.

## Component Ownership And Future Scope

**LODEON Customizer** is the fixed component name. This user-created repository
owns the component, its complete feature plan and all seven review steps.
Generic Core interface decisions stay in the independent lodeon-roadmap
repository; that repository does not duplicate Customizer delivery progress.

The Customizer is a small user-controlled local service for sensitive data and
explicitly authorized connections. Personal models are its first capability,
not its permanent product boundary. Future capability types may include Git
access and other sensitive user data. Each needs a typed operation and a
separate disclosure/permission contract; a model grant never implicitly grants
Git writes or access to unrelated data. No generic secret-read API is planned.

Future Git integration may use the user's local Customizer for credentials
and provider operations. The LODEON instance backend remains excluded from Git
credentials and transfer. This refines the earlier browser-only wording: the
user-controlled side may include both browser and Customizer. The exact Git
transport remains a future decision and is not implemented in this release.

The Customizer reuses one pinned Core-owned model execution artifact for
profile validation, provider adapters and completion normalization. Step 1
fixes the delivery boundary; Step 2 provides it without copying provider code.
Core does not depend on this optional repository. A complete local LODEON
instance is not required. Docker/model setup and operational evidence belong
here, not in a second model-only repository.

## Binding Contracts

### Local Setup And Configuration Editing

- Distribute a single `docker-compose.yml` that starts the prebuilt image from
  the GitLab Container Registry with `docker compose up -d`. Each release
  tag contains both `linux/amd64` and `linux/arm64`. Build its wheel
  from the current Core revision for that release. The user needs neither
  repository to start the service.
- Ship a regular LODEON Package with `lodeon.package.yml` and a root
  `config.yml`. On first start, create `data/` beside the Compose file and
  initialize `data/config.yml` from the packaged configuration only if absent.
  The service can start with zero models and zero keys. Restarts and image
  updates preserve an existing file.
- Compose mounts `data/`. The model capability reads `data/models/.env`
  directly when keys are needed. Model definitions refer to keys with the
  existing `apiKeyEnv` field. A key can be changed for subsequent calls
  without recreating the container. The entire personal `data/` directory
  stays out of version control and image builds.
- The text editor and the small local Customizer UI share one editable file,
  `data/config.yml`, and the Core Package resolver and schema. Saving a model,
  broker or default in the UI updates that file directly. A save must retain
  unrelated YAML settings and detect intervening file edits before replacing
  them. Invalid edits leave the last valid configuration available. Rotating
  a key under the same name updates only the model credentials file. The UI
  can show whether a key is configured without returning its stored value.
- The local UI owns configuration edits. Hosted **Settings → Connect personal
  models** owns pairing and selection. A model invocation grant conveys no
  administrative rights. Keep the shared connection service separate from the
  models capability so future capabilities can own their credentials and grants.

### Configuration And Target Identity

- Local YAML uses the existing model-profile contract, including provider,
  model, endpoint, generation, caching and optional description/cost settings.
  Personal model credentials resolve in the local model capability.
  No remote instance secret names, paths or configuration are resolved locally.
- The local service advertises a strict public catalog, never its raw YAML,
  credentials, environment-variable names or administrative configuration.
- Personal target references have an explicit origin and stable identity;
  installed and personal targets cannot collide or replace each other by id
  or label. Catalog composition is not Package/YAML composition.
- The backend explicitly permits delegation through an owned configuration
  contract and the existing authorization policy. Delegation cannot enable a
  disabled Assistant, bypass KG restrictions or enlarge operator resource
  limits. Core rechecks direct access to each instance model before a personal
  broker invokes it as router, worker or fallback. Local grants control
  personal targets. As in Core with authentication disabled, a local profile's
  `access.allowedGroups` is valid YAML and supplies no local authorization.
- A personal target works with zero installed models, without fabricating an
  installed default model. The Connect action remains reachable in that state.
- On connection, sort personal and instance targets alphabetically by display
  label. Select an available Customizer `assistant.defaultModel` immediately
  for the connected user. Project references do not contain the local service
  address, pairing grant, provider endpoint or credentials.

### Two Independent Trust Boundaries

- Pairing with the local service requires explicit local approval of an exact
  LODEON origin. A one-time, locally issued pairing credential may be used.
  No wildcard-origin access, port scanning or
  automatic connection on project import is introduced.
- Provider keys stay in the user-controlled service and go only to the locally
  configured provider. Neither the hosted frontend nor its backend receives
  them. Local pairing grants remain between browser and local service.
- Backend invocation exchange is separately bound to the initiating browser
  operation and its existing authentication context. Correlation ids are not
  authorization. Isolation is required even when instance login is disabled;
  opaque short-lived operation capabilities must not enter traces or projects.
  They protect this transient exchange; they do not authenticate users or grant
  access beyond the existing central model/KG authorization policy.
- The service checks model identity, allowed origin, execution limits and
  permitted request fields. A browser invocation cannot override the configured
  endpoint, read secrets, administer profiles or issue arbitrary HTTP requests.
- The threat guarantee concerns the remote instance operator, not an attacker
  controlling the user's OS or local service image. A permitted origin may
  attempt to abuse invocation authority; local revocation and call/token bounds
  remain necessary. Key confidentiality is not conversation confidentiality.

### Invocation And Lifecycle

- One provider-neutral invocation carries the selected target, existing task,
  complete prepared messages, offered Tools, effective supported generation
  settings and the request's execution bounds. It contains no provider secret.
- Preserve the existing task vocabulary and phase owners. Probe and Suggestions
  use the same execution transport without being relabelled as chat turns.
- The backend receives a validated normalized completion: text, structured Tool
  calls, finish reason, safe errors and available usage. It applies the same
  Tool validation and authorization as for hosted execution.
- Extend the existing HTTP/request lifecycle and gateway boundary. Prefer a
  bounded pending-call exchange compatible with the current HTTP stack; freeze
  the exact transport in Step 1. No ASGI rewrite, durable job database, generic
  event bus, second orchestration state machine or alternate Tool Loop.
- Bind each invocation/result to its operation, connection and call. Duplicate,
  stale, wrong-owner and post-cancellation submissions cannot resume execution
  or cause the same local invocation to be executed again.
- Timeout, cancellation, disconnect, tab close, logout and process restart
  terminate or expire outstanding work. Provider cancellation is best effort
  where supported; a late response never revives the operation. An already
  submitted provider request may still incur charges. No automatic replay of
  an ambiguously completed provider request is allowed.
- Connection loss is an explicit error, never a silent switch to an installed
  model or operator key. Catalog changes cannot retarget an in-flight call.

## Seven Reviewable Steps

### Step 1 — Freeze The Protocol And Verify Browser Feasibility

**Deliverables:** a small versioned contract for catalog, pairing/grant,
invocation, completion, error and cancellation; a field-level data-flow table;
canonical target identity, operator permission and anonymous-operation isolation
rules; the exact shared-runtime delivery boundary and HTTP relay design.

Use a minimal loopback counterpart to check real HTTPS-origin-to-local-service
communication before building the runtime. Cover CORS, Host/Origin checks,
local-network permission and mixed-content behavior. Record actual browser
versions and results against the supported-browser baseline. Any proposed
browser limitation is explicit, not an undisclosed reduction of acceptance.
Do not disable browser security or use an instance proxy as a workaround.

**Review:** inspect every transmitted field and the recorded successful browser
connection. Demonstrate that an unapproved origin cannot pair or invoke. The
prototype is intermediate evidence, not the completed feature.

**Result, 2026-11-23.** The [v1 protocol](PROTOCOL.md) freezes the public
fields, the two independent credentials used after pairing, the HTTP exchange
and the pinned Core wheel. The [browser check](checks/browser-connection.cjs)
loads two real public HTTPS origins with ordinary certificate validation. In
a fresh test context it pairs from `https://example.com`, reads one synthetic
model offer, then attempts to reuse the ticket. The browser sends only
preflights from the second origin, `https://example.org`, for both pairing
and invocation. No provider is configured. The fixture listens on an ephemeral
IPv4 loopback port and closes when the check finishes.

| Browser tested | Local transport | Observed result |
| --- | --- | --- |
| Chrome for Testing 158.0.8127.36, headless macOS | HTTP | Initial loopback permission was `prompt`. With permission denied no request reached the listener. After the per-origin grant, pairing and catalog returned 200. |
| Brave 1.100.58, Chromium 158.0.8127.42, headless macOS | HTTP | Same denial and success, with the engine reporting the permission state. |
| Playwright Firefox 142.0.1, Linux | HTTP | Pairing and catalog returned 200 in the default context. |
| Playwright WebKit 26.0, Linux | HTTP | Fetch failed with “Not allowed to request resource”. The listener saw no request. |
| Same WebKit build | HTTPS | Pairing and catalog returned 200 using a certificate for `127.0.0.1` signed by a CA trusted only inside the disposable container. |

Each successful run observed 403 on ticket reuse and both foreign preflights.
Direct requests with a valid grant and a foreign, null or absent Origin were
rejected. HTTP runs also checked rejection of an unexpected Host. Chromium
permission changes used the browser's per-origin permission API in a disposable
context. The visual permission dialog was not exercised. No grant, certificate
or setting was installed in the user's normal browser profile.

Core uses real Chromium for smoke checks and documents the CSS floor as Chrome
111+, Firefox 128+ and Safari 16.4+. The measurements above are specific to
these builds. Linux WebKit is not a Safari or iOS acceptance run, and the
oldest supported releases were not tested. Keep trusted loopback HTTPS as an
explicit option and explain browser refusal in Settings. Where the browser
blocks the network request, JavaScript may only see a generic fetch failure.
Chrome documents the separate [local network access permission](https://developer.chrome.com/blog/local-network-access).

To reproduce the Firefox check from the Customizer checkout using Core's
existing Playwright 1.56.1 test image:

```sh
docker run --rm --user pwuser -e NODE_PATH=/playwright/node_modules \
  -v "$PWD/checks:/checks:ro" lodeon-playwright-audio:1.56.1 \
  node /checks/browser-connection.cjs firefox
```

Use `webkit` in the same image for the HTTP comparison. For the TLS check,
supply `CHECK_CERT` and `CHECK_KEY` for a loopback certificate whose IP SAN
is `127.0.0.1`. Trust its issuing CA in the disposable browser environment
and set `NODE_EXTRA_CA_CERTS` there for the direct Node checks. For a native
Chromium with the current loopback permission API, run
`node checks/browser-connection.cjs chromium` with Node 22+, Playwright Core
on the module path and `CHROMIUM_PATH` pointing to the executable.

### Step 2 — Provide The Shared Runtime And Customizer Foundation

Separate only what is needed at the existing model gateway to reuse profile
validation, native provider preparation and completion normalization. Publish
one pinned, consumable Core runtime boundary for the independent companion;
keep orchestration and trace ownership in Core and preserve ordinary execution.

Freeze the public catalog projection, supported profile-field treatment and
strict result schemas. Secrets and raw provider exceptions are excluded before
they reach a browser/remote exchange. Resolve how local and operator execution
bounds combine, display restrictions and reject incompatible settings without
silent parameter rewriting. Do not change installed-model semantics.

Deliver the Package, registry image, Compose startup and local files described
above. Replace the prototype examples and restricted loader with the canonical
Package configuration and resolver. Check first start from the Compose file
alone and restart with a pre-existing personal configuration. Review the
local UI save flow against those same files.

**Review:** focused existing provider/gateway tests pass; a neutral consumer can
load the artifact, validate an Ollama and keyed-provider profile, and produce a
normalized completion without copying provider code. Inspect a sentinel-secret
projection. Customizer implementation and operational progress are recorded
here.

**Local delivery check, 2026-11-23.** The Core build target supplied the wheel
for the versioned Customizer image. Starting from the single Compose file
created the personal configuration and service identity. Recreating the
container preserved both files byte for byte and served the local landing
page. The unchanged models-production configuration produced eleven offers.
All 28 Core schema tests and four Customizer checks passed, including key
rotation from disk. The local configuration editor and hosted pairing are pending.

The release build installs the Python modules directly from `src/`.
The locally built `0.1.0` image index contains `linux/amd64` and `linux/arm64`.
The installed catalog command and all four offline Customizer checks passed
on each image. Docker Desktop ran the AMD64 variant on an ARM64 host.

**Published release check, 2026-11-23.** GitLab served tag `0.1.0` anonymously
with image index `sha256:16929fcd16db37b14d98fdc72865dc54049e873e081de23e6d5d16dcec548b1f`.
A client without credentials downloaded both platform manifests and all 25
distinct config and layer blobs (291,951,750 bytes) and verified their SHA-256
digests and sizes. Docker ran the published AMD64 catalog on the ARM64 host.
On ARM64, Compose pulled the tag with an isolated credential-free Docker
configuration and started from a fresh directory containing only the checkout's
`docker-compose.yml`. The loopback page returned HTTP 200, the catalog was
empty, and the service created the packaged configuration, a valid service ID
and the model directory without any credentials.

At the time of this check the public GitLab `main` branch contained only
`README.md` and `ROADMAP.md`. The raw Compose download returned HTTP 404.
Once the Compose file is published, verify its anonymous download against
the file used for this successful startup.

**Earlier prototype evidence, 2026-11-23.** The production Core API installs wheel 0.1.0 and
loads its adapters from site-packages. The independent Customizer image
consumes the same wheel through the SHA-256 in `runtime.lock`. Its local
CLI reads `assistant.modelProfiles`, resolves local environment references
and returns the v1 allowlisted catalog. Schema and runtime checks reject
incompatible generation settings and call bounds before provider execution.
Turn-level policy and grant-wide reservations belong to Step 3.

The 70 focused Core gateway, provider, profile and application-composition
tests pass. Four offline Customizer tests cover catalog filtering, configuration
rejection, keyed request preparation, normalized native Tool calls, safe errors
and limits. A native Anthropic HTTP fixture received one request with the
synthetic key and echoed it in a 401 response. The executor returned only
`assistant.model.credentials_rejected`. Captured diagnostics and the public
catalog contained no test key. In a separate live check the standalone image sent
one bounded request to the already installed Ollama model `gemma4:12b`. Its
normalized answer was `Ready`, finish reason `stop`, with 23 input and 38 output
tokens. This exercises local execution. Browser delegation and the full
SPARQL/Answer workflow have separate acceptance steps.

The broader Core API run passed 660 of 661 tests. The pre-existing
`test_assistant_status_exposes_only_safe_ui_flags` still expects three initial
image previews. Core's committed configuration specifies twelve.

### Step 3 — Implement The Backend Delegation Transport

Review the broker/default additions to the individual-model protocol before
implementing them. At connection time resolve mixed broker members against
local grants and directly authorized instance model profiles. An unresolved
or ambiguous member makes the affected broker unavailable. Implement the
request-local exchange at the existing gateway with bounded transient state,
owner validation, single-use result correlation and cleanup. Reuse current
phase/cancellation services; retain no completed-call database or server-side
personal profile registry.

Resolve public personal targets only for the authorized requesting operation.
The backend never connects to the user's localhost or accepts personal provider
keys. Add coded localized errors and enforce operator/KG policy independently
of anything reported by the browser.

Implement the corresponding restricted Customizer execution boundary with
locally approved exact origins, scoped pairing grants, revocation and local
call/token bounds. Validate Host/Origin and reject endpoint injection,
secret/configuration reads and administrative operations from the hosted app.
Filter credential-bearing provider diagnostics before any response or log.

**Review:** a neutral browser counterpart completes a request. A second user,
anonymous tab or wrong operation cannot read its model input or submit its
result. Duplicate, expired and cancelled replies are rejected. Ordinary
installed-model requests and protected graph access retain their behavior.

### Step 4 — Add Connect Personal Models And Catalog Composition

Use the existing hosted Settings/menu/modal patterns for service address,
pairing, connection status and disconnect. Local editing belongs to the
Customizer. Store active grants in tab memory, separate from project data.
Reconnection requires local approval. A compatible service/protocol is checked
before its public catalog is accepted. Connecting/catalog discovery performs
no model inference.

Compose installed and personal targets in the existing selector and Model
information view, with unambiguous source, combined alphabetical ordering
and immediate application of an available personal default.
Retain a stable personal selection in the project contract without a grant or
service address. Only one personal service is connected per tab initially;
separate tabs/origins have independently scoped connections. The action must
work when the instance has no installed models and remain unavailable when the
operator disables this capability.

Document startup and pairing for the Compose service delivered in Step 2.
Publish ports on loopback only; require no Docker socket, privileged container
or operator tunnel. Document host Ollama reachability and supported browser
permissions. Keep local secret inputs out of version control and generic logs.
Make configuration reload and connection revocation behavior explicit; a new
vault or persistent administrative database is not part of this first release.

To review the proposed local UI, change a model's temperature, save, and
inspect its existing profile in `data/config.yml`. Then edit that value by
hand and reopen the form. It must show the value from the file.

**Review:** pair, inspect/select an actual local offer, disconnect and reconnect.
Verify same-label collision handling, zero-installed-model operation, keyboard
and narrow-layout usability, policy rejection and absence of secrets in
browser-visible catalogs and saved projects. Customizer startup and pairing
are reviewed from this repository.

### Step 5 — Complete The Existing Assistant Workflow Through Delegation

Wire chat, mandatory Query handoff, retries, proposals and the tool-free final
Answer call through the same delegated model boundary. Native structured Tool
requests return to Core; Core executes the authorized SPARQL/MCP request and
supplies canonical evidence to the next delegated call. Complete Probe and
Suggestions through their existing owners. No domain-specific repair prompts,
limit increases or changes to existing follow-up decisions.

Connection/catalog identity must participate in probe-cache applicability;
one user's or an earlier connection's successful probe cannot certify another.
Use the existing Core broker dispatcher for personal mixed brokers. Verify a
personal broker using a local worker and an authorized instance worker, and
the denial of an instance member the user cannot select directly.

**Review:** a real local Ollama model completes a question, structured query
handoff, real Core-executed SPARQL result and final answer. A controlled native
keyed-provider fixture verifies the same transport and secret boundary without
paid inference. Check explicit Probe, Suggestions and a normal Node proposal
using the same established workflows. Model quality failures are recorded as
such, not repaired with new Core heuristics.

### Step 6 — Verify Provenance, Persistence And Failure Boundaries

Reuse existing model-call provenance, usage, readable trace/report preparation
and kept-chat structures. Record personal execution origin without connection
secrets, count each model invocation once and keep relay traffic out of Tool
counts. Metrics reported by the companion are not independently verified
provider billing; missing values stay unknown. Preserve per-task attribution.

Exercise project reload and ZIP import/export: selected personal references and
historical evidence survive, live grants and service addresses do not travel.
Unavailable references remain visible and require explicit reconnection or
model selection. Import never pairs, invokes or silently substitutes a model.

**Review:** inspect a representative readable report and actual ZIP roundtrip.
Check disconnect during a call, local service stop, timeout, duplicate/late
reply and logout/revocation. Inspect both sides' errors/logs and Core artifacts
for a controlled sentinel secret. No new secret is supplied for these checks.

### Step 7 — Consolidated Acceptance, Documentation And Closure

Run one bounded final acceptance from committed, unchanged Core, Documentation,
Roadmap and Customizer inputs; record revisions and statuses before/after using
strictly read-only Git commands with optional index refresh disabled.
Complete the applicable central suite and relevant dependency/image security
checks once, with required rebuilds for changed dependencies or images.
Customizer checks remain repository-owned. Do not repeat full acceptance at
every step or introduce a new test platform.

Use a real browser connection, actual local Docker service and Ollama for the
complete backend–browser–local-model–SPARQL–final-answer workflow, including an
instance with zero installed models. Verify a controlled keyed-provider path,
connection lifecycle and project ZIP roundtrip. Check that Core starts and
works without the optional service and that existing installed models and
headless Virtual Models retain their contracts. No paid provider campaign or
automatic model downloads are included.

Synchronize Core operational instructions, actual human-facing Documentation
and this roadmap; reference the Customizer's own delivery evidence. Mark each
repository's actual outcome, including unresolved browser/model limitations.
Closure requires the complete workflow, not only protocol/unit tests or a
manually assembled intermediate path. Only humans create repositories, write
Git state, commit, merge and deploy.

## Efficiency And Scope Control

Reuse focused tests while developing; add cases only for new invariants or
observed defects. Retain one neutral protocol counterpart and a small
deterministic provider fixture. No broad model matrix, benchmark campaign,
semantic judge, new Broker policies or unrelated refactoring. After each step,
report the changed behavior, relevant check results, remaining limitations and
the next step. Do not claim unexecuted acceptance or silently broaden scope.

The broader concept baseline in the independent lodeon-roadmap repository,
assistant-project-settings-personal-models-and-git.md, continues to record the
settings and Git boundaries. This plan supersedes its original personal-key
handling for the selected release scope only. The corresponding generic Core
interface is recorded there in assistant-personal-model-delegation.md.

Preserve the existing Core Model Task, Query Handoff, mandatory Answer Stage,
Configuration and Access Control contracts except for the explicitly agreed
generic extensions. Their canonical records remain in lodeon-roadmap; this
repository does not duplicate them or introduce a second implementation plan.
