#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Audit an ALREADY published Telegra.ph page. Creates nothing.

Separate from any publish script on purpose: re-running a publisher to "check"
spawns a duplicate page. Verify by path against the page you already have.
This is the verification half of a publish gate - the DoD of the last step is
"the draft is clean", not "published".

Usage:
    python telegraph-verify.py <path-slug>

Exit code 0 only when every gate passes, so it can be used in a pipeline.
"""

import json
import os
import re
import subprocess
import sys

SOCKS = "127.0.0.1:12334"   # telegra.ph is unreachable without it on this network
API = "https://api.telegra.ph"

# Substrings that must never appear in a published page.
LEAK_PATTERNS = [
    r"ontonet\.ru", r"\b\d{10}\b", r"n\.gusev", r"NikolayGusev",
    r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    r"/Users/[a-z]", r"C:\\\\Users\\\\[a-z]",
]


def curl(url):
    cmd = ["curl", "-s", "--socks5-hostname", SOCKS, "-m", "40", url]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        sys.exit("curl failed (%d): %s" % (out.returncode, out.stderr[:300]))
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        sys.exit("non-JSON from %s:\n%s" % (url, out.stdout[:300]))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1].strip().strip("/")

    page = curl("%s/getPage/%s?return_content=true" % (API, path))
    if not page.get("ok"):
        sys.exit("getPage failed: %s" % json.dumps(page, ensure_ascii=False)[:300])
    result = page["result"]

    # getPage returns content already parsed as a list, NOT a JSON string
    raw = result.get("content", [])
    content = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
    nodes = len(raw) if isinstance(raw, list) else len(json.loads(raw or "[]"))

    title = result.get("title", "")
    em = content.count("\u2014") + content.count("&#8212;")
    gu = content.count("\u00ab") + content.count("\u00bb")
    leaks = [p for p in LEAK_PATTERNS if re.search(p, content)]
    md_left = content.count("](")

    print("title:      %s" % title)
    print("url:        https://telegra.ph/%s" % path)
    print("nodes:      %d" % nodes)
    print("img nodes:  %d" % content.count('"tag": "img"'))
    print("pre nodes:  %d" % content.count('"tag": "pre"'))
    print("h3 nodes:   %d" % content.count('"tag": "h3"'))
    print("em-dash:    %d  (must be 0)" % em)
    print("guillemets: %d  (must be 0)" % gu)
    print("md leftovers: %d  (must be 0)" % md_left)
    print("leaks:      %s" % (leaks or "none"))

    # A draft MUST be visibly marked, otherwise it reads as a published page.
    if "\u0427\u0415\u0420\u041d\u041e\u0412\u0418\u041a" in title:
        print("draft mark: present")
    else:
        print("draft mark: ABSENT  (ok only for a final version)")
    if len(title) > 60:
        print("WARNING: title exceeds 60 chars and was likely truncated by the API")

    ok = em == 0 and gu == 0 and not leaks and md_left == 0 and nodes > 20
    print("---")
    print("VERDICT: %s" % ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
