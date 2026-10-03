"""Обновить черновик на Telegra.ph через editPage того же path.

Канон: createPage вызывается один раз. Любые правки - editPage с тем же path.
Контент берётся из article-tg.md (подготовлен: frontmatter снят, H1 первой
строкой, img.src абсолютные). createPage здесь НЕ вызывается никогда.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

ARTICLE, PATH, TITLE, AUTHOR = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
CONVERTER = os.path.expanduser(
    r"~\AppData\Local\hermes\skills\content\writer\scripts\telegraph-publish-images.py")
SOCKS = "127.0.0.1:12334"
API = "https://api.telegra.ph"
TITLE_MAX = 60
MARKER = "ЧЕРНОВИК"
LEAKS = ("n.gusev", "C:/Users", "/c/Users", "hermes-agent.ru", "llm.pii-guard",
         "shturman.ai", "gusev@", "@gusev", "10.0.0.", "192.168.", "password", "api_key")
UUID = __import__("re").compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def token():
    for line in open(os.path.expanduser("~/.hermes/.env"), encoding="utf-8"):
        if line.strip().startswith("TELEGRAPH_TOKEN="):
            t = line.strip().partition("=")[2].strip().strip('"').strip("'")
            if t and "{" not in t:
                return t
    sys.exit("нет TELEGRAPH_TOKEN")


def call(method, payload):
    fd, tmp = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    try:
        out = subprocess.run(
            ["curl", "-s", "-m", "50", "--socks5-hostname", SOCKS,
             "-X", "POST", "%s/%s" % (API, method),
             "-H", "Content-Type: application/json",
             "--data-binary", "@" + tmp],
            capture_output=True, text=True, encoding="utf-8").stdout
        return json.loads(out or "{}")
    finally:
        os.unlink(tmp)


def audit(blob, title, expect_imgs, quiet=False):
    leaked = [w for w in LEAKS if w.lower() in blob.lower()]
    checks = {
        "img-нод": (blob.count('"tag": "img"'), expect_imgs),
        "figcaption": (blob.count('"tag": "figcaption"'), 0),
        "markdown-остаток": (blob.count("<p>!<a href="), 0),
        "em-dash": (blob.count("\u2014"), 0),
        "guillemets": (blob.count("\u00ab") + blob.count("\u00bb"), 0),
        "uuid": (len(UUID.findall(blob)), 0),
        "длина title": (len(title), None),
        "маркер": (1 if MARKER in title else 0, 1),
        "утечки": (len(leaked), 0),
    }
    if not quiet:
        for k, (got, want) in checks.items():
            print("%-18s %s" % (k + ":", got if want is None else ("%s (ждём %s)" % (got, want))))
    bad = [k for k, (got, want) in checks.items() if want is not None and got != want]
    return bad, leaked


def main():
    spec = importlib.util.spec_from_file_location("tg_img", CONVERTER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    dom = mod.md_to_dom(open(ARTICLE, encoding="utf-8").read())
    imgs = [n for n in dom if n.get("tag") == "img"]
    for n in imgs:
        if not n.get("attrs", {}).get("src", "").startswith("http"):
            sys.exit("img.src не абсолютный")

    res = call("editPage", {
        "path": PATH, "access_token": token(), "title": TITLE,
        "author_name": AUTHOR, "author_url": "",
        "content": dom, "return_content": "false",
    })
    if not res.get("ok"):
        sys.exit("editPage: " + json.dumps(res, ensure_ascii=False)[:400])
    print("edit ok: %s" % res["result"].get("url"))

    got = call("getPage", {"path": PATH, "return_content": "true"})
    raw = got.get("result", {}).get("content", [])
    nodes = raw if isinstance(raw, list) else json.loads(raw or "[]")
    blob = json.dumps(nodes, ensure_ascii=False)
    title = got.get("result", {}).get("title", "")
    print("--- гейт по живой странице ---")
    bad, leaked = audit(blob, title, len(imgs))
    print("узлов:              %d" % len(nodes))
    if bad:
        sys.exit("ГЕЙТ НЕ ПРОЙДЕН: " + "; ".join(bad) + (" утечки: %s" % leaked if leaked else ""))
    print("\nГЕЙТ ПРОЙДЕН. Страница та же, createPage не вызывался.")


if __name__ == "__main__":
    main()
