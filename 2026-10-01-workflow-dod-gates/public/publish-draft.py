#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Publish a Markdown draft to telegra.ph as a review copy, then check it.

WHAT THE DoD ACTUALLY IS HERE
    "The page exists and renders correctly". That check has to hit the real
    API, not a local file, or it proves nothing.

PUBLIC-DRAFT CONTRACT (why this is not just a publisher)
    A telegra.ph page is public the moment createPage returns. There is no
    private draft and no unpublish. Two consequences for the pipeline:

      1. Do not call createPage twice. It always mints a NEW path, so a
         second call leaves an orphan page and no way to fix the first.
         Corrections go through editPage on the existing path.
      2. The review marker lives in the TITLE, not in a flag. " (ЧЕРНОВИК для
         вычитки)" makes the state visible to anyone who gets the link, and
         the URL stays uncited until you decide to send it.

    Telegra.ph truncates the title at 60 characters, SILENTLY, and will cut
    the marker off the end. So the marker must be inside the budget from the
    start — see fix_title(), which shortens the BASE title and never touches
    the marker. editPage enforces the same limit.

VERIFIED BEHAVIOUR (2026-09-30)
    - getPage?return_content=true returns result.content as an ALREADY PARSED
      list of DOM nodes, not a JSON string. json.loads(result["content"])
      raises. isinstance(raw, str) is the only correct guard.
    - a plain string in that field is a parse failure, not a document.

PRIVATE-NETWORK NOTE
    Where telegra.ph needs a proxy, set SOCKS=host:port. Leave it empty for a
    direct connection. curl cannot read MSYS paths in --data-binary, so the
    payload is written to a native-path temp file first.

Env
    TELEGRAPH_ACCESS_TOKEN   required (or TELEGRAPH_TOKEN in ~/.hermes/.env)
    SOCKS                    optional, default "" (direct)
    ARTICLE                  optional, default article.md
    TELEGRAPH_CONVERTER      optional path to a Markdown->Telegraph DOM module
    LEAK_TERMS               optional comma-separated internal names that must
                             not reach the page
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

API = "https://api.telegra.ph"
SOCKS = os.environ.get("SOCKS", "")
ARTICLE = os.environ.get("ARTICLE", "article.md")
TITLE_LIMIT = 60
MARKER = "(ЧЕРНОВИК для вычитки)"
CONVERTER = os.environ.get("TELEGRAPH_CONVERTER", "telegraph-publish-direct.py")

# Terms that must never appear in the published DOM. Extend via env.
LEAK_TERMS = tuple(
    t.strip() for t in os.environ.get("LEAK_TERMS", "").split(",") if t.strip()
)


def _mod():
    """importlib, not import: converter filenames usually contain hyphens."""
    spec = importlib.util.spec_from_file_location("telegraph_convert", CONVERTER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def token():
    t = os.environ.get("TELEGRAPH_ACCESS_TOKEN")
    if t:
        return t
    env = os.path.join(os.path.expanduser("~"), ".hermes", ".env")
    if os.path.exists(env):
        m = re.search(r"^TELEGRAPH_TOKEN\s*=\s*(.+)$", open(env, encoding="utf-8").read(), re.M)
        if m:
            return m.group(1).strip().strip('"\'')
    sys.exit("no Telegraph token: set TELEGRAPH_ACCESS_TOKEN or ~/.hermes/.env")


def call(method, payload):
    fd, tmp = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        cmd = ["curl", "-s", "-m", "40"]
        if SOCKS.strip():
            cmd += ["--socks5-hostname", SOCKS.strip()]
        cmd += ["-X", "POST", API + "/" + method,
                "-H", "Content-Type: application/json",
                "--data-binary", "@" + tmp]
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        return json.loads(out.stdout or "{}")
    finally:
        os.unlink(tmp)


def fix_title(base):
    """Fit base+marker into 60 chars by shortening BASE only.

    The marker is the contract; the headline is what gives way. If even the
    marker does not fit, say so instead of publishing something unlabelled.
    """
    suffix = " " + MARKER
    if len(suffix) >= TITLE_LIMIT:
        sys.exit("marker alone exceeds the %d-char limit" % TITLE_LIMIT)
    room = TITLE_LIMIT - len(suffix)
    if len(base) > room:
        base = base[: room - 1].rstrip(" ,-—:") + "…"
    return base + suffix


def main():
    md = open(ARTICLE, encoding="utf-8").read()
    base = md.splitlines()[0].lstrip("# ").strip()
    title = fix_title(base)
    if len(title) > TITLE_LIMIT:
        sys.exit("title is %d chars after shortening — refusing to publish" % len(title))

    nodes = _mod().md_to_dom(md)
    body = call("createPage", {
        "title": title,
        "author_name": os.environ.get("AUTHOR_NAME", ""),
        "author_url": "",
        "content": nodes,
        "return_content": "false",
    })
    if not body.get("ok"):
        sys.exit("createPage failed: %s" % json.dumps(body, ensure_ascii=False)[:400])

    r = body["result"]
    url = r["url"]
    page = url.rsplit("/", 1)[-1]
    print("url:      %s" % url)
    print("title:    %s (%d/%d chars)" % (r.get("title"), len(r.get("title", "")), TITLE_LIMIT))

    got = call("getPage", {"path": page, "return_content": "true"})
    raw = got.get("result", {}).get("content")
    parsed = json.loads(raw) if isinstance(raw, str) else raw
    if isinstance(parsed, str):
        parsed = json.loads(parsed)

    html = json.dumps(parsed, ensure_ascii=False)
    for w in LEAK_TERMS:
        if w in html:
            sys.exit("LEAK: %r reached the published page" % w)
    # UUID gate: term lists never cover identifiers, so a working realm or
    # entity UUID ships unnoticed while the enumeration says "clean". Match the
    # shape, not a known value.
    uuids = set(re.findall(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", html))
    if uuids:
        sys.exit("LEAK: %d UUID(s) reached the page: %s"
                 % (len(uuids), sorted(uuids)[:3]))
    print("nodes:    %d" % len(parsed))
    print("leaks:    %s" % (", ".join(LEAK_TERMS) or "no terms configured"))
    print("uuids:    0")
    print("\nCorrections must go through editPage on this path, never createPage again.")
    return url


if __name__ == "__main__":
    main()