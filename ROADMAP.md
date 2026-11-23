# LODEON Customizer Roadmap

Implementation requested on 2026-11-22. **Progress: 1 of 7 review steps complete.**
The v1 protocol and browser feasibility check are ready for review. The next
step delivers the shared model runtime and local service foundation. This is
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

This release does not implement Git transfer, project parameter-editing forms,
a model/API-key configuration GUI, a browser secret vault, personal Brokers,
hybrid Broker configuration, multiple simultaneous service connections in one
tab, provider token streaming or a general runtime Package/plugin loader.
Those features require their own decisions. Existing installed Brokers and
Virtual Models retain their current behavior; a headless client without the
browser relay cannot select a personal target in this release.

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

### Configuration And Target Identity

- Local YAML uses the existing model-profile contract, including provider,
  model, endpoint, generation, caching and optional description/cost settings.
  Environment references resolve only in the local service's environment.
  No remote instance secret names, paths or configuration are resolved locally.
- The local service advertises a strict public catalog, never its raw YAML,
  credentials, environment-variable names or administrative configuration.
- Personal target references have an explicit origin and stable identity;
  installed and personal targets cannot collide or replace each other by id
  or label. Catalog composition is not Package/YAML composition.
- The backend explicitly permits delegation through an owned configuration
  contract and the existing authorization policy. Delegation cannot enable a
  disabled Assistant, bypass KG restrictions or enlarge operator resource
  limits. Ordinary installed-target defaults and limit semantics stay intact.
- A personal target works with zero installed models, without fabricating an
  installed default model. The Connect action remains reachable in that state.
- Personal profiles remain configuration, not automatically selected defaults
  for the hosted instance. Project references do not contain the local service
  address, pairing grant, provider endpoint or credentials.

### Two Independent Trust Boundaries

- Pairing with the local service requires explicit local approval of an exact
  LODEON origin. A one-time, locally issued pairing credential may be used; no
  key-editing GUI is required. No wildcard-origin access, port scanning or
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

In this repository, establish the minimal component/package manifest and
service foundation against that runtime. Read canonical model-profile YAML,
resolve local environment references, provide secret-free Ollama and native
provider examples, and expose only the strict public catalog. Unsupported
non-model instance sections must not be silently adopted. No model weights are
downloaded and no model/key editor is added.

**Review:** focused existing provider/gateway tests pass; a neutral consumer can
load the artifact, validate an Ollama and keyed-provider profile, and produce a
normalized completion without copying provider code. Inspect a sentinel-secret
projection. Customizer implementation and operational progress are recorded
here.

### Step 3 — Implement The Backend Delegation Transport

Add a request-local delegated execution path at the existing gateway. Implement
the frozen browser exchange on the current HTTP stack, bounded transient state,
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

Use the existing Settings/menu/modal patterns for service address, pairing,
connection status and disconnect. No model editor or secret input. Store
active grants in tab memory, separate from project data; reconnection must not
be authorized by an imported project. A compatible service/protocol is checked
before its public catalog is accepted. Connecting/catalog discovery performs
no model inference.

Compose installed and personal targets in the existing selector and Model
information view, with unambiguous source and unchanged installed ordering.
Retain a stable personal selection in the project contract without a grant or
service address. Only one personal service is connected per tab initially;
separate tabs/origins have independently scoped connections. The action must
work when the instance has no installed models and remain unavailable when the
operator disables this capability.

Deliver the actual Customizer as a reproducible Docker service with a minimal
local/CLI pairing mechanism and documented start/stop/configuration workflow.
Publish ports on loopback only; require no Docker socket, privileged container
or operator tunnel. Document host Ollama reachability and supported browser
permissions. Keep local secret inputs out of version control and generic logs.
Make configuration reload and connection revocation behavior explicit; a new
vault or persistent administrative database is not part of this first release.

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
Existing installed Brokers retain their routing; this release adds no personal
Broker editor or implicit mixing of dynamic targets into installed Brokers.

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
