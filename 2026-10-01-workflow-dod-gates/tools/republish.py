#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Финальная публикация статьи на Telegra.ph: перелить body целиком через
editPage того же path. Ничего не создаёт.

ЧТО ЗДЕСЬ ДВАЖДЕТСЯ СОДЕРЖАТЬСЯ, И ОБА ДЕФЕКТА ЖИЛИ В ПУБЛИКАЦИИ

1. ФРОНТМАТТЕР В ТЕКСТЕ
   Файл начинается с блока `--- ... ---`, который нужен сайту, но читателю
   показывает YAML: `title:`, `slug:`, `date:`, `tags:`, `author:`, `site:`.
   Регулярка `^---` не срабатывает, если перед блоком есть пустая строка
   или пробелы: `^` матчится на позиции 0, а там уже не `---`. Так и уехало
   в первую публикацию. Поэтому режем по `\\A\\s*` и ПРОВЕРЯЕМ результат,
   а не предполагаем.

2. ДУБЛЬ КАРТИНКИ
   Строка `![подпись](url)` в теле проходит через markdown-конвертер как
   обычная ссылка - получается абзац-ссылка с текстом подписи. Поверх мы
   вставляем figure с той же подписью. Читатель видит подпись дважды, причем
   одна из них кликабельна и ведёт в никуда (относительный путь на telegra.ph
   = 404). Канон это уже знает: `telegraph-publish-direct.py` не умеет
   `![]()`, поэтому строку картинки надо убрать ДО конвертации, а figure
   добавить отдельно.

Оба дефекта вернутся при любой пере republication, если чинить их в готовой
странице руками. Правится источник и гейт на выходе.

Env
    ARTICLE               markdown-исходник, по умолчанию article.md
    COVER_URL             абсолютный публичный URL обложки
    COVER_CAPTION         подпись figure и alt картинки
    TELEGRAPH_PATH        slug страницы без https://
    TELEGRAPH_CONVERTER   модуль с md_to_dom(markdown)
    SOCKS                 host:port, пусто = напрямую
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

API = "https://api.telegra.ph"
PATH = os.environ.get("TELEGRAPH_PATH", "")
SOCKS = os.environ.get("SOCKS", "")
ARTICLE = os.environ.get("ARTICLE", "article.md")
COVER = os.environ.get("COVER_URL", "")
CAPTION = os.environ.get("COVER_CAPTION", "")
_CONV = os.environ.get("TELEGRAPH_CONVERTER", "telegraph-publish-direct.py")

FRONTMATTER = re.compile(r"\A\s*---\r?\n.*?\r?\n---\s*\r?\n", re.S)
# Строка-картинка целиком. `\s*` вокруг важны: не съедать соседний абзац.
IMAGE_LINE = re.compile(r"^[ \t]*!\[[^\]]*\]\([^)]*\)[ \t]*\r?\n?", re.M)
# YAML-ключи, которые не должны пережить в тексте статьи.
FM_KEYS = ("title:", "slug:", "date:", "tags:", "author:", "site:", "cover:")
# Признаки того, что фронтматтер всё-таки уехал.
LEAK_RE = re.compile(r'"(?:title|slug|date|tags|author)":')
# Сиротский разделитель: строка из одних тире, не часть фронтматтера.
ORPHAN_RULE = re.compile(r'(?m)^[ \t]*-{3,}[ \t]*$')


def need(value, name):
    if not value:
        sys.exit("задай %s" % name)


def token():
    t = os.environ.get("TELEGRAPH_ACCESS_TOKEN")
    if t:
        return t.strip().strip("\"'")
    env = os.path.join(os.path.expanduser("~"), ".hermes", ".env")
    if os.path.exists(env):
        m = re.search(r"^TELEGRAPH_TOKEN\s*=\s*(.+)$", io_read(env), re.M)
        if m:
            return m.group(1).strip().strip("\"'")
    sys.exit("нет токена Telegraph: задай TELEGRAPH_ACCESS_TOKEN или ~/.hermes/.env")


def io_read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


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


def converter():
    """importlib, а не import: имя файла конвертера содержит дефис."""
    spec = importlib.util.spec_from_file_location("tg_convert", _CONV)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def prepare(md):
    """Фронтматтер и строки-картинки убраны, готовый текст для конвертера."""
    raw = md.replace("\r\n", "\n")
    raw = FRONTMATTER.sub("", raw, count=1)
    raw = IMAGE_LINE.sub("", raw)
    # Одиночный --- в теле страницы - остаток фронтматтера, а не
    # горизонтальная линия. Ни один гейт его не ловил: проверка была
    # только «начинается ли текст с ---», а сирота стоит в середине.
    # Читатель видит его как текст.
    raw = ORPHAN_RULE.sub("", raw)
    return raw.lstrip("\n")


def figure_node():
    return {"tag": "figure", "children": [
        {"tag": "img", "attrs": {"src": COVER, "alt": CAPTION}},
        {"tag": "figcaption", "children": [CAPTION]}]}


