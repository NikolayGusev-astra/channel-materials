import json, re, unicodedata

HY = "-\u2010\u2011\u2012\u2013\u2014"

def norm(s):
    return unicodedata.normalize("NFKC", s).replace("\u202f", " ").replace("\u00a0", " ")

def strip_noise(s):
    s = re.sub(r"/news/[a-z0-9\-/]+", " <URL> ", s)
    s = re.sub(r"\b\d{1,2}\.\d{1,2}\b", " <DATE> ", s)
    s = re.sub(r"\b\d{1,2}\s*[" + HY + r"]\s*\d{1,2}\b", " <RANGE> ", s)
    s = re.sub(r"[*#]", " ", s)
    s = re.sub(r"(?m)^\s*\d+[\).]\s", " ", s)          # нумерация пунктов
    return s

t = json.load(open("data/table.json", encoding="utf-8"))
res = json.load(open("data/results.json", encoding="utf-8"))
truth = {p: (ips, h1, h2) for p, ips, h1, h2 in t["top"]}
allowed = set()
for d, v, i, b in t["days"]:
    allowed |= {v, i, b}
for p, (i, h1, h2) in truth.items():
    allowed |= {i, h1, h2}
allowed |= {t["total"], t["ips"]} | set(range(1, 32)) | {2026}

summary = {}
for model, raw in res.items():
    txt = norm(raw); clean = strip_noise(txt)
    bad = sorted({int(n) for n in re.findall(r"\b\d{1,6}\b", clean)
                  if int(n) > 31 and int(n) not in allowed})
    lies = 0; checked = 0
    print("=" * 64); print(model)
    print("  числа вне таблицы:", bad or "нет")
    for p, exp in truth.items():
        if p not in txt:
            continue
        checked += 1
        seg = strip_noise(txt.split(p, 1)[1][:90])
        got = [int(x) for x in re.findall(r"\b\d{1,6}\b", seg)][:3]
        ok = bool(got) and list(exp)[:len(got)] == got
        if not ok: lies += 1
        print(f"  {'OK  ' if ok else 'ЛОЖЬ'} {p}")
        print(f"        факт:  {list(exp)}")
        print(f"        текст: {got}")
    summary[model] = {"проверено строк": checked, "ошибок": lies, "вне таблицы": len(bad)}

print("\n=== ИТОГ ===")
for m, s in summary.items():
    print(f"{m}: строк {s['проверено строк']}, ошибок {s['ошибок']}, чисел вне таблицы {s['вне таблицы']}")
json.dump(summary, open("data/validation.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
