#!/usr/bin/env python3
"""Publish article.md to Telegra.ph as a 2-part DRAFT with cross-links.

Telegra.ph CONTENT_TOO_BIG: ~18.7k chars of Russian text -> ~34 KB payload,
over the ~28 KB limit. Canon: split at a logical section boundary, publish
both parts, then fill real cross-links with editPage.
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
SPLIT = "## А дальше начинается пустота"
T1 = "35 официальных DevOps-скиллов: что взяли. Часть 1 (черновик)"
T2 = "А Kubernetes не нашёлся. Часть 2 (черновик)"

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
    out = subprocess.run(
        ["curl", "-s", "--socks5-hostname", "127.0.0.1:12334",
         "-H", "Content-Type: application/json",
         "--data-binary", "@" + tmp.replace("\\", "/"),
         "https://api.telegra.ph/" + ("createPage" if "path" not in payload else "editPage")],
        capture_output=True, text=True, timeout=90,
    )
    return json.loads(out.stdout)


def main(md_path):
    md = open(md_path, encoding="utf-8").read()
    md = re.sub(r"\A---\n.*?\n---\n", "", md, flags=re.S)
    md = re.sub(r"\A#\s+.*\n", "", md, count=1)
    part2, part1 = md.split(SPLIT, 1)
    part1 = part1.rstrip() + "\n\nПродолжение - вторая часть.\n"
    part2 = SPLIT + part2
    part2 = ("В первой части разбор того, что нашлось у поставщиков "
             "инструментов: Docker, HashiCorp, Grafana, GitHub.\n\n" + part2)

    r2 = api({"access_token": TOKEN, "title": T2, "author_name": AUTHOR,
              "author_url": "https://hermes-agent.ru",
              "content": tpd.md_to_dom(part2)})
    if not r2.get("ok"):
        sys.exit("part2 failed: " + str(r2.get("error"))[:200])
    p2 = r2["result"]["path"]
    print("PART2:", r2["result"]["url"])

    link1 = "Продолжение - вторая часть: [А Kubernetes не нашёлся](/%s)\n\n" % p2
    r1 = api({"access_token": TOKEN, "title": T1, "author_name": AUTHOR,
              "author_url": "https://hermes-agent.ru",
              "content": tpd.md_to_dom(link1 + part1)})
    if not r1.get("ok"):
        sys.exit("part1 failed: " + str(r1.get("error"))[:200])
    p1 = r1["result"]["path"]
    print("PART1:", r1["result"]["url"])

    link2 = ("Первая часть: [что взяли у поставщиков](/%s)\n\n" % p1)
    r2e = api({"access_token": TOKEN, "path": p2, "title": T2,
               "author_name": AUTHOR, "author_url": "https://hermes-agent.ru",
               "content": tpd.md_to_dom(link2 + part2)})
    print("PART2 EDIT:", r2e.get("ok"), r2e.get("result", {}).get("url", ""))
    json.dump({"path1": p1, "url1": r1["result"]["url"],
               "path2": p2, "url2": r2["result"]["url"]},
              open(os.path.join(os.path.dirname(md_path), "telegraph-draft.json"), "w"),
              ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main(sys.argv[1])
