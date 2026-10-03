"""Опубликовать черновик статьи на Telegra.ph С КАРТИНКАМИ.

Канон (writer -> telegraph-publish-images): родной скрипт полезен только как
КОНВЕРТЕР. Сеть в этой машине: api.telegra.ph отвечает только через SOCKS5,
requests без socks падает на CONNECT. Поэтому md_to_dom заимствуется из
telegraph-publish-images.py, а сам вызов createPage идёт через curl с
--socks5-hostname и payload во временном файле на нативном пути
(curl не ест MSYS-пути в --data-binary).

createPage вызывается ОДИН РАЗ. Дальше все правки - editPage того же path.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

ARTICLE = sys.argv[1]
TITLE = sys.argv[2]
AUTHOR = sys.argv[3]
CONVERTER = os.path.expanduser(
    r"~\AppData\Local\hermes\skills\content\writer\scripts\telegraph-publish-images.py")
SOCKS = "127.0.0.1:12334"
API = "https://api.telegra.ph"
TITLE_MAX = 60
MARKER = "ЧЕРНОВИК"
LEAKS = ("n.gusev", "<local-path>hermes-agent.ru", "llm.pii-guard", "shturman",
         "nikolaygusev", "channel-materials", "10.0.0.")
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def token():
    env = os.path.expanduser("~/.hermes/.env")
    for line in open(env, encoding="utf-8"):
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


def main():
    if len(TITLE) > TITLE_MAX:
        sys.exit("заголовок %d симв. при лимите %d - маркер срежется" % (len(TITLE), TITLE_MAX))
    if MARKER not in TITLE:
        sys.exit("в заголовке нет маркера черновика")

    spec = importlib.util.spec_from_file_location("tg_img", CONVERTER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    md = open(ARTICLE, encoding="utf-8").read()
    dom = mod.md_to_dom(md)

    # img-ноды обязаны быть голыми, без figcaption, и с абсолютным src
    imgs = [n for n in dom if n.get("tag") == "img"]
    figs = [n for n in dom if n.get("tag") in ("figure", "figcaption")]
    for n in imgs:
        src = n.get("attrs", {}).get("src", "")
        if not src.startswith("http"):
            sys.exit("img.src не абсолютный: %r" % src)
    print("в DOM: img=%d figure=%d figcaption=%d" % (len(imgs), len(figs), len(figs)))
    if not imgs:
        sys.exit("img-нод нет - публиковать нечего, статья пойдёт без иллюстраций")
    if figs:
        sys.exit("figure/figcaption в DOM - канон требует голую img-ноду")

    body = call("createPage", {
        "access_token": token(),
        "title": TITLE,
        "author_name": AUTHOR,
        "author_url": "",
        "content": dom,
        "return_content": "false",
    })
    if not body.get("ok"):
        sys.exit("createPage: " + json.dumps(body, ensure_ascii=False)[:400])
    url = body["result"]["url"]
    path = url.rsplit("/", 1)[-1]
    print("url:    %s" % url)
    print("path:   %s" % path)

    got = call("getPage", {"path": path, "return_content": "true"})
    raw = got.get("result", {}).get("content", [])
    nodes = raw if isinstance(raw, list) else json.loads(raw or "[]")
    blob = json.dumps(nodes, ensure_ascii=False)
    title_live = got.get("result", {}).get("title", "")
    print("--- гейт по ЖИВОЙ странице ---")
    print("img-нод:            %d" % blob.count('"tag": "img"'))
    print("img src на месте:   %s" % all(i["attrs"]["src"] in blob for i in imgs))
    print("markdown-остаток:   %d (<p>!<a href=)" % blob.count("<p>!<a href="))
    print("em-dash:            %d" % blob.count("\u2014"))
    print("guillemets:         %d" % (blob.count("\u00ab") + blob.count("\u00bb")))
    print("title на живой:     %r (%d)" % (title_live, len(title_live)))
    print("маркер на живой:    %s" % ("да" if MARKER in title_live else "НЕТ"))
    leaked = [w for w in LEAKS if w.lower() in blob.lower()]
    print("утечки:             %s" % (leaked or "нет"))
    print("uuid:               %d" % len(UUID.findall(blob)))

    fail = []
    if blob.count('"tag": "img"') != len(imgs):
        fail.append("img-нод на странице != %d" % len(imgs))
    if not all(i["attrs"]["src"] in blob for i in imgs):
        fail.append("не все img.src попали на страницу")
    if blob.count("<p>!<a href="):
        fail.append("markdown картинки не сконвертирован")
    if blob.count("\u2014") or blob.count("\u00ab") or blob.count("\u00bb"):
        fail.append("типографика не чистая")
    if MARKER not in title_live:
        fail.append("маркер черновика не на живой странице")
    if leaked:
        fail.append("утечка: %s" % leaked)
    if UUID.findall(blob):
        fail.append("uuid на странице")
    if fail:
        sys.exit("ГЕЙТ НЕ ПРОЙДЕН: " + "; ".join(fail))
    print("\nГЕЙТ ПРОЙДЕН. Финал = editPage этого path, маркер снимается последним шагом.")


if __name__ == "__main__":
    main()
