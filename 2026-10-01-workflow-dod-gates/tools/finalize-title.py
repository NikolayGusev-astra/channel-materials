#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Снять маркер «(ЧЕРНОВИК для вычитки)» с уже опубликованной страницы.

Зачем существует
    Telegra не умеет приватных черновиков: страница публична с момента
    createPage. Стадия вычитки помечается МАРКЕРОМ В ЗАГОЛОВКЕ, а не
    приватностью. Канон: черновик → editPage того же path → финальная версия
    БЕЗ маркера.

    Ссылка из поста в канале ведёт на страницу, которая сама себя называет
    черновиком. Это ровно тот случай, когда канон нарушен внешне, и читатель
    видит это первым.

Безопасность правок
    Контент берётся С ЖИВОЙ страницы (getPage) и отправляется обратно без
    изменений — правится только title. Если бы текст пришёл из локального
    .md, любое расхождение между файлом и страницей тихо затёрло бы
    опубликованную версию.

Идемпотентность
    Если маркера на странице нет - скрипт ничего не делает и сообщает об
    этом. Повторный запуск безопасен.

Env
    TELEGRAPH_PATH   обязательно, slug страницы без https://
    SOCKS            необязательно, host:port, пусто = напрямую
"""

import json
import os
import re
import subprocess
import sys
import tempfile

API = "https://api.telegra.ph"
PATH = os.environ.get("TELEGRAPH_PATH", "")
SOCKS = os.environ.get("SOCKS", "")
MARKER = "ЧЕРНОВИК"
TITLE_MAX = 60


def call(method, payload):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
        tmp = f.name
    try:
        cmd = ["curl", "-s", "-m", "50"]
        if SOCKS:
            cmd += ["--socks5-hostname", SOCKS]
        cmd += ["-X", "POST", API + "/" + method,
                "-H", "Content-Type: application/json",
                "--data-binary", "@" + tmp]
        return json.loads(subprocess.run(cmd, capture_output=True, text=True,
                                         encoding="utf-8").stdout or "{}")
    finally:
        os.unlink(tmp)


def token():
    t = os.environ.get("TELEGRAPH_ACCESS_TOKEN")
    if t:
        return t.strip().strip("\"'")
    env = os.path.join(os.path.expanduser("~"), ".hermes", ".env")
    if os.path.exists(env):
        m = re.search(r"^TELEGRAPH_TOKEN\s*=\s*(.+)$",
                      io_read(env), re.M)
        if m:
            return m.group(1).strip().strip("\"'")
    sys.exit("нет токена Telegraph: задай TELEGRAPH_ACCESS_TOKEN или ~/.hermes/.env")


def io_read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def strip_marker(title):
    """Убрать маркер и хвостовые пробелы, не трогая базу."""
    base = re.sub(r"\s*\(ЧЕРНОВИК[^)]*\)", "", title)
    base = re.sub(r"\s*[-–—|]\s*$", "", base)
    return base.strip()


def main():
    if not PATH:
        sys.exit("задай TELEGRAPH_PATH")

    live = call("getPage", {"path": PATH, "return_content": "true"})
    if not live.get("ok"):
        sys.exit("getPage не прошёл: " + json.dumps(live, ensure_ascii=False)[:300])

    result = live["result"]
    old = result.get("title", "")
    content = result.get("content", [])
    nodes = len(content) if isinstance(content, list) else len(json.loads(content or "[]"))

    print("было:  %r (%d символов)" % (old, len(old)))
    print("узлов: %d (будут перезаписаны как есть)" % nodes)

    if MARKER not in old:
        print("маркера нет, ничего не делаю")
        return

    new = strip_marker(old)
    if not new:
        sys.exit("после снятия маркера заголовок пуст, остановилась")
    if len(new) > TITLE_MAX:
        sys.exit("новый заголовок %d символов при лимите %d; сократить базу"
                 % (len(new), TITLE_MAX))

    res = call("editPage", {
        "path": PATH,
        "access_token": token(),
        "title": new,
        "content": content,
        "return_content": "false",
    })
    if not res.get("ok"):
        sys.exit("editPage не прошёл: " + json.dumps(res, ensure_ascii=False)[:400])
    print("стало: %r (%d символов)" % (new, len(new)))
    print("url:   %s" % res["result"].get("url"))

    # Контроль на живой странице, а не на возврате API.
    chk = call("getPage", {"path": PATH, "return_content": "true"})
    if not chk.get("ok"):
        sys.exit("контрольный getPage не прошёл")
    got = chk["result"].get("title", "")
    got_nodes = chk["result"].get("content", [])
    got_nodes = len(got_nodes) if isinstance(got_nodes, list) else len(json.loads(got_nodes or "[]"))

    print("---")
    print("контроль title:  %r" % got)
    print("маркер снят:     %s" % ("да" if MARKER not in got else "НЕТ"))
    print("лимит 60:        %s (%d)" % ("ок" if len(got) <= TITLE_MAX else "НАРУШЕН", len(got)))
    print("узлов не теряно: %s (%d)" % ("да" if got_nodes == nodes else "НЕТ", got_nodes))
    if MARKER in got or len(got) > TITLE_MAX or got_nodes != nodes:
        sys.exit("контроль не пройден")


if __name__ == "__main__":
    main()