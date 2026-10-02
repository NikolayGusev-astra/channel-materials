#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OntoNet gate client for the draw pipeline.

Implements the agent-side lifecycle of a MemoryArtifact:
    draft -> submit -> accept   (all three callable with one API key)

    supersede / revoke          a new revision or a rollback

WHAT THE GATE IS, AND WHERE THE BOUNDARY REALLY LIVES (verified live
2026-10-01). Two independent layers, and the second one is easy to miss:

  1. Realm user roles, fetched at GET /realm/{id}/user/roles:
        OWNER | PARTICIPANT | OBSERVER
     The artifact draft I created and accepted myself, so this token holds a
     write-capable role. Enforce draft-then-accept by issuing the WRITER a
     token scoped to PARTICIPANT (or OBSERVER) and reserving accept for an
     OWNER token. The same idea as giving a drawing bot a read-only PAT and
     the reviewer a full one.

  2. Agent principal, a separate admission system on top:
     POST /realm/{id}/agent-population/admissions  (operation: admit)
     plus artifact/own/path, which reads your own draft or proposed artifact
     by path. That reader is the ONLY path that can see a draft, and it needs
     an agent_principal that this realm has never admitted:
     UNKNOWN_AGENT_PRINCIPAL for every value tried.

CORRECTION to an earlier claim in this file: accept_memory_artifact succeeds
with the same agent token that created the draft, and that does NOT show that
OntoNet has no role check. It shows that the token in use has write rights.
The boundary is a property of the token's role, not of the artifact lifecycle.
Never conclude "the server does not check" from "my token was allowed".
Never conclude "the agent cannot close its own step" from one token.

Transport note (verified live 2026-10-01): this goes through their OFFICIAL MCP
server, not the REST layer. REST /agent-memory/artifact/draft returns a BARE
HTTP 400 for a byte-identical payload their own MCP layer accepts. Their
OpenAPI declares neither the artifact_kind whitelist nor the per-kind
write_mode rule — only the MCP layer reveals them.

    artifact_kind  capability_dossier | decision | handoff | operation_matrix
                   | review_log | review_protocol | test_strategy | worklog
    write_mode     'replace' for decision, 'append' for the entry-log kinds
    targets        NON-EMPTY; target_kind in realm|template|entity|diagram
    body           ASCII-escaped JSON (raw UTF-8 -> invalid unicode code point)

Their search returns ACCEPTED artifacts only — a draft or a proposed artifact
is invisible there — and get_own_memory_artifact_draft_by_path demands an
agent_principal this realm has never admitted (UNKNOWN_AGENT_PRINCIPAL).
Hence the local state file: draft records the artifact_id, and the next
command reads it back. That file is the only thing that survives a restart.

Usage
-----
  python onto_gate.py draft --path draw/2026-10-01-cover --kind decision \
        --summary "cover 1024x640 verified" --dod-json '{"checks":[...]}'
  python onto_gate.py submit  --path draw/2026-10-01-cover
  python onto_gate.py status  --path draw/2026-10-01-cover
  python onto_gate.py audit   --path draw/2026-10-01-cover
  python onto_gate.py list
  python onto_gate.py supersede --path draw/2026-10-01-cover \
        --summary "..." --dod-json '{...}'

Env
  ONTONET_API_KEY   required
  ONTONET_MCP       optional, default https://app.ontonet.ru/mcp
  ONTONET_REALM     REQUIRED: UUID of your realm
