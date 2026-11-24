# LODEON Customizer personal model protocol v1

This contract covers personal model invocation and broker discovery. The desktop
app bundles the Core runtime and its public payload schemas. Local model routes, the Core exchange and the hosted Settings catalog client
are implemented. The Editor also runs the v1 invocation exchange for chat,
probe and suggestions. Each reservation binds its own grant connection,
catalog revision, graph and selected target. Personal probes run fresh on the
active connection. The standard Assistant HTTP response completes the operation.

The v1 envelopes below describe individual model offers. The
[approved broker contract](#selected-broker-policy-and-personal-default) describes the additional
disclosure needed for mixed brokers and a connected-user default. Local
administration uses the Customizer's own UI and files.
A model connection grant cannot authorize configuration or key edits.

## Local connection

The desktop app listens on `http://127.0.0.1:8765`. The user saves one
LODEON instance URL on the app's local settings page. HTTPS is required except
for HTTP on the exact hosts `localhost`, `127.0.0.1` and `[::1]`. A deployment path is
retained for display. Browser permission is granted to its serialized origin
(scheme, hostname and port), which is the boundary a browser can enforce.
The app starts with no authorized origin. Its management forms post to `/instance`, `/model` (create or edit a profile),
`/model-key` (write the key for a saved profile) and `/quit`. Model editing
pages live under `/models/` on the app’s own origin. Only the key reference
appears in YAML. The password field always opens empty. All require the local Host and its own Origin. Saving a valid
configuration revokes active connections. The hosted page cannot administer
the app, read a key or change the permitted instance.

The hosted client contacts the loopback service with credentials omitted,
redirects rejected and no referrer. It must run in a secure context whose
browser and deployment policy permit the local request. Every model route,
including preflight, checks Host and the exact configured Origin. A missing,
opaque or foreign Origin is denied. Responses use `Cache-Control: no-store`
and `Vary: Origin`. Only the configured origin receives a matching
`Access-Control-Allow-Origin`. Browser permission is independent of the saved
instance. The existing browser evidence and its limits are in the roadmap.

| Method and path | Request | Result |
| --- | --- | --- |
| POST `/v1/connect` | Empty request from the saved instance's origin | `200 {connectionId, grant, expiresInSeconds}` |
| GET `/v1/catalog` | Local bearer grant | `200 {revision, models}` |
| GET `/v1/targets` | Local bearer grant | Models, broker summaries and optional default |
| POST `/v1/instance-models` | Grant and `{models: [{id, label, provider, sampling}]}` from the current authorized instance status | Per-model sampling overrides for those IDs. Sampling accepts only optional temperature and topP. The roster expires with its grant. |
| POST `/v1/broker` | Grant and `{target, revision}` | Selected broker policy and member offers |
| POST `/v1/invoke` | Grant and invocation | One terminal result envelope |
| POST `/v1/cancel` | Grant and `{operationId, callId, connectionId}` | `204` after recording cancellation |
| POST `/v1/disconnect` | Grant | `204` after revocation |

The local bearer grant and the independent Core operation token stay in tab
memory. Send the former only to loopback and the latter only to Core. Keep
both out of URLs, logs, traces and projects. Connection, operation and call
IDs serve only for correlation.

## Fields crossing each boundary

Objects below have closed envelopes. `?` denotes optional. Nested Tool schemas,
Tool arguments and message content follow their existing Core contracts.

| Fields | From → to | Meaning and disclosure |
| --- | --- | --- |
| `target = {source: "personal", serviceId, profileId}` | Local → tab → selected Core operation | Stable public service UUID generated once locally, plus the local profile's public ID. Compare the tuple, never a label. Project and chat `modelId` use Core’s existing `personal:<serviceId>:<profileId>` representation of this tuple. Reconnection verifies it. Sharing a project can disclose these public IDs. Installed target IDs retain their existing meaning. |
| `offer = {target, label, description?, provider, generation, promptCaching, limits, cost?}` | Local → tab. The selected model's offer or the selected broker's local member offers → Core | Allowlist public configuration intentionally supplied for display or budgeting. Use the existing four provider IDs and canonical nested profile fields/types. Omitted local generation/limit settings project as empty objects. Render strings as text. Native model name, endpoint, paths, env names, credentials, local access lists and raw YAML stay local. |
| `revision, connectionId` | Local → tab → Core | Opaque catalog snapshot and per-grant connection ID. Bind both to the operation and reject changes before dispatch. A changed catalog or grant requires a new operation. |
| `kind, knowledgeGraphProfileId, revision, connectionId` plus one of `offer`, `broker`, `instance` and optional `instanceSettings` | Tab → Core | Authorize and reserve the exchange for exactly one `chat`, `probe` or `suggestions` request. Core applies its own policy and budget to all browser-supplied metadata. |
| `operationId, operationToken, expiresInSeconds` | Core → tab | Short-lived authority for this operation only. Local receives the correlation ID on calls. Core and tab alone hold the token. |
| `operationId, callId, connectionId, revision, target, task` | Core → tab → local | Identify one call. Use the existing Core task enum. Local checks the grant, target and revision before dispatch. |
| `messages, tools, generation, bounds` | Core → tab → local | Exact prepared provider-neutral messages and offered function schemas (`[]` for a tool-free call). Generation allows only `temperature`, `topP`, `reasoningEffort` from the approved profile. Bounds contain positive `maxInputCharacters`, `maxOutputTokens` and `modelRequestTimeoutSeconds`. Both sides enforce their own limits. |
| Provider-native model ID, translated request and provider authentication | Local → configured provider or Ollama | The local profile fixes the destination. The shared adapter applies caching/runtime settings and prepares messages, Tools and authorized Story/KG evidence. Any configured provider credential stays on this connection. |
| `operationId, callId, connectionId, completion` **or** `operationId, callId, connectionId, error` | Local → tab → Core | Echo the bound IDs. Exactly one outcome. The tab may report a closed transport error if local execution becomes unreachable. Core validates the envelope before resuming. |
| `completion = {content, toolCalls, finishReason?, usage?}` | Inside success | Text and ordered native calls `{id, name, arguments}` with object arguments. Finish reasons use Core's enum. Optional usage contains available nonnegative integer token counts only (`inputTokens`, `outputTokens`, `totalTokens`, `cachedInputTokens`, `cacheWriteInputTokens`). Core owns call counts, timing, pricing estimates and provenance. |
| `error = {code}` | Inside failure | Existing allowlisted Core model error codes or the protocol codes below. Localize at the receiver. Exclude raw provider bodies, exception strings, headers and stack traces. |

The invocation is the single object formed by the two Core-to-local call rows.
For delegated calls, measure input characters in the compact UTF-8 JSON text
of `{"messages":…,"tools":…}` before provider translation. Count Unicode
code points, preserve non-ASCII characters, and use no separator whitespace.
Core prepares the context and validates returned Tool calls through its normal
Tool Loop. Local limits or an advertised price cannot grant access to Core
resources. Core takes the lower of its delegated budget and each advertised
maximum. Local rejects requests exceeding its independently configured limits
or changing its configured generation values. Local call and output-token
budgets apply across all connections to the active configuration. An ambiguously
completed call consumes its reservation. Installed-model limits keep their
existing semantics.

## Core HTTP exchange

Use the existing threaded HTTP server and synchronous operation handlers. The
browser starts the ordinary operation and relays calls concurrently. The new
base path is `/api/assistant/delegation/v1`. Requests to Core use the existing
instance authentication. The exchange additionally requires an exact same-origin
Editor request. A disabled Assistant always takes precedence.
The existing Assistant status exposes a `personalModelsAllowed` boolean for
this browser session independently of the installed-model count. Service
addresses, other users' offers and local pairing state stay out of status.

1. **Reserve.** `POST /operations` accepts exactly one selection (personal offer, personal broker or installed model ID in `instance`) and
   returns `201 {operationId, operationToken, expiresInSeconds}`. Check the
   operator's opt-in `assistant.personalModels.enabled` (default false) and
   its optional `access.allowedGroups` using the existing central model
   access policy, plus the ordinary KG and operation permissions. An installed
   model is unnecessary. Bound the number, size and lifetime of reservations,
   including anonymous requests. Optional `instanceSettings` maps directly
   accessible installed member IDs to temperature/topP patches. Direct installed
   selection requires a nonempty patch for that model. A personal broker may
   supply patches solely for its installed members. Each provider call rechecks
   access and merges the patch into a request-local profile. Direct installed
   selection completes through the ordinary HTTP response without polling loopback.
2. **Start once.** The existing chat, probe or suggestions POST carries its
   ordinary payload and the headers `X-Lodeon-Operation-Id` and
   `X-Lodeon-Operation-Token`. Omit the installed `modelId`. Bind before
   tracing, reject a conflicting model, kind or graph, and attach the reserved
   selection and authorized sampling values to that request. Keep the existing operation open for its ordinary
   final HTTP response. The gateway exposes at most one pending invocation
   per operation and waits on a condition until reply, cancellation or timeout.
3. **Deliver once.** `POST /next` with both headers and empty body waits up
   to 15 seconds or the earlier remaining deadline. `204` means poll again.
   `200` delivers the invocation and atomically marks it delivered. Only one
   poll may wait per operation. A delivered invocation is never redelivered.
   The tab submits it once to the local service.
4. **Resume once.** `POST /result` with both headers and the terminal envelope
   returns `204` after atomic acceptance. Match the session, operation,
   connection and outstanding delivered call. A missing, expired, cancelled,
   duplicate or mismatched result cannot advance the gateway. Core executes
   authorized Tools and may publish another call through the same exchange.
5. **Finish.** The ordinary final response ends polling. `POST /cancel` on
   the exchange with both headers and empty body closes it and wakes waiters.
   For a delegated chat the existing turn status and cancel routes also verify
   the exchange owner. Probe and Suggestions keep their existing lifecycle.
   The tab cancels any local in-flight call. Deadlines release state even
   after a lost final response, tab close or process loss.

Every exchange action validates the token and the original live session if
login is enabled, and rechecks applicable permissions. With login disabled,
the server-issued token held by the initiating tab distinguishes anonymous
operations. Same-origin scripts that possess the token share its authority.
A turn ID, trace ID, cookie alone, or a new login by the same user grants no
access to a pending exchange.

Use bounded in-memory state. Atomically reserve local call IDs within a grant
before invoking the provider and remember consumed or cancelled IDs until grant
expiry, including cancellation arriving before an invocation. Release pending
payloads promptly. Revocation, logout, timeout or restart invalidates affected
state. A lost delivery or ambiguous provider outcome terminates explicitly.
The relay does not replay it or substitute an installed target.

For transport failures use `{error: {code}}`. Use `400 invalid_request`,
`403 denied`, `404 unsupported_version` for other protocol versions,
`409 conflict` for incompatible revisions or consumed calls, `410 closed`
for a closed exchange whose ownership can still be verified, `429 busy` for
capacity, and `504 timeout` for timeout. Unknown or unauthorized operations
share the same denial. A browser network failure maps to `connection_failed`,
explicit cancellation to `cancelled`. The wire codes are fixed identifiers.
Core maps them to its registered errors. Never forward free-form diagnostics.

### Current transport bounds

Core holds up to 32 live operations per process. Each expires after the earlier
of one hour or the configured model request timeout multiplied by
`2 + maxToolCallsPerTurn`. Each individual call also observes its effective
model request timeout. The Core exchange and the local model routes accept up
to 2 MiB per JSON request body.

The local service allows up to 32 concurrent grants lasting up to one day.
The active configuration has a shared budget of 1,024 calls and 2³¹ output
tokens. Reconnection does not replenish it. Saving locally or restarting the
app resets the budget and invalidates earlier grants. An invocation reserves
its full output ceiling. Early cancellation consumes one call slot and
prevents later execution of the same ID within that grant.

### Call history in Core

Core adds `executionSource` to the provenance of each delegated operation's
worker. Its values are `personal` for a local Customizer invocation and
`instance` for a hosted member. Core retains router provenance separately
under `routerMetrics` in kept chats. These fields belong to Core's records.
The terminal envelope continues to carry only available token measurements.
Core counts the invocation and measures elapsed time. A missing measurement
leaves its total unknown.

## Shared runtime delivery

Each desktop build installs `lodeon-model-runtime` from the same Core revision
as the bundled resolver and configuration defaults. Core's API installs its
own copy from the same source. The desktop archive includes Python and these
dependencies. Public wire compatibility follows the protocol version.

## Selected broker policy and personal default

The approved extension uses two additional local routes under the existing v1
prefix. The individual-model catalog and terminal result retain their wire formats.
`GET /v1/targets` returns `revision`, granted `models` and `brokers`, and
optionally `defaultTarget`. A broker summary contains its target, label,
optional description and typed member references. The browser checks those
references against both authorized catalogs. When an operation selects a
broker, `POST /v1/broker` takes `{target, revision}` with the local grant.
Its response contains `{target, members, models, policy}` and, for a policy
with a routed task, the string `routingPrompt`. Members identify
their source and profile; personal members also identify their local service.
A broker reservation carries this object in `broker` in place of `offer`.
Core validates its closed native policy and membership before reserving.

- **On connection**, the tab receives granted model and broker summaries.
  For a broker it also needs the member IDs to check availability. Each member
  must resolve uniquely to a locally granted ordinary model or a directly
  authorized instance model. A missing, inaccessible or ambiguous member
  makes that broker unavailable. Selecting an available personal default uses
  its stable target reference from the catalog and takes effect immediately.
- **When starting an operation with a personal broker**, provide Core with the
  selected broker's execution policy: bound member references, routing hints,
  router selection, objective, routing prompt ID, task strategies and ordered
  fallbacks. Include the public model offers needed for its local calls.
  The local owner can see what a broker grant discloses. Endpoints, provider
  credentials, environment names and the rest of the local configuration stay
  on the user's machine.
- **For routed tasks**, the Customizer snapshots the registered UTF-8 Markdown
  template for `policy.router.prompt` when loading local configuration. The
  selected-broker response carries its text. Paths, the registry and unrelated
  templates stay local. A fixed-only policy omits `routingPrompt`. Missing
  or unusable local templates return `409 routing_prompt_unavailable` on
  selection. Core validates the submitted template at reservation and renders
  it only for that operation's router. The router's input limit also applies
  to the expanded text. A hosted or KG prompt with the same ID has no effect.
  Full tracing can record the rendered model input and the template's logical
  ID and content hash. Only put text in the routing file that may be shared
  with the connected instance and the router's provider.

For example, a personal broker can assign planning to local Ollama and query
writing to an instance model. Core delegates the planning call, checks the
user's direct access before calling the hosted query worker, and executes any
accepted SPARQL tool call itself. The local service checks its own grant for
each personal model call.
