"""Шаг 3: разметка остатка ротатором бесплатных LLM (OpenRouter :free).
Запуск: python 03_label_llm.py --mails mails_rules.json --out mails_labeled.json
Креды: env OPENROUTER_API_KEY. 429/503 -> автопереезд на следующую модель.
Совет агенту: подставь актуальные :free модели из https://openrouter.ai/api/v1/models
(список меняется), проверь smoke на 10 письмах перед полным прогоном.
"""
import json, os, re, time, argparse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from collections import Counter

MODELS_DEFAULT = [
    "deepseek/deepseek-v4-flash-0731:free",
    "inclusionai/ling-3.0-flash-sante:free",
    "google/gemma-4-26b-a4b-it:free",
    "nex-agi/nex-n2.5-mini:free",
]
PROMPT = """Письмо: "{subj}"
Текст: {body}

Требует ли это письмо действия или содержит личную важную информацию (оплата, документ, запись, срок)? Промо-рассылки, дайджесты, соцсети, уведомления - НЕ важные.
Формат ответа: сначала одно слово "да" или "нет", потом краткое пояснение."""

def extract(text):
    if not text: return None
    m = re.search(r"\b(да|нет)\b", text[:60], re.I)
    if m: return m.group(1).lower()
    hits = re.findall(r"\b(да|нет)\b", text, re.I)
    return hits[-1].lower() if hits else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mails", default="mails_rules.json")
    ap.add_argument("--out", default="mails_labeled.json")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--batch", type=int, default=200)
    ap.add_argument("--proxy", default=None, help="http://host:port если нужен для openrouter.ai")
    args = ap.parse_args()
    key = os.environ["OPENROUTER_API_KEY"]
    handler = urllib.request.ProxyHandler({"http": args.proxy, "https": args.proxy}) if args.proxy else urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(handler)
    mi = [0]

    def call(model, text):
        body = json.dumps({"model": model, "messages": [{"role": "user", "content": text}],
            "temperature": 0, "max_tokens": 300}).encode("utf-8")
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        with opener.open(req, timeout=90) as r:
            msg = json.loads(r.read().decode())["choices"][0]["message"]
        return (msg.get("content") or msg.get("reasoning") or "").strip().lower()

    def yes_no(m):
        if m.get("label") is not None:
            return m
        text = PROMPT.format(subj=m["subject"][:120], body=m["body_snippet"][:300])
        tried = 0
        while tried < len(MODELS_DEFAULT) * 3:
            model = MODELS_DEFAULT[mi[0] % len(MODELS_DEFAULT)]
            try:
                ans = extract(call(model, text))
                if ans:
                    return {**m, "label": 1 if ans == "да" else 0, "source": "llm", "model": model}
                return {**m, "label": None, "source": "unparsed"}
            except urllib.error.HTTPError:
                mi[0] += 1; tried += 1; time.sleep(1.2)
            except Exception:
                mi[0] += 1; tried += 1; time.sleep(0.7)
        return {**m, "label": None, "source": "exhausted"}

    mails = json.load(open(args.mails, encoding="utf-8"))
    rest = [m for m in mails if m.get("label") is None]
    print("к разметке LLM:", len(rest), flush=True)
    out = [m for m in mails if m.get("label") is not None]
    t0 = time.time()
    for c in range(0, len(rest), args.batch):
        chunk = rest[c:c+args.batch]
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            out += list(ex.map(yes_no, chunk))
        json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False)
        ok = sum(1 for r in out if r.get("label") is not None)
        print(f"{len(out)}/{len(mails)} ({ok} ок) {time.time()-t0:.0f}s {dict(Counter(r.get('source') for r in out))}", flush=True)
    print("DONE")

if __name__ == "__main__":
    main()
