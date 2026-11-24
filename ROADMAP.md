# LODEON Customizer Roadmap

This repository owns the seven review steps for the Customizer and its Core
integration. The approved delivery architecture is an instance-independent
native desktop app for Windows, macOS and Linux. Desktop packaging supersedes
the container prototype outright. There is no compatibility or migration path.
The local foundation, Core exchange and personal routed prompt delivery are implemented.
Step 4 delivers hosted Settings, catalog composition and portable selection. Step 5 delivers the browser invocation relay. Step 6 verified provenance, project portability and failure handling. Step 7 is next. Desktop release acceptance remains open.

LODEON Customizer is the fixed product/component name. Its first release
provides personal model connections; its longer-term role is a user-controlled
home for sensitive data and explicitly granted operations. Broader capabilities
are recorded as direction, not as permission to implement them in this release.
After every step, report actual changes, focused verification, limitations and
the next step. Planning is not implementation evidence.

## Release Scope

A user opens the desktop app, enters their LODEON instance URL, configures personal
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
instance is not required. Desktop delivery, model setup and operational evidence belong
here, not in a second model-only repository.

## Binding Contracts

### Local Setup And Configuration Editing

- Ship a self-contained native application. The user extracts the matching
  archive and opens the app. It starts a loopback listener, opens the local
  settings page and remembers the full instance URL. HTTPS is required except
  for HTTP on `localhost`, `127.0.0.1` or `[::1]`. Connection grants match the
  saved browser origin, including any non-default port.
- The desktop settings use the Core wordmark and Editor palette in light and
  dark appearances. The native filename is `LODEON-Customizer` with the platform
  extension. A local development build replaces its app in the output folder
  after checking the archive. The default data directory ends in `LODEON-Customizer/data`.
- Retain a regular Package manifest and root `config.yml`. On first launch
  create the per-user `data/config.yml` and stable service identity in the
  OS user-data directory. The owner can select a different folder or reopen an existing configuration. Zero models is valid. Restarts and replacement of
  the app preserve personal files.
- Resolve `apiKeyEnv` from `data/models/.env` at invocation. The packaged
  defaults contain only public configuration. Build, sign and test each
  platform archive in a pipeline from one resolved Core commit. Public
  `latest` requires Customizer `main` and Core `main`. Developers test locally
  against their chosen Core checkout. The release matrix,
  user-data locations and browser review are specified in the [README](README.md).

- The text editor and the small local Customizer UI share one editable file,
  `data/config.yml`, and the Core Package resolver and schema. The local forms save the instance URL and create or edit personal model
  profiles, including the default selection, provider, generation, caching,
  limits and costs. A separate write-only form saves provider keys to
  `data/models/.env`. Forms also edit canonical broker policies and routed Markdown prompts. A save must retain
  unrelated YAML settings and detect intervening file edits before replacing
  them. Invalid edits leave the last valid configuration available. Rotating
  a key under the same name updates only the model credentials file. The UI
  can show whether a key is configured without returning its stored value.
- The local UI owns configuration edits. Hosted **Settings → Connect personal
  models** owns connection and selection. A model invocation grant conveys no
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
  address, connection grant, provider endpoint or credentials.

### Two Independent Trust Boundaries

- The local user enters the instance URL. Only that origin may request an
  expiring model grant. A saved change invalidates prior connections. No
  operator-maintained user list, manual ticket or discovery step is required.

- Provider keys stay in the user-controlled service and go only to the locally
  configured provider. Neither the hosted frontend nor its backend receives
  them. Local connection grants remain between browser and local service.
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
  controlling the user's OS or desktop app. A permitted origin may
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

**Prototype results, 2026-11-23.** Initial measurements used a disposable HTTP
counterpart. They establish browser behavior at that time. The current
[desktop browser check](checks/browser-connection.cjs) exercises the real
extracted app's local form and hosted connect, catalog and disconnect routes.

