#!/usr/bin/env python3
"""Publish article.md to Telegra.ph as 3-part DRAFT with real cross-links.

Measured limit: ~14k chars of Russian prose per page passes, 16.6k returns
CONTENT_TOO_BIG. Article is 30.4k, so three parts. Markdown images are stripped:
telegraph-publish-direct.py has no img-node support, and the image URLs only
become absolute after the site publish. Images ship with the site version.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

SKILL = r"<local-path>\Users\n.gusev\AppData\Local\hermes\skills\content\writer\scripts\telegraph-publish-direct.py"
AUTHOR = "Гусев Николай"
SPLITS = ["## Чего официального нет вообще", "## Как это грузится: диспетчер"]
TITLES = [
    "DevOps-скиллы для агента: 35 официальных, 111 своих. Часть 1 (черновик)",
    "Пустота под Kubernetes. Часть 2 (черновик)",
    "Свои скиллы, приоритет, грабли. Часть 3 (черновик)",
]

spec = importlib.util.spec_from_file_location("tpd", SKILL)
tpd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tpd)
TOKEN = tpd.get_token()
if not TOKEN:
    sys.exit("no TELEGRAPH_TOKEN in ~/.hermes/.env")


def api(payload):
    tmp = os.path.join(tempfile.gettempdir(), "telegraph_payload.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    endpoint = "editPage" if "path" in payload else "createPage"
    out = subprocess.run(
        ["curl", "-s", "--socks5-hostname", "127.0.0.1:12334",
         "-H", "Content-Type: application/json",
         "--data-binary", "@" + tmp.replace("\\", "/"),
         "https://api.telegra.ph/" + endpoint],
        capture_output=True, text=True, timeout=120,
    )
    return json.loads(out.stdout)


def create(title, body):
    return api({"access_token": TOKEN, "title": title, "author_name": AUTHOR,
                "author_url": "https://hermes-agent.ru", "content": tpd.md_to_dom(body)})


def main(md_path):
    md = re.sub(r"\A---\n.*?\n---\n", "", open(md_path, encoding="utf-8").read(), flags=re.S)
    md = re.sub(r"\A#\s+.*\n", "", md, count=1)
    md = re.sub(r"(?m)^!\[[^\]]*\]\([^)]+\)\n?", "", md)

    chunks = []
    rest = md
    for s in SPLITS:
        head, rest = rest.split(s, 1)
        chunks.append(head)
    chunks.append(rest)

    paths, urls = [], []
    for i, body in enumerate(chunks):
        r = create(TITLES[i], body)
        if not r.get("ok"):
            print("FAIL part", i + 1, r.get("error"), "len", len(body))
            sys.exit(1)
        paths.append(r["result"]["path"])
        urls.append(r["result"]["url"])
        print(f"PART{i+1}: {r['result']['url']}  ({len(body)} chars)")

    for i in range(len(paths)):
        nav = " ".join(
            "[Часть %d](/%s)" % (j + 1, paths[j]) if j != i else "Часть %d" % (i + 1)
            for j in range(len(paths)))
        e = api({"access_token": TOKEN, "path": paths[i], "title": TITLES[i],
                 "author_name": AUTHOR, "author_url": "https://hermes-agent.ru",
                 "content": tpd.md_to_dom(nav + "\n\n" + chunks[i])})
        print(f"EDIT{i+1}:", e.get("ok"))

    json.dump({"paths": paths, "urls": urls}, open(
        os.path.join(os.path.dirname(md_path), "telegraph-draft.json"), "w"),
        ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main(sys.argv[1])
