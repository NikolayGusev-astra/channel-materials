#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verify an ALREADY published Telegra.ph page. Creates nothing.

Every check here hits the live API. A local file proves nothing about what a
reader actually gets.

WHY THIS IS A DoD AND NOT A STYLING PASS
    The page has to satisfy facts, not taste: it exists, the illustration is
    really an <img> (a markdown image that stayed a link is invisible in the
    API response yet renders as dead text for the reader), no long dashes or
    guillemets survived the converter, no leftover markdown, and nothing
    internal leaked.

PUBLIC-DRAFT CONTRACT
    Telegra has no private draft: a page is public the instant createPage
    returns. The review state lives in the TITLE, so the title is checked for
    the marker here. A page that lost the marker is unlabelled public content.

Env
    TELEGRAPH_PATH    required, page slug without https://
    PUBLIC_IMG_HOST   optional, host allowed to serve images, default our own
    SOCKS             optional host:port, empty = direct
    LEAK_TERMS        optional comma-separated internal names that must not
                      appear in prose (your own hostnames, ids, logins)
"""

import json
import os
import re
import subprocess
import sys

API = "https://api.telegra.ph"
PATH = os.environ.get("TELEGRAPH_PATH", "")
SOCKS = os.environ.get("SOCKS", "")
PUBLIC_IMG_HOST = os.environ.get("PUBLIC_IMG_HOST", "https://hermes-agent.ru/")
DRAFT_MARKER = "ЧЕРНОВИК"
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
IMG_SRC_RE = re.compile(r'"src"\s*:\s*"([^"]*)"')


def curl(url):
    cmd = ["curl", "-s", "-m", "50"]
    if SOCKS:
        cmd += ["--socks5-hostname", SOCKS]
    cmd += [url]
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if out.returncode != 0:
        sys.exit("curl failed (%d): %s" % (out.returncode, out.stderr[:300]))
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        sys.exit("non-JSON:\n%s" % out.stdout[:300])


def img_srcs(text):
    return IMG_SRC_RE.findall(text)


def prose_without_srcs(text):
    """Page text with img src values removed.

    An illustration must live on a public host, so a blanket domain ban flags
    the article's own artwork. The same host in PROSE is still a leak.
    """
    return IMG_SRC_RE.sub('"src":""', text)


def leak_terms():
    extra = [w.strip() for w in os.environ.get("LEAK_TERMS", "").split(",") if w.strip()]
    return tuple(extra) + ("192.168.", "10\\.")


def main():
    if not PATH:
        sys.exit("set TELEGRAPH_PATH to the page slug")
    page = curl("%s/getPage/%s?return_content=true" % (API, PATH))
    if not page.get("ok"):
        sys.exit("getPage failed: %s" % json.dumps(page, ensure_ascii=False)[:300])

    result = page["result"]
    raw = result.get("content", [])
    content = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
    nodes = len(raw) if isinstance(raw, list) else len(json.loads(raw or "[]"))
    title = result.get("title", "")

    print("title:      %s (%d chars)" % (title, len(title)))
    print("url:        https://telegra.ph/%s" % PATH)
    print("nodes:      %d" % nodes)
    print("img nodes:  %d" % content.count('"tag": "img"'))
    print("pre nodes:  %d" % content.count('"tag": "pre"'))
    print("h3 nodes:   %d" % content.count('"tag": "h3"'))

    # typography gate
    em = content.count("\u2014") + content.count("&#8212;")
    gu = content.count("\u00ab") + content.count("\u00bb")
    print("em-dash:    %d  (must be 0)" % em)
    print("guillemets: %d  (must be 0)" % gu)

    # leak gate. Two questions, two checks:
    #   prose   — internal names must not appear as text at all;
    #   img src — only PUBLIC_IMG_HOST may serve an image, because Telegra
    #             has to fetch it and nothing internal is reachable from here.
    prose = prose_without_srcs(content)
    leaks = [w for w in leak_terms() if w in prose]

    srcs = img_srcs(content)
    bad_srcs = [s for s in srcs if not s.startswith(PUBLIC_IMG_HOST)]
    if bad_srcs:
        leaks.append("non-public img src: %s" % bad_srcs[:2])

    print("img srcs:   %s" % (srcs or "none"))
    print("leaks:      %s" % (leaks or "none"))

    # UUID gate: any realm/entity/diagram UUID reaching a public page.
    # A term list never covers identifiers — they are new every time — so this
    # one matches the shape. A working realm UUID shipped unnoticed once
    # because the enumeration above reported "none".
    uuids = set(UUID_RE.findall(content))
    print("uuids:      %d  (must be 0)  %s"
          % (len(uuids), sorted(uuids)[:3] if uuids else ""))

    md = content.count("](")
    print("md leftovers: %d  (must be 0)" % md)

    # Draft marker: a report, not a verdict. Telegra has no private draft, so
    # the title marker is how a reader is told this text is still under review.
    # Which side of the line the page is on depends on where it is being read
    # from, so FAILING on a missing marker only makes sense while it is still a
    # review URL. The version-publish gate checks the marker; this DoD reports
    # it and never fails on it.
    marker = "есть" if DRAFT_MARKER in title else "снят (финальная версия)"
    print("draft mark: %s" % marker)

    ok = (em == 0 and gu == 0 and not leaks and not uuids and md == 0 and nodes > 20)
    print("---")
    print("VERDICT: %s" % ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()