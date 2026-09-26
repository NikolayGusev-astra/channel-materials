"""Publish markdown to Telegra.ph WITH images (img nodes).

The canonical script (content/writer/scripts/telegraph-publish-direct.py) has no
image support at all: its inline_to_nodes() parses ![alt](url) as a normal link,
so illustrations silently degrade to clickable captions. This variant intercepts
image syntax before inline parsing and emits {"tag": "img", "attrs": {"src": ...}}.

Telegra.ph accepts ONLY absolute http(s) URLs in img.src. Relative paths 404.

Usage:
  python telegraph-publish-images.py 'Title' 'Author' /path/to/article.md
"""
import json
import os
import re
import sys

import requests


def get_token():
    env_path = os.path.expanduser("~/.hermes/.env")
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("TELEGRAPH_TOKEN="):
                    tok = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if tok and "{" not in tok:
                        return tok
    except OSError:
        pass
    return os.environ.get("TELEGRAPH_TOKEN", "")


def ensure_account(author):
    tok = get_token()
    if tok:
        return tok
    r = requests.post(
        "https://api.telegra.ph/createAccount",
        json={"short_name": "Hermes Agent", "author_name": author},
        timeout=20,
    )
    d = r.json()
    if not d.get("ok"):
        raise SystemExit("createAccount failed: " + str(d.get("error")))
    tok = d["result"]["access_token"]
    with open(os.path.expanduser("~/.hermes/.env"), "a", encoding="utf-8") as f:
        f.write(f"\nTELEGRAPH_TOKEN={tok}\n")
    return tok


def inline_to_nodes(text):
    """Inline markdown -> nodes. Image syntax is handled by caller, not here."""
    out = []
    pattern = re.compile(
        r"(\*\*[^*]+\*\*)|(\*[^*]+\*)|(`[^`]+`)|(\[[^\]]+\]\([^)]+\))"
    )
    pos = 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            out.append(text[pos : m.start()])
        tok = m.group(0)
        if tok.startswith("**"):
            out.append({"tag": "strong", "children": [tok[2:-2]]})
        elif tok.startswith("`"):
            out.append({"tag": "code", "children": [tok[1:-1]]})
        elif tok.startswith("["):
            lm = re.match(r"\[([^\]]+)\]\(([^)]+)\)", tok)
            href = lm.group(2)
            # telegra.ph silently drops absolute self-links
            if href.startswith("https://telegra.ph"):
                out.append(lm.group(1))
            else:
                out.append(
                    {"tag": "a", "attrs": {"href": href}, "children": [lm.group(1)]}
                )
        else:
            out.append({"tag": "em", "children": [tok[1:-1]]})
        pos = m.end()
    if pos < len(text):
        out.append(text[pos:])
    return out


IMG_RE = re.compile(r"^!\[([^\]]*)\]\(([^)\s]+)\)$")


def md_to_dom(md):
    dom = []
    lines = md.split("\n")
    i = 0
    in_code = False
    code_lines = []

    while i < len(lines):
        line = lines[i]

        if line.strip().startswith("```"):
            if in_code:
                dom.append({"tag": "pre", "children": ["\n".join(code_lines)]})
                code_lines = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue

        m = IMG_RE.match(line.strip())
        if m:
            alt, url = m.group(1), m.group(2)
            if not url.startswith("http"):
                raise SystemExit(
                    "img src must be absolute http(s) URL, got: " + url
                )
            # Telegra.ph: no figcaption by design - channel style is bare images.
            dom.append({"tag": "img", "attrs": {"src": url}})
            i += 1
            continue

        if line.startswith("#### "):
            dom.append({"tag": "h4", "children": [line[5:].strip()]})
        elif line.startswith("### ") or line.startswith("## ") or line.startswith("# "):
            dom.append({"tag": "h3", "children": [line.lstrip("#").strip()]})
        elif line.strip() == "---":
            dom.append({"tag": "hr"})
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            items = []
            while i < len(lines) and (
                lines[i].strip().startswith("- ") or lines[i].strip().startswith("* ")
            ):
                items.append(
                    {"tag": "li", "children": inline_to_nodes(lines[i].strip()[2:])}
                )
                i += 1
            dom.append({"tag": "ul", "children": items})
            continue
        elif line.strip():
            dom.append({"tag": "p", "children": inline_to_nodes(line.strip())})

        i += 1

    return dom


def main():
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    title, author, path = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(path, encoding="utf-8") as f:
        md = f.read()

    body = md.split("---", 2)[2].lstrip("\n") if md.startswith("---") else md
    content = md_to_dom(body)

    token = ensure_account(author)
    r = requests.post(
        "https://api.telegra.ph/createPage",
        json={
            "access_token": token,
            "title": title,
            "author_name": author,
            "author_url": "https://hermes-agent.ru",
            "content": content,
        },
        timeout=25,
    )
    d = r.json()
    if not d.get("ok"):
        raise SystemExit("createPage failed: " + str(d.get("error")))
    url = d["result"]["url"]
    short = url.rstrip("/").rsplit("/", 1)[-1]

    chk = requests.get(
        f"https://api.telegra.ph/getPage/{short}?return_content=true", timeout=20
    ).json()
    c = json.dumps(chk.get("result", {}).get("content", ""), ensure_ascii=False)
    print("URL:", url)
    print(
        "Verify: em_dashes=%d, guillemets=%d, img_nodes=%d, figcaptions=%d, abs_img_urls=%d"
        % (
            c.count("\u2014"),
            c.count("\u00ab") + c.count("\u00bb"),
            c.count('"tag": "img"'),
            c.count("figcaption"),
            c.count("https://hermes-agent.ru/project-profiles"),
        )
    )


if __name__ == "__main__":
    main()
