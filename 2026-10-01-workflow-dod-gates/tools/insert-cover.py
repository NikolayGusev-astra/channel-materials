#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Insert the cover illustration into an existing Telegra.ph page, IN PLACE.

WHY editPage AND NOT createPage
    createPage always mints a NEW path. Calling it twice leaves an orphan page
    that nobody can find or fix, and the draft the reviewer already holds keeps
    its old content. Corrections always go through editPage on the same path.

IDEMPOTENT
    Re-running is safe: if the content already carries an image, the page is
    published as-is instead of stacking a second copy. The caller can therefore
    retry after a network failure without inspecting the page by hand first.

Env
    ARTICLE               optional, markdown source, default article.md
    COVER_URL             required, absolute PUBLIC url of the illustration
                          (Telegra fetches it; a relative path is a 404)
    COVER_CAPTION         required, the figcaption text and img alt
    TELEGRAPH_PATH        required, page slug without https://
    TELEGRAPH_CONVERTER   optional, module exposing md_to_dom(markdown)
    SOCKS                 optional host:port, empty = direct
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

API = "https://api.telegra.ph"
PATH = os.environ.get("TELEGRAPH_PATH", "")
SOCKS = os.environ.get("SOCKS", "")
ARTICLE = os.environ.get("ARTICLE", "article.md")
COVER = os.environ.get("COVER_URL", "")
CAPTION = os.environ.get("COVER_CAPTION", "")
TITLE = os.environ.get("TELEGRAPH_TITLE", "")
_CONV = os.environ.get("TELEGRAPH_CONVERTER", "telegraph-publish-direct.py")
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def need(value, name):
    if not value:
        sys.exit("set %s" % name)


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
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
        tmp = f.name
    try:
        cmd = ["curl", "-s", "-m", "50"]
        if SOCKS:
            cmd += ["--socks5-hostname", SOCKS]
        cmd += ["-X", "POST", API + "/" + method,
                "-H", "Content-Type: application/json",
                "--data-binary", "@" + tmp]
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8").stdout
        return json.loads(out or "{}")
    finally:
        os.unlink(tmp)


def converter():
    """importlib, not import: converter filenames usually contain hyphens."""
    spec = importlib.util.spec_from_file_location("telegraph_convert", _CONV)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    need(PATH, "TELEGRAPH_PATH")
    need(COVER, "COVER_URL")
    need(CAPTION, "COVER_CAPTION")

    md = open(ARTICLE, encoding="utf-8").read()
    nodes = converter().md_to_dom(md)

    # Idempotency is checked against the LIVE page, not against the markdown.
    # The source has no image (the cover is referenced from the site, not
    # inlined), so testing `nodes` would insert a second copy on every retry —
    # the markdown-driven check I wrote first was exactly that wrong.
    live = call("getPage", {"path": PATH, "return_content": "true"})
    if live.get("ok") and COVER in json.dumps(live, ensure_ascii=False):
        print("cover already on the page, republishing without a duplicate")
        print("img nodes on page:", json.dumps(live, ensure_ascii=False).count('"tag": "img"'))
        return

    anchor = None
    for i, n in enumerate(nodes):
        if n.get("tag") in ("p", "h3") and "платформа" in json.dumps(n, ensure_ascii=False):
            anchor = i
            break
    if anchor is None:
        sys.exit("no anchor paragraph found; pass an explicit anchor instead of guessing")
    nodes[anchor:anchor] = [
        {"tag": "figure", "children": [
            {"tag": "img", "attrs": {"src": COVER, "alt": CAPTION}},
            {"tag": "figcaption", "children": [CAPTION]}]},
    ]
    print("img node inserted before node", anchor)

    payload = {
        "path": PATH,
        "access_token": token(),
        "title": TITLE,
        "author_name": os.environ.get("AUTHOR_NAME", ""),
        "author_url": "",
        "content": nodes,
        "return_content": "false",
    }
    res = call("editPage", payload)
    if not res.get("ok"):
        sys.exit("editPage failed: " + json.dumps(res, ensure_ascii=False)[:400])
    print("edit ok:", res["result"].get("url"))

    chk = call("getPage", {"path": PATH, "return_content": "true"})
    if not chk.get("ok"):
        sys.exit("getPage failed after edit: " + json.dumps(chk, ensure_ascii=False)[:300])
    html = json.dumps(chk, ensure_ascii=False)
    title = chk["result"].get("title", "")
    print("img nodes on page:", html.count('"tag": "img"'))
    print("cover url present:", COVER in html)
    print("uuids:", len(UUID_RE.findall(html)))
    print("title:", title, "(%d chars)" % len(title))
    print("draft marker in title:", "ЧЕРНОВИК" in title)

    bad = [k for k, want in (("img nodes on page", 1), ("cover url present", True),
                             ("uuids", 0), ("draft marker in title", True))
           if (html.count('"tag": "img"') if k == "img nodes on page"
               else len(UUID_RE.findall(html)) if k == "uuids"
               else (COVER in html) if k == "cover url present"
               else ("ЧЕРНОВИК" in title)) != want]
    if bad or len(title) > 60:
        sys.exit("post-edit check failed: %s" % (bad or "title over 60 chars"))


if __name__ == "__main__":
    main()