def insert_cover(nodes):
    """Обложка - перед первым абзацем лида, не по индексу.

    Привязка к тексту, а не к позиции: вставка по номеру ломается, как только
    кто-то правит вступление.
    """
    if any(n.get("tag") == "img" for n in nodes):
        return "уже была, повторно не вставляю"
    anchor = None
    for i, n in enumerate(nodes):
        if n.get("tag") in ("p", "h3") and "платформа" in json.dumps(n, ensure_ascii=False):
            anchor = i
            break
    if anchor is None:
        sys.exit("не нашёл абзац-якорь для обложки; вставить по индексу наугад нельзя")
    nodes.insert(anchor, figure_node())
    return "вставлена перед узлом %d" % anchor


def current_title():
    """Заголовок живой страницы.

    editPage требует title, но правим мы только body. Передавать константу
    из исходника опасно: если заголовок уже правили вручную, он молча
    откатится. Поэтому читаем текущий и возвращаем как есть.
    """
    live = call("getPage", {"path": PATH, "return_content": "false"})
    if not live.get("ok"):
        sys.exit("не могу прочитать текущий заголовок: "
                 + json.dumps(live, ensure_ascii=False)[:200])
    title = live["result"].get("title", "")
    if not title:
        sys.exit("у страницы пустой заголовок, править body не буду")
    return title


def main():
    need(PATH, "TELEGRAPH_PATH")
    need(COVER, "COVER_URL")
    need(CAPTION, "COVER_CAPTION")

    # --dry-run обязан быть РЕАЛЬНЫМ. Флаг без разбора аргументов даёт
    # скрипт, который печатает 'edit ok' и при этом пишет на живую
    # страницу: гейт, заявленный как сетевой, оказывается сетевым.
    dry_run = "--dry-run" in sys.argv

    raw = prepare(io_read(ARTICLE))

    # Гейт на подготовленном тексте: дефекты ловим до похода в сеть.
    leaked = [k for k in FM_KEYS if k in raw.split("\n\n")[0] or re.search(
        r"(?m)^%s" % re.escape(k), raw)]
    if leaked:
        sys.exit("фронтматтер не срезан: %s" % leaked[:4])
    if IMAGE_LINE.search(raw):
        sys.exit("строка-картинка не вырезана, будет дубль подписи")
    if raw.lstrip().startswith("---"):
        sys.exit("текст начинается с ---, проверь исходник")
    print("исходник: %d символов, фронтматтер и картинки вырезаны" % len(raw))

    nodes = converter().md_to_dom(raw)
    print("DOM до обложки: %d узлов" % len(nodes))
    print("обложка: %s" % insert_cover(nodes))

    if dry_run:
        print("---")
        print("DRY RUN: сеть не трогаю, editPage не вызван.")
        print("подготовлено узлов: %d" % len(nodes))
        blob = json.dumps(nodes, ensure_ascii=False)
        img_n = blob.count('"tag": "img"')
        # Считаем figcaption-узлы, а не вхождения строки подписи.
        # Подпись в подготовленном DOM есть дважды - в alt картинки и
        # в figcaption, - а Telegra вырезает alt при сохранении. Счётчик
        # строки на подготовленном DOM даёт ложное 2, на живой странице -
        # случайное 1. Узел figcaption существует в обоих.
        cap_n = blob.count('"tag": "figcaption"')
        md_img = blob.count("](")
        print("img-нод:       %d  (должна быть 1)" % img_n)
        print("figcaption:    %d  (должна быть 1)" % cap_n)
        print("markdown-остаток '](': %d  (должен быть 0)" % md_img)
        if img_n != 1 or cap_n != 1 or md_img:
            sys.exit("контроль подготовки не прошёл")
        print("VERDICT: PASS (структура, без сети)")
        return

    res = call("editPage", {
        "path": PATH,
        "access_token": token(),
        # title обязателен: editPage без него отдаёт TITLE_REQUIRED.
        # Правим только body, но поле всё равно нужно передать - берём
        # текущий заголовок страницы, чтобы не сбросить его случайно.
        "title": current_title(),
        "content": nodes,
        "return_content": "false",
    })
    if not res.get("ok"):
        sys.exit("editPage не прошёл: " + json.dumps(res, ensure_ascii=False)[:400])
    print("edit ok: %s" % res["result"].get("url"))

    # Гейт на ЖИВОЙ странице. Локальная проверка ничего не значит: читатель
    # получает то, что вернул сервер.
    chk = call("getPage", {"path": PATH, "return_content": "true"})
    if not chk.get("ok"):
        sys.exit("контрольный getPage не прошёл")
    live = chk["result"].get("content", [])
    blob = json.dumps(live, ensure_ascii=False)
    title = chk["result"].get("title", "")

    fm_hits = [k for k in FM_KEYS if k in blob]
    img_n = blob.count('"tag": "img"')
    # figcaption-узлы, не вхождения строки: см. комментарий в dry_run.
    cap_n = blob.count('"tag": "figcaption"')
    md_img = blob.count("](")

    print("---")
    print("узлов:        %d" % (len(live) if isinstance(live, list) else 0))
    print("img-нод:      %d  (должна быть 1)" % img_n)
    print("figcaption:   %d  (должна быть 1)" % cap_n)
    print("frontmatter:  %s" % (fm_hits or "нет"))
    print("markdown-остаток '](': %d  (должен быть 0)" % md_img)
    print("title:        %r (%d)" % (title, len(title)))

    if fm_hits or img_n != 1 or cap_n != 1 or md_img or len(title) > 60:
        sys.exit("контроль не пройден")
    print("VERDICT: PASS")


if __name__ == "__main__":
    main()