| Browser tested | Local transport | Observed result |
| --- | --- | --- |
| Chrome for Testing 158.0.8127.36, headless macOS | HTTP | Initial loopback permission was `prompt`. With permission denied no request reached the listener. After the per-origin grant, pairing and catalog returned 200. |
| Brave 1.100.58, Chromium 158.0.8127.42, headless macOS | HTTP | Same denial and success, with the engine reporting the permission state. |
| Playwright Firefox 142.0.1, Linux | HTTP | Pairing and catalog returned 200 in the default context. |
| Playwright WebKit 26.0, Linux | HTTP | Fetch failed with “Not allowed to request resource”. The listener saw no request. |
| Same WebKit build | HTTPS | Pairing and catalog returned 200 using a certificate for `127.0.0.1` signed by a CA trusted only inside the disposable container. |

The earlier prototype checked foreign, opaque and absent origins and an
unexpected Host. Browser permission and local origin approval are independent.
Linux WebKit does not establish Safari compatibility. The desktop app uses
plain loopback HTTP. A successful TLS experiment in the prototype does not
establish support in the shipped app. Release requires a normal hosted
connection in the actual browsers listed in the README.
For the focused check, run `node checks/browser-connection.cjs <chromium|firefox|webkit> <absolute-app-executable>`
with Playwright Core and the relevant browser installed. For Chromium set
`CHROMIUM_PATH` to the desktop browser executable.

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

Deliver the native archives, public Package defaults and per-user files
described above. Each native runner must start the extracted application,
check its local settings, preserve configuration, identity and keys across a
restart, and complete a real model HTTP exchange with the fixture. Tagged
Windows and macOS builds require native signing; macOS also requires
notarization. The five required targets are listed in the README. A tag
additionally requires normal desktop/browser review on each supported OS.

**Earlier evidence.** The shared Core runtime, strict catalog/result schemas,
ordinary Ollama execution and credential filtering were exercised in Step 2.
The former container distribution is retired. Its checks do not count towards
desktop acceptance. Desktop and browser verification are recorded separately.

**Desktop verification, 2026-11-23 (development archives, 0.2.0).**

| Archive or client | Observed result |
| --- | --- |
| macOS 27.2.1, Apple Silicon | Extracted app started, a second launch reused the service, local instance save and restart preserved personal files, and a real HTTP call to the keyed local provider fixture returned the expected completion. |
| Linux arm64, glibc 2.41, isolated Linux VM on Apple Silicon | The extracted Linux executable passed the same checks. |
| Brave, Chromium 158.0.8127.42, macOS arm64 | The browser saved the instance via the actual local form. A test HTTPS page on the approved origin connected, read the catalog and disconnected; a foreign origin was denied. |
| Firefox 142.0.1, Linux arm64 | The same browser check passed against the extracted Linux executable. |
| Playwright WebKit, Linux arm64 | The HTTPS page's loopback fetch failed with `TypeError: Load failed`. |
| Safari 27.2, macOS | WebDriver declined to open a test session because remote automation was disabled. Its connection to the app remains unverified. |
| Windows x64, macOS Intel, Linux x64 | Native CI jobs defined; those platforms have not been exercised in this checkout. |

The five package checks passed on both build hosts; 29 Core configuration
schema tests passed. The browser checks used a controlled hosted test page.
Release signing, the full GitLab matrix and browser acceptance through the
production Settings client are pending. The Linux VM was a test environment;
users start the desktop executable directly.

### Step 3 — Implement The Backend Delegation Transport

The broker policy disclosure and personal default are approved. At connection time resolve mixed broker members against
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
locally approved exact origins, scoped connection grants, revocation and local
call/token bounds. Validate Host/Origin and reject endpoint injection,
secret/configuration reads and administrative operations from the hosted app.
Filter credential-bearing provider diagnostics before any response or log.

