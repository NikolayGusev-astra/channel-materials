"""Верификация уже опубликованного черновика на Telegra.ph.

НЕ создаёт страницу. Канон: createPage вызывается один раз, дальше editPage
того же path; повторный createPage оставил бы сироту, которого никто не найдёт.

Запрещённые термины - инфраструктура и учётные данные владельца. Адрес
зеркала материалов (github.com/.../channel-materials) в список НЕ входит:
он публикуется в футере каждого поста канона, и img.src обязан быть
абсолютным URL рабочего хоста.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

PATH = sys.argv[1]
SOCKS = "127.0.0.1:12334"
API = "https://api.telegra.ph"
MARKER = "ЧЕРНОВИК"
LEAKS = ("n.gusev", "C:/Users", "/c/Users", "hermes-agent.ru", "llm.pii-guard",
         "shturman.ai", "gusev@", "@gusev", "10.0.0.", "192.168.", "POSTGRES",
         "password", "api_key")
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


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
    got = call("getPage", {"path": PATH, "return_content": "true"})
    if not got.get("ok"):
        sys.exit("getPage: " + json.dumps(got, ensure_ascii=False)[:300])
    res = got["result"]
    raw = res.get("content", [])
    nodes = raw if isinstance(raw, list) else json.loads(raw or "[]")
    blob = json.dumps(nodes, ensure_ascii=False)
    title = res.get("title", "")

    imgs = [n for n in nodes if n.get("tag") == "img"]
    srcs = [n.get("attrs", {}).get("src", "") for n in imgs]
    figs = blob.count('"tag": "figcaption"')

    print("title:              %r (%d симв.)" % (title, len(title)))
    print("маркер черновика:   %s" % ("да" if MARKER in title else "НЕТ - финальная версия"))
    print("узлов:             %d" % len(nodes))
    print("img-нод:           %d" % len(imgs))
    print("figcaption:         %d (канон: 0)" % figs)
    print("markdown-остаток:  %d" % blob.count("<p>!<a href="))
    print("pre-блоков:        %d" % blob.count('"tag": "pre"'))
    print("em-dash:           %d" % blob.count("\u2014"))
    print("guillemets:        %d" % (blob.count("\u00ab") + blob.count("\u00bb")))
    print("uuid:              %d" % len(UUID.findall(blob)))
    leaked = [w for w in LEAKS if w.lower() in blob.lower()]
    print("утечки:            %s" % (leaked or "нет"))

    print("--- картинки ---")
    for s in srcs:
        ok = s.startswith("http")
        code = subprocess.run(
            ["curl", "-sI", "--max-time", "25", s],
            capture_output=True, text=True, encoding="utf-8").stdout
        status = "?"
        for ln in code.split("\n"):
            if ln.startswith("HTTP/"):
                status = ln.split()[1]
        print("  %s  %s" % (status, s[-58:]))
        if not ok or status != "200":
            sys.exit("картинка не отдаёт 200: %s (%s)" % (status, s))

    fail = []
    if not imgs:
        fail.append("img-нод нет")
    if figs:
        fail.append("figcaption в кадре")
    if blob.count("<p>!<a href="):
        fail.append("markdown картинки не сконвертирован")
    if blob.count("\u2014") or blob.count("\u00ab") or blob.count("\u00bb"):
        fail.append("типографика не чистая")
    if leaked:
        fail.append("утечка: %s" % leaked)
    if UUID.findall(blob):
        fail.append("uuid на странице")
    if len(title) > 60:
        fail.append("заголовок длиннее 60")
    if fail:
        sys.exit("ГЕЙТ НЕ ПРОЙДЕН: " + "; ".join(fail))
    print("\nГЕЙТ ПРОЙДЕН.")


if __name__ == "__main__":
    main()
