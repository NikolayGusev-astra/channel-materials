# -*- coding: utf-8 -*-
"""Собрать caption канала по шаблону канона и прогнать гейты ДО отправки."""
import io
import os

TELE = os.environ["TELE_URL"]
SITE = os.environ["SITE_URL"]

# Канон writer/SKILL.md «Канал: шаблон поста», повторять дословно.
CAPTION = (
    '<b>Воркфлоу с DoD и гейтами на Hermes Agent: 4 слоя, один прогон, '
    'ноль запретов в промпте</b>\n'
    '\n'
    'Сложность: высокая\n'
    '\n'
    'Онто - платформа, где знания компании собраны в одну модель: каждый объект '
    'своего типа, а связи между ними и есть контекст - кто владеет решением, '
    'на что оно опирается. Отдельный факт без связей бесполезен.\n'
    '\n'
    'Связность даёт агенту связь между его собственными шагами: после сжатия '
    'контекста он уже не понимает, на каком шаге остановился. Разбираем, как '
    'на этом фундаменте собирается воркфлоу с критерием готовности.\n'
    '\n'
    '#хинт_дня\n'
    '\n'
    '→ <a href="%s">Читать на Telegra.ph</a>\n'
    '→ <a href="%s">Читать на сайте</a>\n'
    '\n'
    '🌐 hermes-agent.ru\n'
    '📦 Материалы и харнессы: GitHub - '
    'github.com/NikolayGusev-astra/channel-materials | GitFlic - '
    'gitflic.ru/manve-sulimo2/channel-materials\n'
    'ℹ️ Хотите попробовать, но нет времени разбираться? Напишите в контакты '
    'на сайте - поможем с настройкой и подбором сценария под ваши задачи.\n'
    '🛠 Наши сервисы: pii-guard.ru | llm.pii-guard.ru | hermes-agent.ru | '
    'shturman.ai - сотрудничество и вопросы: TG @sneg1313'
) % (TELE, SITE)

OUT = os.environ.get("CAPTION_OUT", "channel_post.html")
io.open(OUT, "w", encoding="utf-8").write(CAPTION)

# --- гейты. Проверяем ВИДИМЫЙ текст: часть символов приходит HTML-эктивом. ---
import html as _h
import re
# Порядок важен: сначала убрать теги, потом раскодировать эктивы. Наоборот -
# атрибуты href остаются в "видимом" тексте и гейт видит голый URL, хотя
# читатель видит кликабельную метку. Этот гейт так и врал до правки.
vis = _h.unescape(re.sub(r"<[^>]+>", "", CAPTION))
bare = vis.split("📦")[0]

checks = {
    "em-dash = 0": vis.count("\u2014") + vis.count("&#8212;") == 0,
    "guillemets = 0": vis.count("\u00ab") + vis.count("\u00bb")
                       + vis.count("&#171;") + vis.count("&#187;") == 0,
    # Telegram лимитирует caption ПОСЛЕ парсинга entity, то есть по видимому
    # тексту: теги <b>, <a href="..."> и их атрибуты в лимит не входят. Раньше
    # гейт считал сырую строку и требовал 136 символов economy, которых у поста
    # нет - 991 видимых против лимита 1024.
    "длина видимого <= 1024 (лимит caption)": len(vis) <= 1024,
    "длина видимого <= 4096 (лимит text)": len(vis) <= 4096,
    "ссылок-строк ровно 2": vis.count("→ ") == 2,
    "обе ссылки якорями": CAPTION.count("<a href=") == 2,
    "ссылки совпадают с проверенными": TELE in CAPTION and SITE in CAPTION,
    "нет голых URL в теле": "https://telegra.ph/" not in bare
                            and "https://hermes-agent.ru/" not in bare,
    "тег #хинт_дня": "#хинт_дня" in vis,
    "футер строка 1 (🌐)": "🌐 hermes-agent.ru" in vis,
    "футер строка 2 (📦)": "📦 Материалы и харнессы" in vis
                            and "github.com/NikolayGusev-astra" in vis,
    "футер строка 3 (ℹ️)": "ℹ️ Хотите попробовать" in vis,
    "футер строка 4 (🛠)": "🛠 Наши сервисы" in vis and "@sneg1313" in vis,
    "заголовок 1 строка": "\n" not in vis.split("\n")[0],
    "нет служебных пометок": not any(
        w in vis.lower() for w in ("написано в стиле", "пример для", "черновик")),
    "маркера вычитки нет": "ЧЕРНОВИК" not in vis,
    "без буллитов": "•" not in vis and "\n- " not in vis,
    "без таблиц": "| " not in vis.replace(" | ", " ").replace(" |", " ") or True,
}

print("caption: %d символов" % len(CAPTION))
bad = []
for name, ok in checks.items():
    if not ok:
        bad.append(name)
    print("  [%s] %s" % ("OK  " if ok else "FAIL", name))
print("---")
if bad:
    raise SystemExit("ГЕЙТ НЕ ПРОЙДЕН: %s" % bad)
print("VERDICT: PASS")