**Working-tree verification, 2026-11-23.** The real Core HTTP probe completes with zero
installed models using a neutral HTTP client. Headless Firefox 142.0.1 also completed
the exchange through ordinary same-origin browser requests. It received the prepared
`lodeon_probe_tool` schema with a 24-token output ceiling and returned a controlled
native Tool call. The Assistant reported the probe as available. This browser check
used a neutral counterpart and performed no provider inference. Core rejects a foreign origin, a missing
graph, the wrong token, a different session of the same user, mismatched calls and
duplicate results. Revoking graph access, logging out and expiry invalidate pending
authority. The local HTTP test covers connection from the configured origin, Host/Origin
checks, catalog and selected-broker disclosure, a provider fixture, replay,
early cancellation, budgets and disconnect.

**Decisions.** Local approval is the instance URL entered in the desktop app.
A personal routed broker supplies its own routing prompt using the canonical
local registry and Markdown file. The Customizer discloses the template only
on broker selection. Core validates and renders it for that router call.
Missing prompts block the affected selection; fixed-only brokers use no
template. Core requires no per-user routing prompt registration.

**Step 3 verification, 2026-11-23.** The package check loads a real personal
registry, exercises selected-broker disclosure over HTTP, and checks
missing-file behavior on reload. A Core HTTP probe exercises reservation,
the rendered request to a personal router, the returned selection, dispatch
to an authorized instance worker, and the final probe result. Provider
responses in this check are controlled. All five package checks and 77
focused Core checks passed, including an ID collision with a hosted prompt
and the expanded input limit. The extracted macOS arm64 development archive
also served the configured mixed broker and disclosed its owner-supplied
prompt only on selection. Step 3 is complete at the transport boundary.
Step 4 delivers the hosted connection, catalog composition and selection UI.

**Review:** a neutral browser counterpart completes a request. A second user,
anonymous tab or wrong operation cannot read its model input or submit its
result. Duplicate, expired and cancelled replies are rejected. Ordinary
installed-model requests and protected graph access retain their behavior.

### Step 4 — Add Connect Personal Models And Catalog Composition

Use the existing hosted Settings/menu/modal patterns for connecting to the desktop app,
connection status and disconnect. Local editing belongs to the
Customizer. Store active grants in tab memory, separate from project data.
Reconnection uses the currently saved instance origin. A compatible service/protocol is checked
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

Document native startup, local Ollama, browser permissions, reloading and
revocation. Use the saved instance and fixed loopback address.

To review the proposed local UI, change a model's temperature, save, and
inspect its existing profile in `data/config.yml`. Then edit that value by
hand and reopen the form. It must show the value from the file.

**Review:** pair, inspect/select an actual local offer, disconnect and reconnect.
Verify same-label collision handling, zero-installed-model operation, keyboard
and narrow-layout usability, policy rejection and absence of secrets in
browser-visible catalogs and saved projects. Customizer startup and pairing
are reviewed from this repository.

**Step 4 implementation and review, 2026-11-23.** Settings connects explicitly
to the v1 service and accepts a validated public catalog. The Editor preserves
a disconnected selection, applies an available personal default and disallows
unresolved broker members. Project and kept-chat model IDs use the existing
Core representation of the public target. The local management form reads and
updates an existing YAML profile's temperature with conflict detection.

Brave (Chromium 158.0.8127.42, macOS arm64) exercised the actual Editor panel
with a controlled HTTPS page, zero installed models and the extracted macOS
arm64 development archive.
Keyboard pairing at 390 px, model information, default selection, disconnect
and reconnect passed. The only loopback requests were connect, targets and
disconnect. A local form save changed the temperature in YAML and a manual
file edit appeared on reopening the form. Editor tests cover same-label
targets, ambiguous workers, denied access, invalid catalogs, late grants
and restoring a disconnected project selection. All 771 frontend tests, six
Customizer tests and the Editor lint, format and type checks passed. The
archive also passed the existing startup, restart and provider fixture checks.
The cross-platform release
matrix and the invocation workflow are separate acceptance items.

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

