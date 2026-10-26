import json, re, time, urllib.request, unicodedata, sys

BASE = "C:/Work/Assist/channel-materials/2026-10-19-dag-tables-to-reports"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
d = json.load(open(BASE + "/data/narrow.json", encoding="utf-8"))
facts = d["facts"]

def build(rows):
    lines = []
    for f in rows:
        lines.append(f"- {f['slug']} | вышла {f['published']} | уник. IP {f['ip']} | "
                     f"просмотры 09-13: {f['views_09_13']} | просмотры 14-19: {f['views_14_19']}")
    block = "\n".join(lines)
    return f"""Ниже статьи с готовыми числами. Числа посчитаны, считать не нужно.

{block}

Для каждой статьи объясни ОДНОЙ фразой, что означают её числа.
Не считай и не выводи новых чисел. Первая половина нулевая, вторая нет - статья вышла недавно.
Вторая половина заметно меньше первой - интерес угасает.

Верни только JSON-массив:
[{{"slug": "...", "trend": "новинка|рост|спад|стабильно", "reason": "одна фраза"}}]"""

def ask(model, p, mt=1200):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": p}],
                       "temperature": 0.0, "max_tokens": mt}).encode()
    req = urllib.request.Request("http://127.0.0.1:1234/v1/chat/completions", body,
                                 {"Content-Type": "application/json"})
    t0 = time.time(); r = json.load(opener.open(req, timeout=600))
    m = r["choices"][0]["message"]
    txt = (m.get("content") or "").strip() or (m.get("reasoning_content") or "").strip()
    return txt, time.time() - t0, r.get("usage", {}), r["choices"][0].get("finish_reason")

def parse(txt):
    t = re.sub(r"^\s*```[a-z]*\s*", "", txt.strip()); t = re.sub(r"\s*```\s*$", "", t)
    m = re.search(r"\[.*\]", t, re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except Exception: return None

model = sys.argv[1]
out = {}
for i in range(0, len(facts), 4):
    chunk = facts[i:i+4]
    try:
        raw, dt, us, fin = ask(model, build(chunk))
    except Exception as e:
        print(f"батч {i//4+1}: ОШИБКА {type(e).__name__}: {e}"); continue
    data = parse(raw)
    ok = 0
    print(f"\n--- батч {i//4+1}: {dt:.0f}s, tok={us.get('completion_tokens')}, finish={fin}")
    if not data:
        print("   JSON не разобран:", raw[:150]); continue
    for row in data:
        slug = str(row.get("slug","")).strip()
        f = next((x for x in chunk if x["slug"] == slug), None)
        if not f: continue
        good = row.get("trend") == f["trend"]; ok += good
        print(f"   {'OK  ' if good else 'ОШИБ'} {slug[:36]:36} факт={f['trend']:9} мод={str(row.get('trend')):9}")
        print(f"        {str(row.get('reason',''))[:100]}")
    print(f"   верно {ok}/{len(chunk)}")
    out[f"batch{i//4+1}"] = {"secs": round(dt), "tok": us.get("completion_tokens"),
                             "finish": fin, "ok": ok, "of": len(chunk), "raw": raw[:3000]}
json.dump(out, open(BASE + f"/data/batch_{model.split('/')[-1]}.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
