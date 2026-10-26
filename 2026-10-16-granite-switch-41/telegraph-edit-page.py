"""Update an existing Telegraph page (editPage) from markdown, with images.

Adapted from telegraph-publish-images.py: reuses md_to_dom/inline_to_nodes
(image-aware) and swaps createPage -> editPage on the existing path.
"""
import json
import os
import re
import urllib.request
import urllib.parse


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


def inline_to_nodes(text):
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
                raise SystemExit("img src must be absolute http(s) URL, got: " + url)
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


def api(method, payload):
    url = "https://api.telegra.ph/" + method
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def main():
    title, author, path, md_path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    with open(md_path, encoding="utf-8") as f:
        md = f.read()
    # Drop the leading "# Title" heading — it is passed as the page title.
    if md.startswith("# "):
        md = md.split("\n", 1)[1].lstrip("\n")
    content = md_to_dom(md)
    token = get_token()
    d = api(
        "editPage",
        {
            "access_token": token,
            "path": path,
            "title": title,
            "author_name": author,
            "content": content,
        },
    )
    if not d.get("ok"):
        raise SystemExit("editPage failed: " + str(d.get("error")))
    # verify
    chk = json.load(
        urllib.request.urlopen(
            urllib.request.Request(
                "https://api.telegra.ph/getPage/"
                + path
                + "?return_content=true&format=json"
            ),
            timeout=20,
        )
    )
    c = json.dumps(chk.get("result", {}).get("content", ""), ensure_ascii=False)
    print("URL: https://telegra.ph/" + path)
    print(
        "verify: em_dashes=%d, guillemets=%d, img_nodes=%d"
        % (
            c.count("\u2014"),
            c.count("\u00ab") + c.count("\u00bb"),
            c.count('"tag": "img"'),
        )
    )


if __name__ == "__main__":
    import sys
    main()