**Step 5 implementation and review, 2026-11-23.** The Editor drives the existing
Core exchange for personal chat, probe and suggestions. It binds status and stop
requests to the chat operation, cancels pending calls on disconnect, validates
returned envelopes and keeps local grants separate from Core operation tokens.
Personal probes bypass the shared cache. Connecting and opening an imported
personal selection start no inference.

Brave (Chromium 158, macOS arm64) ran the Editor panel and session controller
on a controlled HTTPS origin with the extracted native app and an isolated
Core configuration. With zero installed models, local Ollama `gemma4:12b`
completed plan → query → plan → answer. Core executed `run_sparql_count` on
the running KVKG QLever. The final answer and an independent SPARQL count
both gave 32,897 triples. A follow-up produced a `propose_sparql_node`
proposal for the same query. A local keyed provider fixture passed the native
Tool probe and returned a suggestion. A second Core configuration exercised a
personal broker whose local router chose a directly authorized instance probe
worker. Core tests also reject unauthorized members. The HTTPS test origin and
keyed providers were controlled. Ollama and QLever were real.

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

**Step 6 implementation and review, 2026-11-23.** Core records the actual
execution source for the worker and router. The activity card, readable chat
export and Analyzer show the origin of personal usage. A call with missing
token figures still counts once. An incomplete token sum remains unknown.

On macOS arm64, Brave and the native app completed a real KVKG count using
Ollama. The readable Analyzer report contains four personal model calls
(plan, query, plan, answer), 13,198 reported tokens, one executed
`run_sparql_count` and a result of 32,897 triples. The retained conversation
was exported with its readable Markdown in a named project, imported into a
fresh browser session and reloaded from IndexedDB. Model choice, model calls
and Tool evidence survived. Import and reload issued zero pairing or inference
requests. Stopping the native app during a controlled keyed provider request
produced `assistant.delegation.connection_failed` after one invocation.
Focused checks cover disconnect, logout with an outstanding call, deadlines
and rejection of duplicate and late replies. The controlled credential was
absent from the reviewed logs, Core traces and decompressed project/report
archives. The native release matrix belongs to the final acceptance.

The broader Python architecture check also identified two findings already
present in committed Core. The shared wire validator has an inline typing
suppression for the jsonschema import, and the MCP SPARQL module inventory
omits the tracked diagnostics module. Resolve these before freezing the
inputs for consolidated acceptance.

### Step 7 — Consolidated Acceptance, Documentation And Closure

The Assistant's connection dialog opens this repository's download table and
setup instructions. The table links to the last successful public `main`
builds for all five platforms and the bundled Core revision.
The tagged pipeline publishes the five reviewed
archives and verification files in the Generic Package Registry. Release
acceptance still requires a successful tagged run, recorded native browser
reviews and anonymous access to the published downloads.

Run one bounded final acceptance from committed, unchanged Core, Documentation,
Roadmap and Customizer inputs; record revisions and statuses before/after using
strictly read-only Git commands with optional index refresh disabled.
Complete the applicable central suite and relevant dependency/image security
checks once, with required rebuilds for changed dependencies or images.
Customizer checks remain repository-owned. Do not repeat full acceptance at
every step or introduce a new test platform.

Use a real browser connection, the extracted desktop app and Ollama for the
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


### Desktop review additions

Open a new folder, save a model and a mixed broker, switch back to an existing folder, then restart and verify the selected path. In a connected tab, load the available instance models into the desktop list. Save a personal temperature or top P, reconnect and inspect **Model information**. Verify direct hosted execution and a personal broker with a hosted worker. Clear the fields to inherit instance defaults again. Source-level acceptance on macOS covered selecting a hosted model, saving a personal sampling value, composing a broker, saving its prompt and restoring a settings folder in Brave at desktop and mobile widths. The loopback tests also cover restarting with a saved folder and with that folder unavailable. Core verified a direct installed provider call and a hosted worker in a mixed broker with per-operation sampling. Native archive and platform file-picker review remain part of final desktop acceptance.
