# OntoNet as a gate provider

OntoNet (`app.ontonet.ru`, product of Varkulevich's team) has no pipeline/gate/workflow entity.
It has something better for gating: a server-enforced artifact state machine. Verified against
the live REST API and the shipped OpenAPI doc.

## It is NOT a gate out of the box

```
draft ──submit──▶ proposed ──accept──▶ accepted ──supersede──▶ new cycle
                                       │
                                    revoke
```

The load-bearing question is not "does the lifecycle have an accept state" but "**what role does my
key hold, and what does that role permit**". Two independent layers decide it, and both are real.

## Authorization: two layers, verified live

**Layer 1 — realm user roles.** `GET /realm/{realmId}/user/roles` returns a closed set:

```
{"roles":["OWNER","PARTICIPANT","OBSERVER"]}
```

Roles are bound to the realm and to the key. `accept_memory_artifact` called with the same key
that created the draft returned `status: accepted`, `last_audit_event: accepted` — because that key
holds a **write-capable role**, not because the boundary is absent.

**An earlier revision of this file concluded from that single success that "there is no separate
reviewer identity, no role check, and no server-side principal separation on this path". That was
an overclaim and it was wrong.** One credential being permitted says only what that credential may
do; it says nothing about whether the system distinguishes credentials. Asking the API what roles
exist answered the question in one call and disproved the claim. Never write "the system does not
check" as a finding — write which role you hold and what that role permits.

**Layer 2 — agent principal and admissions.** A separate governance system sits on top:
`POST /realm/{realmId}/agent-population/admissions` (operation `admit`) plus
`POST /realm/{realmId}/agent-memory/artifact/own/path`, which reads your own draft or proposed
artifact by path and is the only reader that can see a draft. It demands an `agent_principal`; in
an unadmitted realm every value returns `UNKNOWN_AGENT_PRINCIPAL`, and `list_realm_agents`
returns `agents: []` with `governance_status: governance_unavailable` and issue
`constitution_missing`. So per-agent governance is unavailable in an unadmitted realm — but that
is a statement about agent admission, NOT about role enforcement. Do not let the second fact
appear to support the first claim.

**How to make it a real gate:** give the writing agent a key at `PARTICIPANT` (or `OBSERVER` for
read-only) and reserve `accept` for an `OWNER` key. Then `proposed → accepted` is genuinely
unreachable for the writer, and the boundary holds because of the role, not because of the
workflow. Until two keys exist, this provider is durable state plus an audit log.

The general lesson, which is why this lives here rather than in a changelog: **a gate whose
enforcement you have inferred is a hypothesis, and a successful call with your own key disproves
nothing.** Prove the boundary from both directions — attempt the transition it is supposed to block
with the blocked party's credentials, AND enumerate what the system actually distinguishes. "The
lifecycle says only a reviewer can accept this" and "the reviewer holds a different role" are two
separate claims; only the second is load-bearing, and only the API can confirm it.

Supporting endpoints (path segment is `realmId` for these, unlike the UI's `contextId`):

- `POST /realm/{realmId}/agent-memory/artifact/draft` — create/replace draft
- `POST /realm/{realmId}/agent-memory/artifact/{artifactId}/submit`
- `POST /realm/{realmId}/agent-memory/artifact/{artifactId}/accept`
- `POST /realm/{realmId}/agent-memory/artifact/{artifactId}/revoke`
- `POST /realm/{realmId}/agent-memory/artifact/{artifactId}/supersede` (via draft + `supersedes_artifact_id`)
- `POST /realm/{realmId}/agent-memory/artifact/search` — ACCEPTED artifacts only
- `GET|POST /session-state/{contextId}` — persisted process state per context
- `POST /realm/{realmId}/agent-population/admissions` — atomic agent admission
- `GET  /realm/{realmId}/user/roles` — the caller's roles in this realm (OWNER/PARTICIPANT/OBSERVER)
- `POST /realm/{realmId}/agent-memory/artifact/own/path` — read own draft/proposed by path (needs `agent_principal`)
- `GET  /realm/{realmId}/agent-population/genesis` — realm initialization state

There is **no separate audit tool**; `GET .../audit` in the REST docs has no MCP counterpart
(`readArtifactAudit` → "Unknown tool"). Read the trail off the artifact itself via
`get_memory_artifact` and take `status`, `last_audit_event`, `last_audit_event_at`, `append_entries`.

## Preconditions: there is no wall

**Artifact writes work with a plain API key. Do not conclude otherwise from a failed probe.**

An earlier revision of this file asserted that a `not_initialized` realm blocks all agent writes
and that drafts "fail with an opaque 400". That conclusion was wrong and it cost a real debugging
session: a `draft` against an allegedly-unwritable realm succeeded and returned an `artifact_id`.
`GET /realm/{realmId}/agent-population/genesis` is a realm-lifecycle signal, not an agent-write
permission check. An admissions API exists for multi-agent governance, but its absence is not a
precondition for the artifact lifecycle.

The rule that replaces it: **a bare 4xx from one transport is not a capability verdict.** Their
REST and MCP layers disagree, so before concluding a write is forbidden, replay the same payload
through the other interface — a byte-identical payload that REST rejects is accepted by MCP.

## Use the MCP transport, not REST

Go through `https://app.ontonet.ru/mcp` with header `X-Onto-Api-Key` (NOT `X-API-Key`, which is
the REST header) after a standard `initialize` handshake. Reasons, all verified live:

- REST `POST /realm/{realmId}/agent-memory/artifact/draft` returns a bare HTTP 400 for a payload
  their own MCP layer accepts.
- The `artifact_kind` whitelist and the per-kind `write_mode` rule appear ONLY in the MCP tool
  schema. Their OpenAPI declares `artifact_kind` a free string, so a REST caller cannot discover
  the valid set — it just 400s.
- REST 400s name no field, so a wrong value and a missing field are indistinguishable from REST.

### Values only the MCP schema reveals

- `artifact_kind` — closed set: `capability_dossier`, `decision`, `handoff`, `operation_matrix`,
  `review_log`, `review_protocol`, `test_strategy`, `worklog`.
- `write_mode` — `replace` for `decision`, `append` for the entry-log kinds. Guessing the
  uppercase enum names their REST docs imply gets a 400.
- `review_destination` — a person's name, not the literal string `owner`.
- `targets` — required and non-empty; `target_kind` in `realm|template|entity|diagram`.
- `body` — ASCII-escaped JSON; raw UTF-8 fails with "invalid unicode code point".

## Trap: only accepted artifacts are findable

`read_accepted_by_path` and `search_memory_artifacts` BOTH resolve ACCEPTED artifacts only.
Immediately after `draft`, and again after `submit` while status is `proposed`, the artifact exists
but no reader can see it — so a client that re-resolves the id by path reports "no artifact" and
the chain silently stops. `get_own_memory_artifact_draft_by_path` would cover the draft, but it
requires an `agent_principal` the realm has never admitted (`UNKNOWN_AGENT_PRINCIPAL` for every
value tried).

**Capture the `artifact_id` from the `draft` response and persist it next to the run state.** That
state file is then the only thing carrying a step's identity across a restart — which is the whole
point of using this provider, so make sure it is written before the next command runs.

## Verified API quirks (all reproduced live)

1. **`search` pagination is offset-based and the default window is empty.** Asking for
   `first=50` returns "No memory artifacts on the requested page ... total: 1, first: 50,
   offset: 100. Use first=0 and offset=<page size>". The first page must be requested explicitly
   as `first=0, offset=<page size>`.
2. **`search` rejects any `artifact_kind` filter** with 400 despite the schema. Filter client-side.
3. **`agent_principal` is required**; when it is present-but-unknown you get a precise
   `UNKNOWN_AGENT_PRINCIPAL`, when absent you get a bare 400 with no field name. Do not debug
   from the bare 400 — probe once with an explicit principal to get the readable error.
4. **`draft` requires `targets` (non-empty) and `source_ref`** — the official MCP tool schema
   marks all seven of `artifact_kind, write_mode, body, summary, source_ref, targets` as
   required. Getting 400s with no field named means a missing required field, not a bad value.
5. **400 responses carry no detail.** The `admissions` endpoint is the exception: it returns a
   structured `{code, field, violation, correlation_id}`. Absence of detail is not absence of a
   cause.

## Client

`scripts/onto_gate.py` in this skill wraps the MCP transport:
`draft | submit | status | audit | list | supersede`. It ASCII-escapes request bodies, records a
body sha256 in the artifact body, validates `artifact_kind` against the real whitelist, persists
the returned `artifact_id` to a local state file, and accepts `--id` on the follow-up commands so
the chain survives a restart. Run it with `ONTONET_API_KEY` set; `ONTONET_REALM` overrides the
default realm, `ONTONET_MCP` overrides the endpoint. It deliberately exposes no `accept`
subcommand — that is a policy choice in the client, not a server restriction: the key in use has
been shown to accept. Omitting it keeps the writer from closing its own step, which is only a real
constraint once the writer holds a lesser role.

The `draw-onto` skill carries a second, image-pipeline-specific client built on the same verified
contract. If one of them 400s at `draft`, check the transport before debugging the payload.

## Fit assessment

Worth it when the process outlives one session (a night batch of many generated artifacts), when
the DoD must be auditable, or when a second key lets you turn the lifecycle into a real gate. Not
worth it for a one-shot task, and not worth installing as a "gate" while one key holds every
transition — that is a durable journal plus two round-trips per step, and the audit trail it buys
is the part that justifies the cost.
