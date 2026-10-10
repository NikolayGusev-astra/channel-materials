#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OntoNet gate client — agent-side half of the MemoryArtifact lifecycle.

    draft -> submit   (agent CAN do this)
    accept / revoke   (server checks authorization — NOT the agent's call)

The point: the agent can PROPOSE a finished step but cannot CLOSE it. That is a
mechanical gate, not a prose reminder that dies with the context window.

See the sibling skill `agent-workflow-gates` for when this is worth using.

Usage
-----
  python onto_gate.py draft  --path draw/2026-10-01-cover --summary "cover 1024x640 verified" \
                             --dod-json '{"checks":["1024x640","vision ok"]}'
  python onto_gate.py submit --path draw/2026-10-01-cover
  python onto_gate.py status --path draw/2026-10-01-cover
  python onto_gate.py audit  --path draw/2026-10-01-cover
  python onto_gate.py list   [--first 50]
  python onto_gate.py supersede --path draw/2026-10-01-cover --summary "..." --dod-json '{...}'

Env
  ONTONET_API_KEY  required (X-API-Key)
  ONTONET_BASE     optional, default https://app.ontonet.ru/api/v2/core
  ONTONET_REALM    optional, default = Hermes Agent Development realm
"""

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = "https://app.ontonet.ru/api/v2/core"
DEFAULT_REALM = "4562b68a-98a0-4e68-a3a4-f36c5c10ff49"  # Hermes Agent Development

# Their server rejects non-ASCII-escaped JSON bodies ("invalid unicode code point"),
# so every outbound body goes through ensure_ascii=True.
def _body(obj):
    return json.dumps(obj, ensure_ascii=True).encode("utf-8")


def realm():
    return os.environ.get("ONTONET_REALM") or DEFAULT_REALM


def post(path, payload, timeout=60):
    base = (os.environ.get("ONTONET_BASE") or DEFAULT_BASE).rstrip("/")
    key = os.environ.get("ONTONET_API_KEY", "")
    if not key:
        sys.exit("ONTONET_API_KEY is not set")
    req = urllib.request.Request(
        base + path,
        data=_body(payload),
        headers={"X-API-Key": key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        # Their 400s name no field. Point at the documented cause set instead of the body.
        sys.exit("HTTP %d on %s\n%s\n\nHint: a bare 400 here usually means a missing required "
                 "field (agent_principal / targets / source_ref), or an unadmitted realm "
                 "(GET /realm/<id>/agent-population/genesis)." % (e.code, path, e.read()[:400]))
    except Exception as e:
        sys.exit("transport error on %s: %s" % (path, e))
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        sys.exit("non-JSON response from %s:\n%s" % (path, raw[:400]))


def _dod(summary, dod_json):
    """Body = the DoD, kept as structured JSON so a verifier can machine-check it."""
    doc = {"summary": summary, "checks": []}
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
    return doc


def _read_by_path(path):
    res = post("/realm/%s/agent-memory/artifact/path" % realm(), {"artifact_path": path})
    return res if isinstance(res, dict) and res.get("artifact_id") else None


def _draft_payload(a, doc, supersedes=None):
    payload = {
        "artifact_kind": a.kind,
        "artifact_path": a.path,
        "body": json.dumps(doc, ensure_ascii=False),
        "summary": a.summary,
        "write_mode": a.write_mode,
        "source_ref": "agent-workflow-gates/scripts/onto_gate.py",
        "review_destination": a.review or "owner",
        "targets": [{"target_kind": "realm", "target_id": realm(), "role": "primary"}],
    }
    if supersedes:
        payload["supersedes_artifact_id"] = supersedes
    return payload


def cmd_draft(a):
    print(json.dumps(post("/realm/%s/agent-memory/artifact/draft" % realm(),
                          _draft_payload(a, _dod(a.summary, a.dod_json))),
                     ensure_ascii=False, indent=2))
    print("\nNEXT: python onto_gate.py submit --path %s" % a.path, file=sys.stderr)


def cmd_submit(a):
    art = _read_by_path(a.path)
    if not art:
        sys.exit("no artifact at path %s — draft it first" % a.path)
    print(json.dumps(post("/realm/%s/agent-memory/artifact/%s/submit"
                          % (realm(), art["artifact_id"]), {}), ensure_ascii=False, indent=2))
    print("\nGATE: the agent cannot advance past 'proposed'. A principal with server-side\n"
          "rights must accept. Do not report the step as done until status=accepted.",
          file=sys.stderr)


def cmd_status(a):
    art = _read_by_path(a.path)
    if not art:
        sys.exit("no artifact at path %s" % a.path)
    print(json.dumps(art, ensure_ascii=False, indent=2))


def cmd_audit(a):
    art = _read_by_path(a.path)
    if not art:
        sys.exit("no artifact at path %s" % a.path)
    print(json.dumps(post("/realm/%s/agent-memory/artifact/%s/audit"
                          % (realm(), art["artifact_id"]), {}), ensure_ascii=False, indent=2))


def cmd_list(a):
    # Verified live: search 400s on offset:0 and on any artifact_kind value, both of
    # which the schema declares legal. Omit both; filter client-side.
    res = post("/realm/%s/agent-memory/artifact/search" % realm(), {"first": a.first})
    items = res.get("items", []) if isinstance(res, dict) else res
    for it in items:
        print("%-40s %-12s %s" % (it.get("artifact_path", "?"), it.get("status", "?"),
                                  (it.get("summary") or "")[:60]))
    print("\ntotal: %s" % (res.get("total", "?") if isinstance(res, dict) else len(items)))


def cmd_supersede(a):
    art = _read_by_path(a.path)
    if not art:
        sys.exit("no artifact at path %s" % a.path)
    print(json.dumps(post("/realm/%s/agent-memory/artifact/draft" % realm(),
                          _draft_payload(a, _dod(a.summary, a.dod_json),
                                         supersedes=art["artifact_id"])),
                     ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description="OntoNet gate client")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("draft", help="create a draft artifact carrying the DoD")
    d.add_argument("--path", required=True)
    d.add_argument("--kind", default="NOTE")
    d.add_argument("--summary", required=True)
    d.add_argument("--dod-json", help='structured DoD, e.g. \'{"checks":["1024x640","vision ok"]}\'')
    d.add_argument("--write-mode", default="APPEND")
    d.add_argument("--review")
    d.set_defaults(func=cmd_draft)

    s = sub.add_parser("submit", help="propose the step for review (agent-side boundary)")
    s.add_argument("--path", required=True)
    s.set_defaults(func=cmd_submit)

    st = sub.add_parser("status", help="read one artifact by path")
    st.add_argument("--path", required=True)
    st.set_defaults(func=cmd_status)

    au = sub.add_parser("audit", help="who did what, when")
    au.add_argument("--path", required=True)
    au.set_defaults(func=cmd_audit)

    li = sub.add_parser("list", help="list accepted artifacts")
    li.add_argument("--first", type=int, default=50)
    li.set_defaults(func=cmd_list)

    sp = sub.add_parser("supersede", help="new revision of an existing decision")
    sp.add_argument("--path", required=True)
    sp.add_argument("--summary", required=True)
    sp.add_argument("--dod-json")
    sp.add_argument("--kind", default="NOTE")
    sp.add_argument("--write-mode", default="APPEND")
    sp.add_argument("--review")
    sp.set_defaults(func=cmd_supersede)

    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
