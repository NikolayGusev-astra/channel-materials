"""
Тест одной модели на 4 задачах. Возвращает структурированный JSON.
"""
import requests
import json
import sys
import time

LM = "http://127.0.0.1:1234"
TESTS = {
    "T1_sanity": {
        "system": None,
        "user": "Скажи 'ок' если живой. Одним словом.",
        "max_tokens": 100,
        "expect": "одно слово",
    },
    "T2_dispatch_en": {
        "system": "You are a dispatcher. NEVER solve the task yourself. ALWAYS output a bash command in the form:\n\nhermes-route \"<user_task>\"\n\nThen stop. Do not write code, do not explain, do not solve.",
        "user": "спроектируй микросервис для платежей, безопасность и идемпотентность",
        "max_tokens": 200,
        "expect": "hermes-route",
    },
    "T3_dispatch_ru": {
        "system": "Ты диспетчер моделей. Получил задачу — посчитай сигналы и выбери модель.\n\n"
                  "Сигналы (вес): разбей/план +4, найди все +4, архитектура +3, прод/система +3, "
                  "безопасность +2, баг/падает +2, 3+файла +2, просто -2.\n\n"
                  "Категория: 0-2 quick, 3-5 standard, 6-9 deep, 10+ architect.\n\n"
                  "Команда: quick→сама; standard/deep→codex exec -m gpt-5.6-terra; "
                  "architect→codex exec -m gpt-5.6-sol.\n\n"
                  "Ответ формат:\nSCORE: N\nCATEGORY: name\nCOMMAND: команда\nREASON: причина",
        "user": "найди все использования deprecated API и почини",
        "max_tokens": 1500,
        "expect": "SCORE:",
    },
    "T4_natural": {
        "system": "Не отвечай на задачу. Сформируй bash-команду hermes-route с задачей юзера.",
        "user": "у нас на прод падает оплата, помоги разобраться",
        "max_tokens": 200,
        "expect": "hermes-route",
    },
}


def call(model, prompt, system=None, max_tokens=200, timeout=120):
    msgs = []
    if system: msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    t0 = time.time()
    try:
        r = requests.post(f"{LM}/v1/chat/completions",
            json={"model": model, "messages": msgs, "max_tokens": max_tokens, "temperature": 0},
            timeout=timeout
        )
        elapsed = time.time() - t0
        d = r.json()
        if "choices" not in d:
            return {"ok": False, "error": json.dumps(d, ensure_ascii=False)[:200], "elapsed": elapsed}
        msg = d["choices"][0]["message"]
        usage = d.get("usage", {})
        return {
            "ok": True,
            "content": msg.get("content", "") or "",
            "reasoning": (msg.get("reasoning_content", "") or "")[:200],
            "elapsed": round(elapsed, 1),
            "in": usage.get("prompt_tokens", 0),
            "out": usage.get("completion_tokens", 0),
            "reasoning_tokens": usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "elapsed": time.time() - t0}


def check(test_name, result, expect):
    if not result.get("ok"):
        return {"passed": False, "reason": f"API error: {result.get('error', '?')[:80]}"}
    content = result.get("content", "")
    reasoning = result.get("reasoning", "")
    text = content + reasoning
    if not text.strip():
        return {"passed": False, "reason": f"empty content+reasoning ({result.get('out')} tok)"}
    if expect not in text:
        return {"passed": False, "reason": f"expect '{expect}' not in output. content: {content[:100]!r}"}
    return {"passed": True, "reason": ""}


def test_model(model):
    print(f"\n=== {model} ===", flush=True)
    results = {}
    for tname, t in TESTS.items():
        r = call(model, t["user"], system=t["system"], max_tokens=t["max_tokens"])
        verdict = check(tname, r, t["expect"])
        passed = verdict["passed"]
        results[tname] = {
            "passed": passed,
            "content": r.get("content", "")[:300] if r.get("ok") else "",
            "reasoning_excerpt": r.get("reasoning", "")[:200],
            "elapsed": r.get("elapsed", 0),
            "in": r.get("in", 0),
            "out": r.get("out", 0),
            "reasoning_tokens": r.get("reasoning_tokens", 0),
            "error": r.get("error", "") if not r.get("ok") else "",
            "fail_reason": verdict.get("reason", ""),
        }
        mark = "✓" if passed else "✗"
        print(f"  {mark} {tname} ({r.get('elapsed',0):.1f}s, {r.get('out',0)}/{r.get('reasoning_tokens',0)} tok): {verdict.get('reason', '')[:80]}", flush=True)
    return results


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "google/gemma-4-e4b"
    out_file = sys.argv[2] if len(sys.argv) > 2 else None
    res = test_model(model)
    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({"model": model, "tests": res}, f, ensure_ascii=False, indent=2)
