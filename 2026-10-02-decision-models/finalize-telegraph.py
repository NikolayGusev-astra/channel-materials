"""Finalise the two Telegra.ph drafts.

Does three things on the SAME pages (same token, never createAccount):
  1. rebuilds the DOM from the cleaned part-N.md files - the publisher kept the
     YAML frontmatter and a duplicated H1 as visible paragraphs;
  2. strips the "(ЧЕРНОВИК для вычитки)" marker from the page title;
  3. prefixes the cover image on part 1 only.

Idempotent: rerunning rewrites identical content.
"""
import importlib.util
import json
import os
import sys
import urllib.parse
import urllib.request

for _k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(_k, None)

# api.telegra.ph from this host only answers through SOCKS5; the env proxy
# handler must stay disabled or CONNECT gets hijacked.
import socks
import socket

socket.socket = socks.socksocket
socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 12334, rdns=True)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

API = "https://api.telegra.ph"
COVER = "https://hermes-agent.ru/decision-models/cover.png"
HERE = os.path.dirname(os.path.abspath(__file__))
PUBLISHER = os.path.expanduser(
    r"~\AppData\Local\hermes\skills\content\writer\scripts\telegraph-publish-direct.py")

PAGES = [
    ("part-1.md",
     "CHetyre-decision-modeli-za-nedelyu-Jev-klass-vyshel-iz-tupika-CHERNOVIK-dlya-vychitki---chast-1-iz-2-10-02",
     "Четыре decision-модели за неделю: Jev-класс вышел из тупика (часть 1 из 2)", True),
    ("part-2.md",
     "CHetyre-decision-modeli-za-nedelyu-gde-primenyat-i-chto-vybrat-CHERNOVIK-dlya-vychitki---chast-2-iz-2-10-02",
     "Четыре decision-модели за неделю: где применять и что выбрать (часть 2 из 2)", False),
]


def load_publisher():
    spec = importlib.util.spec_from_file_location("tgpub", PUBLISHER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def token():
    env = os.path.expanduser("~/.hermes/.env")
    with open(env) as f:
        for line in f:
            if line.strip().startswith("TELEGRAPH_TOKEN="):
                return line.strip().partition("=")[2].strip()
    sys.exit("TELEGRAPH_TOKEN not found")


def call(method, payload):
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(f"{API}/{method}", data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    return json.load(opener.open(req, timeout=60))


def main():
    pub = load_publisher()
    tok = token()
    for md_name, path, title, with_cover in PAGES:
        with open(os.path.join(HERE, md_name), encoding="utf-8") as f:
            nodes = pub.md_to_dom(f.read())
        if with_cover and not any(n.get("tag") == "img" for n in nodes):
            nodes = [{"tag": "img", "attrs": {"src": COVER}}] + nodes
        res = call("editPage", {
            "access_token": tok, "path": path, "title": title,
            "author_name": "Гусев Николай",
            "author_url": "https://hermes-agent.ru",
            "content": json.dumps(nodes, ensure_ascii=False),
        })
        print(f"{path[:44]} ok={res.get('ok')} nodes={len(nodes)} "
              f"url={res.get('result', {}).get('url')}", flush=True)


if __name__ == "__main__":
    main()