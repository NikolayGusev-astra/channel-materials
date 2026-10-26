import json, re, time, urllib.request, unicodedata, datetime, sys

BASE = "C:/Work/Assist/channel-materials/2026-10-19-dag-tables-to-reports"
SITE = "C:/Work/Assist/hermes-site/site"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

t = json.load(open(BASE + "/data/table.json", encoding="utf-8"))

def frontmatter(slug):
    p = f"{SITE}/content/articles/{slug}.md"
    txt = open(p, encoding="utf-8").read()
    fm = txt.split("---")[1]
    title = re.search(r'^title:\s*"?(.*?)"?$', fm, re.M).group(1)
    pub = re.search(r'^published_at:\s*(\S+)', fm, re.M)
    return title, (pub.group(1) if pub else "")

facts = []
for path, ips, h1, h2 in t["top"]:
    slug = path.replace("/news/", "").strip("/")
    title, pub = frontmatter(slug)
    # истина считается кодом, не моделью
    if pub >= "2026-10-14":
        trend = "новинка"
    elif h2 > h1 * 1.15:
        trend = "рост"
    elif h2 < h1 * 0.85:
        trend = "спад"
    else:
        trend = "стабильно"
    facts.append({"slug": slug, "title": title, "published": pub,
                  "ip": ips, "views_09_13": h1, "views_14_19": h2,
                  "trend": trend})

lines = []
for f in facts:
    lines.append(f"- {f['slug']} | «{f['title']}» | вышла {f['published']} | "
                 f"уник. IP {f['ip']} | просмотры 09-13: {f['views_09_13']} | "
                 f"просмотры 14-19: {f['views_14_19']}")
block = "\n".join(lines)

prompt = f"""Ниже 12 статей с готовыми числами. Числа уже посчитаны, считать не нужно.

{block}

Задача: для каждой статьи объясни ОДНОЙ фразой, что означают её числа.

Правила:
- Не считай, не складывай, не выводи новых чисел. Используй только числа из строки.
- Если первая половина нулевая, а вторая нет, значит статья вышла недавно.
- Если вторая половина заметно меньше первой, интерес угасает.
- Не пересказывай числа, объясняй смысл.

Верни ТОЛЬКО JSON-массив, без пояснений:
[{{"slug": "...", "trend": "новинка|рост|спад|стабильно", "reason": "одна фраза"}}]"""

def ask(model, p, max_tokens=2500):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": p}],
                       "temperature": 0.0, "max_tokens": max_tokens}).encode()
    req = urllib.request.Request("http://127.0.0.1:1234/v1/chat/completions", body,
                                 {"Content-Type": "application/json"})
    t0 = time.time(); r = json.load(opener.open(req, timeout=900))
    msg = r["choices"][0]["message"]
    txt = (msg.get("content") or "").strip() or (msg.get("reasoning_content") or "").strip()
    return txt, time.time() - t0, r.get("usage", {})

def parse_json(txt):
    txt = re.sub(r"^\s*```[a-z]*\s*", "", txt.strip())
    txt = re.sub(r"\s*```\s*$", "", txt)
    m = re.search(r"\[.*\]", txt, re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except Exception:
        try: return json.loads(m.group(0).replace("\n", " "))
        except Exception: return None

truth = {f["slug"]: f for f in facts}
report = {}
for model in sys.argv[1:]:
    try:
        raw, dt, us = ask(model, prompt)
    except Exception as e:
        print(f"{model}: ОШИБКА {type(e).__name__}: {e}"); continue
    data = parse_json(raw)
    raw_dump = raw
    print("=" * 66); print(f"{model}  ({dt:.0f}s, tok={us.get('completion_tokens')})")
    if not data:
        print("  JSON не разобран. Начало:", raw[:200])
        report[model] = {"error": "no json", "raw": raw[:4000]}; continue
    ok = bad_num = 0
    for row in data:
        slug = str(row.get("slug", "")).strip()
        if slug not in truth:
            continue
        f = truth[slug]
        t_ok = row.get("trend") == f["trend"]
        ok += t_ok
        nums = {int(x) for x in re.findall(r"\b\d{1,6}\b", unicodedata.normalize("NFKC", str(row.get("reason", ""))))}
        allowed = {f["ip"], f["views_09_13"], f["views_14_19"]} | {int(x) for x in re.findall(r"\d+", f["published"])} | set(range(1, 32))
        extra = nums - allowed
        reason = str(row.get("reason", ""))
        invent = re.findall(r"\d+\s*(?:час|мин|дн|сут|недел|месяц)\w*", reason, re.I)
        if invent: extra = extra | {"выдумано: " + ", ".join(invent)}
        if extra: bad_num += 1
        mark = "OK  " if t_ok and not extra else "ОШИБ"
        print(f"  {mark} {slug[:38]:38} факт={f['trend']:9} модель={str(row.get('trend')):9}")
        print(f"        {row.get('reason','')[:110]}")
        if extra: print(f"        числа вне строки: {sorted(extra)}")
    print(f"  ИТОГ: тренд верно {ok}/{len(truth)}, строк с лишними числами {bad_num}")
    report[model] = {"trend_ok": ok, "of": len(truth), "rows_with_extra_numbers": bad_num, "raw": raw_dump[:4000],
                     "secs": round(dt), "tokens": us.get("completion_tokens")}

json.dump({"facts": facts, "report": report}, open(BASE + "/data/narrow.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nсохранено data/narrow.json")
