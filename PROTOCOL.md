# LODEON Customizer personal model protocol v1

This is the implementation contract for the first capability. The executable
Step 1 counterpart exercises pairing, catalog access and browser security.
The installed runtime now validates catalog and result payloads against
`lodeon_model_runtime/personal-models-v1.schema.json` in the wheel. The
production HTTP service, Assistant routes and Settings integration are subsequent steps.

The envelopes below describe individual model offers. The approved mixed
brokers and connected-user default still need a protocol revision before
implementation. Local administration uses the Customizer's own UI and files.
The pairing grant described here cannot authorize configuration or key edits.

## Local connection

The user explicitly selects a loopback service address. The reference address
uses the IPv4 literal `127.0.0.1` and an explicit port. Both HTTP loopback
and locally configured HTTPS with a browser-trusted, name-matching certificate
are supported transports. Docker publishes on host loopback. The Editor allows
only loopback destinations, rejects URL credentials, query, fragment and
redirects, and sends requests with `credentials: "omit"` and no referrer.
The hosted page needs a secure context and a deployment policy that permits
the connection, including CSP `connect-src` if set.

Locally, the user approves an exact serialized HTTPS origin (scheme, host and
port), a set of profile IDs, finite execution bounds and the personal-model
capability. The local command issues a short-lived single-use pairing ticket.
The service validates the expected Host including port and the approved Origin
on every request, including OPTIONS and requests with valid credentials.
Missing, opaque (`null`) or unapproved origins fail before any operation.
Preflight permits only the route's method and required headers. Responses use
`Cache-Control: no-store` and `Vary: Origin`. Only an approved origin gets
its exact `Access-Control-Allow-Origin`. Local browser permission and service
approval are independent.

All paths below are relative to that service. The version is in the path.
Unknown versions, fields or enum values fail closed. JSON bodies use
`application/json`. Empty operations have no body.

| Method and path | Browser sends | Local service returns |
| --- | --- | --- |
| POST `/v1/pair` | `Authorization: Bearer <ticket>` | `200 {connectionId, grant, expiresInSeconds}`. Atomic ticket consumption creates one expiring grant for that origin and approved scope. |
| GET `/v1/catalog` | `Authorization: Bearer <grant>` | `200 {revision, models: [offer, …]}`. An empty list is valid. |
| POST `/v1/invoke` | Grant header and the invocation below | `200` and one terminal result envelope. Execution can block until its deadline. |
| POST `/v1/cancel` | Grant header and `{operationId, callId, connectionId}` | `204` after cancelling or recording cancellation in this grant. Provider interruption is best effort. |
| POST `/v1/disconnect` | Grant header | `204` after revocation and cancellation of pending calls. The local user can revoke independently. |

Tickets, grants and backend operation tokens are independent, cryptographically
random bearer secrets (at least 256 bits). Connection, operation and call IDs
are opaque correlation values. Keep browser-held credentials in tab memory.
Send the ticket and grant only to the local service, and the operation token
only to Core. Exclude all three from URLs, logs, Full traces and project exports.

## Fields crossing each boundary

Objects below have closed envelopes. `?` denotes optional. Nested Tool schemas,
Tool arguments and message content follow their existing Core contracts.

| Fields | From → to | Meaning and disclosure |
| --- | --- | --- |
| `target = {source: "personal", serviceId, profileId}` | Local → tab → selected Core operation | Stable public service UUID generated once locally, plus the local profile's public ID. Compare the tuple, never a label. Only the tuple is needed for a portable selection. Reconnection verifies it. Sharing a project can disclose these public IDs. Installed target IDs retain their existing meaning. |
| `offer = {target, label, description?, provider, generation, promptCaching, limits, cost?}` | Local → tab. Only the selected offer → Core | Allowlist public configuration intentionally supplied for display or budgeting. Use the existing four provider IDs and canonical nested profile fields/types. Omitted local generation/limit settings project as empty objects. Render strings as text. Native model name, endpoint, paths, env names, credentials, local access lists and raw YAML stay local. |
| `revision, connectionId` | Local → tab → Core | Opaque catalog snapshot and per-grant connection ID. Bind both to the operation and reject changes before dispatch. A changed catalog or grant requires a new operation. |
| `kind, knowledgeGraphProfileId, offer, revision, connectionId` | Tab → Core | Authorize and reserve the exchange for exactly one `chat`, `probe` or `suggestions` request. Core applies its own policy and budget to all browser-supplied metadata. |
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
budgets apply across concurrent requests on the grant. An ambiguously
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

1. **Reserve.** `POST /operations` takes the five reservation fields above and
   returns `201 {operationId, operationToken, expiresInSeconds}`. Check the
   operator's opt-in `assistant.personalModels.enabled` (default false) and
   its optional `access.allowedGroups` using the existing central model
   access policy, plus the ordinary KG and operation permissions. An installed
   model is unnecessary. Bound the number, size and lifetime of reservations,
   including anonymous requests.
2. **Start once.** The existing chat, probe or suggestions POST carries its
   ordinary payload and the headers `X-Lodeon-Operation-Id` and
   `X-Lodeon-Operation-Token`. Omit the installed `modelId`. Bind before
   tracing, reject a conflicting model, kind or graph, and attach the reserved
   offer to that request. Keep the existing operation open for its ordinary
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

## Shared runtime delivery

Core builds the Python wheel `lodeon-model-runtime` from
`api/lodeon_model_runtime/`. The `model-runtime-wheel` target in
`api/Dockerfile` exports the artifact. Version 0.1.0 uses LiteLLM 1.104.0.
The Core gateway remains the owner of request orchestration, tracing, cost and
provenance. Core and Customizer install the same wheel. The Customizer release build consumes the wheel directly
from the Core build target and takes the resolver and configuration defaults
from the same Core checkout. Compose starts the versioned image from the
GitLab Container Registry. Wire compatibility follows the protocol version.