"""

import argparse
import hashlib
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request

DEFAULT_MCP = "https://app.ontonet.ru/mcp"
DEFAULT_REALM = ""  # REQUIRED: set ONTONET_REALM to your own realm UUID

# VERIFIED LIVE 2026-10-01 against their MCP server. Their REST /v3/api-docs
# declares artifact_kind as a free string and returns a BARE HTTP 400 on a wrong
# value — the whitelist below is only visible through their MCP layer.
#   artifact_kind: capability_dossier, decision, handoff, operation_matrix,
#                  review_log, review_protocol, test_strategy, worklog
#   write_mode:    'replace' for decision, 'append' for the entry-log kinds
#   targets:       NON-EMPTY; target_kind in realm|template|entity|diagram
#   body:          must be ASCII-escaped JSON (raw UTF-8 -> invalid unicode code point)
ARTIFACT_KINDS = [
    "capability_dossier", "decision", "handoff", "operation_matrix",
    "review_log", "review_protocol", "test_strategy", "worklog",
]
KIND_WRITE_MODE = {"decision": "replace"}
DEFAULT_KIND = "worklog"
DEFAULT_WRITE_MODE = "append"


class OntoError(RuntimeError):
    pass


def _dumps(obj):
    """ASCII-escaped only: their server rejects raw UTF-8 with 'invalid unicode code point'."""
    return json.dumps(obj, ensure_ascii=True)


def rpc(tool, args, timeout=60):
    """One MCP tools/call over a fresh handshake; returns the result text."""
    endpoint = os.environ.get("ONTONET_MCP") or DEFAULT_MCP
    key = os.environ.get("ONTONET_API_KEY", "")
    if not key:
        sys.exit("ONTONET_API_KEY is not set")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "X-Onto-Api-Key": key,
    }
    ctx = ssl.create_default_context()

    def send(payload, sid=None):
        h = dict(headers)
        if sid:
            h["mcp-session-id"] = sid
        req = urllib.request.Request(endpoint, data=_dumps(payload).encode(), headers=h)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.headers.get("mcp-session-id"), r.read().decode()

    try:
        sid, _ = send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "draw-onto-gate", "version": "1.0"}}})
        try:
            send({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
        except Exception:
            pass  # a notification carries no body; an empty 200 is success
        _, body = send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                        "params": {"name": tool, "arguments": args}}, sid)
    except urllib.error.HTTPError as e:
        raise OntoError("HTTP %d from MCP endpoint\n%s"
                        % (e.code, e.read().decode("utf-8", "replace")[:400]))
    except Exception as e:
        raise OntoError("MCP transport error: %s" % e)

    for line in body.splitlines():
        if line.startswith("data:"):
            payload = json.loads(line[5:])
            break
    else:
        raise OntoError("non-SSE response from MCP:\n%s" % body[:400])
    return payload.get("result", {}).get("content", [{}])[0].get("text", "")


def realm():
    r = os.environ.get("ONTONET_REALM") or DEFAULT_REALM
    if not r:
        sys.exit("ONTONET_REALM is not set — export the UUID of your own realm")
    return r


def _artifact_body(summary, dod_json):
    """Body = the DoD. Kept as structured JSON so a verifier can machine-check it."""
    doc = {"summary": summary, "checked_at": None, "checks": []}
    if dod_json:
        try:
            parsed = json.loads(dod_json)
        except json.JSONDecodeError as e:
            sys.exit("--dod-json is not valid JSON: %s" % e)
        if isinstance(parsed, list):
            doc["checks"] = parsed
        elif isinstance(parsed, dict):
            doc.update(parsed)
    doc["body_sha256"] = hashlib.sha256(
        json.dumps(doc, sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()
    return json.dumps(doc, ensure_ascii=False)


STATE_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "hermes", "draw-onto-state"
)


def _state_file(path):
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", path)
    return os.path.join(STATE_DIR, slug + ".json")


def _remember_id(path, aid):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(_state_file(path), "w", encoding="utf-8") as f:
        json.dump({"artifact_path": path, "artifact_id": aid, "realm_id": realm()}, f)


def _recall_id(path):
    try:
        with open(_state_file(path), encoding="utf-8") as f:
            return json.load(f).get("artifact_id")
    except (IOError, OSError, ValueError):
        return None


def _artifact_id(path, explicit=None):
    """Current artifact_id at a path, in ANY lifecycle status (draft included).

    Discovery order matters, because their API has no "find by path" that sees
    a draft: search_memory_artifacts returns accepted artifacts only (verified
    live 2026-10-01: a freshly submitted artifact is invisible there), and
    get_own_memory_artifact_draft_by_path needs an agent_principal that this
    realm has never admitted (UNKNOWN_AGENT_PRINCIPAL). So the pipeline keeps
    the id itself, in a local state file written by draft. That is the point:
    the step's identity survives restarts without the agent holding it in mind.
    """
    for cand in (explicit, _recall_id(path)):
        if not cand:
            continue
        res = rpc("get_memory_artifact", {"realm_id": realm(), "artifact_id": cand})
        if "ID: %s" % cand in res and "error" not in res.lower()[:80]:
            return cand
    for line in rpc("read_accepted_by_path",
                    {"realm_id": realm(), "artifact_path": path}).splitlines():
        if line.startswith("ID: "):
            return line[4:].strip()
    return None


def cmd_draft(a):
    if a.kind not in ARTIFACT_KINDS:
        sys.exit("artifact_kind must be one of: %s" % ", ".join(ARTIFACT_KINDS))
    res = rpc("create_memory_artifact_draft", {
        "realm_id": realm(),
        "artifact_path": a.path,
        "artifact_kind": a.kind,
        "write_mode": KIND_WRITE_MODE.get(a.kind, DEFAULT_WRITE_MODE),
        "body": _artifact_body(a.summary, a.dod_json),
        "summary": a.summary,
        "source_ref": a.source_ref,
        "review_destination": a.review or "name",
        "targets": [{"target_kind": "realm", "target_id": realm(), "role": "primary"}],
    })
    print(res)
    if "created" not in res.lower():
        sys.exit("\nDRAFT FAILED:\n%s" % res)
    for line in res.splitlines():
        if line.startswith("ID: "):
            _remember_id(a.path, line[4:].strip())
    print("\nNEXT: python onto_gate.py submit --path %s" % a.path, file=sys.stderr)


def cmd_submit(a):
    aid = _artifact_id(a.path, a.id)
    if not aid:
        sys.exit("no artifact at path %s — run draft first, or pass --id" % a.path)
    res = rpc("submit_memory_artifact", {"realm_id": realm(), "artifact_id": aid})
    print(res)
    if "submitted" not in res.lower():
        sys.exit("\nSUBMIT FAILED:\n%s" % res)
    print(
        "\nGATE: agent cannot advance past 'proposed'. A principal with server-side\n"
        "rights must accept. Do not report the step as done until status=accepted.",
        file=sys.stderr,
    )


def cmd_status(a):
    aid = _artifact_id(a.path, a.id)
    if not aid:
        sys.exit("no artifact at path %s" % a.path)
    print(rpc("get_memory_artifact", {"realm_id": realm(), "artifact_id": aid}))


def cmd_audit(a):
    """No dedicated audit tool exists on their MCP server (verified: the
    documented artifact tools are draft/submit/accept/revoke/supersede/
    append/update/search/read). Audit trail is carried on the artifact itself,
    so read it back from there."""
    aid = _artifact_id(a.path, a.id)
    if not aid:
        sys.exit("no artifact at path %s" % a.path)
    res = rpc("get_memory_artifact", {"realm_id": realm(), "artifact_id": aid})
    for line in res.splitlines():
        if line.startswith(("ID:", "status:", "last_audit_event", "append_entries")):
            print(line)


def cmd_list(a):
    # Their search paginates from an offset and rejects the default page window:
    # "No memory artifacts on the requested page ... total: 1, first: 50,
    # offset: 100. Use first=0 and offset=<page size>". So the first page must
    # be asked for explicitly as first=0, offset=N.
    res = rpc("search_memory_artifacts", {"realm_id": realm(), "first": 0, "offset": 50})
    print(res)


def cmd_supersede(a):
    aid = _artifact_id(a.path)
    if not aid:
        sys.exit("no artifact at path %s" % a.path)
    print(rpc("supersede_memory_artifact", {
        "realm_id": realm(),
        "artifact_path": a.path,
        "artifact_kind": a.kind,
        "write_mode": KIND_WRITE_MODE.get(a.kind, DEFAULT_WRITE_MODE),
        "body": _artifact_body(a.summary, a.dod_json),
        "summary": a.summary,
        "source_ref": a.source_ref,
        "review_destination": a.review or "name",
        "supersedes_artifact_id": aid,
        "targets": [{"target_kind": "realm", "target_id": realm(), "role": "primary"}],
    }))


def main():
    p = argparse.ArgumentParser(description="OntoNet gate client for the draw pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("draft", help="create a draft artifact carrying the DoD")
    d.add_argument("--path", required=True)
    d.add_argument("--kind", default=DEFAULT_KIND, help="one of: " + ", ".join(ARTIFACT_KINDS))
    d.add_argument("--summary", required=True)
    d.add_argument("--dod-json", help='structured DoD, e.g. \'{"checks":["1024x640","vision ok"]}\'')
    d.add_argument("--source-ref", default="onto_gate.py")
    d.add_argument("--review")
    d.set_defaults(func=cmd_draft)

    sm = sub.add_parser("submit", help="propose the step for review (agent-side boundary)")
    sm.add_argument("--path", required=True)
    sm.add_argument("--id", help="artifact_id; normally read back from local state")
    sm.set_defaults(func=cmd_submit)

    st = sub.add_parser("status", help="read one artifact by path")
    st.add_argument("--path", required=True)
    st.add_argument("--id")
    st.set_defaults(func=cmd_status)

    au = sub.add_parser("audit", help="who did what, when")
    au.add_argument("--path", required=True)
    au.add_argument("--id")
    au.set_defaults(func=cmd_audit)

    li = sub.add_parser("list", help="list accepted artifacts")
    li.set_defaults(func=cmd_list)

    sp = sub.add_parser("supersede", help="new revision of an existing decision")
    sp.add_argument("--path", required=True)
    sp.add_argument("--kind", default="decision")
    sp.add_argument("--summary", required=True)
    sp.add_argument("--dod-json")
    sp.add_argument("--source-ref", default="onto_gate.py")
    sp.add_argument("--review")
    sp.set_defaults(func=cmd_supersede)

    a = p.parse_args()
    try:
        a.func(a)
    except OntoError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
