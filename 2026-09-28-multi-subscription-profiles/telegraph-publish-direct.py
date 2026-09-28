#!/usr/bin/env python3
"""
Direct Telegra.ph publishing via API - no subprocess, no timeout issues.
"""

import sys
import os
import json
import re
import requests


def get_token():
    """Read TELEGRAPH_TOKEN from ~/.hermes/.env."""
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.strip().startswith("TELEGRAPH_TOKEN="):
                    return line.strip().partition("=")[2].strip()
    return None


def md_to_dom(md):
    """Convert simple markdown to Telegra.ph DOM nodes."""
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

        if line.startswith("#### "):
            dom.append({"tag": "h4", "children": [line[5:].strip()]})
        elif line.startswith("### "):
            dom.append({"tag": "h3", "children": [line[4:].strip()]})
        elif line.startswith("## "):
            dom.append({"tag": "h3", "children": [line[3:].strip()]})
        elif line.startswith("# "):
            dom.append({"tag": "h3", "children": [line[2:].strip()]})
        elif line.strip() == "---":
            dom.append({"tag": "hr"})
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            items = []
            while i < len(lines) and (
                lines[i].strip().startswith("- ") or lines[i].strip().startswith("* ")
            ):
                items.append({"tag": "li", "children": inline_to_nodes(lines[i].strip()[2:])})
                i += 1
            dom.append({"tag": "ul", "children": items})
            continue
        elif line.strip() == "":
            pass
        else:
            text = line.strip()
            dom.append({"tag": "p", "children": inline_to_nodes(text)})

        i += 1

    return dom


def inline_to_nodes(text):
    """Convert inline markdown (bold, inline-code, [link](url)) to DOM array."""
    # tokenize: keep delimiters for ** **, ` `, [ ]( ) and plain text
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        # link  [label](url)
        lnk = re.search(r'\[([^\]]*)\]\(([^)]+)\)', text[i:])
        if lnk and lnk.start() == 0:
            tokens.append(("link", lnk.group(1), lnk.group(2)))
            i += lnk.end()
            continue
        # bold **...**
        if text[i:i+2] == "**":
            close = text.find("**", i+2)
            if close != -1:
                tokens.append(("bold", text[i+2:close]))
                i = close + 2
                continue
        # inline code `...`
        if text[i] == "`":
            close = text.find("`", i+1)
            if close != -1:
                tokens.append(("code", text[i+1:close]))
                i = close + 1
                continue
        # accumulate plain text until next special
        j = i
        while j < n and text[j] != "`" and text[j:j+2] != "**" and not text[j:].startswith("["):
            j += 1
        if j > i:
            tokens.append(("text", text[i:j]))
            i = j
        else:
            tokens.append(("text", text[i]))
            i += 1

    out = []
    for tok in tokens:
        if tok[0] == "text":
            out.append(tok[1])
        elif tok[0] == "bold":
            out.append({"tag": "strong", "children": [tok[1]]})
        elif tok[0] == "code":
            out.append({"tag": "code", "children": [tok[1]]})
        elif tok[0] == "link":
            out.append({"tag": "a", "attrs": {"href": tok[2]}, "children": [tok[1]]})
    # Telegra.ph требует children как МАССИВ, не строку - ВСЕГДА возвращаем list
    return [x for x in out if x != ""]


def publish(title, author, md_content, author_url="https://hermes-agent.ru"):
    """Publish article to Telegra.ph. Returns (ok, url_or_error)."""
    token = get_token()

    if not token:
        resp = requests.post(
            "https://api.telegra.ph/createAccount",
            json={"short_name": "Hermes Agent", "author_name": author},
            timeout=15,
        )
        data = resp.json()
        if not data.get("ok"):
            return False, data.get("error", "createAccount failed")
        token = data["result"]["access_token"]
        env_path = os.path.expanduser("~/.hermes/.env")
        with open(env_path, "a") as f:
            f.write(f"\nTELEGRAPH_TOKEN={token}\n")

    content = md_to_dom(md_content)

    resp = requests.post(
        "https://api.telegra.ph/createPage",
        json={
            "access_token": token,
            "title": title,
            "author_name": author,
            "author_url": author_url,
            "content": content,
        },
        timeout=20,
    )

    data = resp.json()
    if data.get("ok"):
        return True, data["result"]["url"]
    return False, data.get("error", "createPage failed")


def verify(path):
    """Check published page for em-dashes and guillemets."""
    resp = requests.get(
        f"https://api.telegra.ph/getPage/{path}?return_content=true", timeout=15
    )
    data = resp.json()
    if not data.get("ok"):
        return {"error": data.get("error")}
    content_str = json.dumps(data["result"]["content"])
    return {
        "em_dashes": content_str.count("\u2014"),
        "guillemets": content_str.count("\u00ab") + content_str.count("\u00bb"),
        "title": data["result"]["title"],
        "views": data["result"].get("views", 0),
    }


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: telegraph-publish-direct.py 'Title' 'Author' /path/to/article.md")
        sys.exit(1)

    title = sys.argv[1]
    author = sys.argv[2]
    article_path = sys.argv[3]

    with open(article_path) as f:
        md = f.read()

    ok, result = publish(title, author, md)
    if ok:
        print(f"URL: {result}")
        path = result.split("/telegra.ph/")[-1] if "/telegra.ph/" in result else result.split("/")[-1]
        ver = verify(path)
        print(f"Verify: em_dashes={ver.get('em_dashes', '?')}, guillemets={ver.get('guillemets', '?')}")
    else:
        print(f"Error: {result}")
        sys.exit(1)
