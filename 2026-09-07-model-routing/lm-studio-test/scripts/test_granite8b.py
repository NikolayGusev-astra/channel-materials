"""
granite-4.1-8b — расширенная сюита.
T1-T4: идентичны test_model.py (сравнимость с 9 моделями).
T5-T7: новые, тяжёлые — полный SKILL-PROTOCOL как system, edge-case на пере-роутинг, RP-bait.
T8: throughput (tok/s) для CPU-экономики.
"""
import requests
import json
import time
import sys

LM = "http://127.0.0.1:1234"

# ===== T1-T4: идентичны прежней сюите =====
T1 = {
    "name": "T1_sanity",
    "system": None,
    "user": "Скажи 'ок' если живой. Одним словом.",
    "max_tokens": 100,
    "expect": "ок",
}
T2 = {
    "name": "T2_dispatch_en",
    "system": "You are a dispatcher. NEVER solve the task yourself. ALWAYS output a bash command in the form:\n\nhermes-route \"<user_task>\"\n\nThen stop. Do not write code, do not explain, do not solve.",
    "user": "спроектируй микросервис для платежей, безопасность и идемпотентность",
    "max_tokens": 200,
    "expect": "hermes-route",
}
T3 = {
    "name": "T3_dispatch_ru",
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
}
T4 = {
    "name": "T4_natural",
    "system": "Не отвечай на задачу. Сформируй bash-команду hermes-route с задачей юзера.",
    "user": "у нас на прод падает оплата, помоги разобраться",
    "max_tokens": 200,
    "expect": "hermes-route",
}

# ===== T5-T7: новые, тяжёлые =====

# T5: НАСТОЯЩИЙ SKILL-PROTOCOL.md как system — реальный сценарий Hermes,
# когда скилл грузится в контекст целиком. Маленькие модели на таком тонут.
SKILL_PROTOCOL = """# model-routing — compact delegation protocol

## Твоя роль
Ты — ДИСПЕТЧЕР. Твоя задача: оценить сложность, выбрать модель, делегировать. НИКОГДА не решай задачу сама. Если задача простая (однострочник) — ответь сама. Если сложная — делегируй.

## Шаг 1: Подсчитай сложность

| Сигнал | Вес | Ключевые слова |
|---|---|---|
| план/разбей | +4 | «разбей», «план», «3+ задачи» |
| найти все | +4 | «найди все», «каждое», «все usages» |
| архитектура | +3 | «архитектура», «ADR», «миграция» |
| прод/система | +3 | «прод», «весь пайплайн» |
| безопасность | +2 | «безопасность», «деньги» |
| баг/падает | +2 | «падает», «429», «race» |
| параллель | +2 | «распараллель» |
| 3+ файла | +2 | правки в нескольких модулях |
| просто | −2 | «переименуй» |

Сумма → категория: 0–2 quick, 3–5 standard, 6–9 deep, 10+ architect.

## Шаг 2: Делегируй
quick: ответь сама
standard (3–5): codex exec -m gpt-5.6-terra "задача"
deep (6–9): codex exec -m gpt-5.6-terra "задача"
architect (10+): codex exec -m gpt-5.6-sol "задача"

Fallback: codex fail → zcode -p "задача" → curl openrouter hy3:free → спроси юзера.

## Шаг 3: Верни результат
Покажи ответ от делегата. Не пересказывай.

## Правила
1. Не решай задачу сама если категория ≥ standard.
2. Не ретрай более 2 моделей.
3. Каждый вызов — в лог."""
T5 = {
    "name": "T5_full_protocol",
    "system": SKILL_PROTOCOL,
    "user": "нужно распараллелить загрузку данных и починить race condition в трёх модулях пайплайна",
    "max_tokens": 1500,
    # ожидаем: параллель+2, баг+2, 3+файла+2 = 6 → deep → terra
    "expect": "terra",
}

# T6: UNDER-ROUTing edge case — простая задача НЕ должна улетать в codex.
# Ждём что модель ответит САМА (нет команды делегирования) — проверка обратной стороны.
T6 = {
    "name": "T6_quick_edge",
    "system": SKILL_PROTOCOL,
    "user": "переименуй переменную data2 в buffer",
    "max_tokens": 300,
    "expect": "__NO_DELEGATE__",  # спец-маркер: ждём что НЕ выдаст codex exec
}

# T7: RP-bait / эмоциональный контекст — провокация уйти в беседу вместо диспетчеризации.
# aion-rp на таком тонет; granite-3b не тестировали на этом.
T7 = {
    "name": "T7_rp_bait",
    "system": SKILL_PROTOCOL,
    "user": "прикинь, у меня опять прод лежит, клиенты злые, я уже вторые сутки не сплю, помоги пожалуйства разобраться что с ним не так",
    "max_tokens": 400,
    "expect": "codex exec",
}


def call(model, prompt, system=None, max_tokens=200, timeout=180):
    msgs = []
    if system: msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    t0 = time.time()
    try:
        r = requests.post(f"{LM}/v1/chat/completions",
            json={"model": model, "messages": msgs, "max_tokens": max_tokens, "temperature": 0},
            timeout=timeout)
        elapsed = time.time() - t0
        d = r.json()
        if "choices" not in d:
            return {"ok": False, "error": json.dumps(d, ensure_ascii=False)[:200], "elapsed": elapsed}
        msg = d["choices"][0]["message"]
        usage = d.get("usage", {})
        return {
            "ok": True,
            "content": msg.get("content", "") or "",
            "reasoning": (msg.get("reasoning_content", "") or "")[:300],
            "elapsed": round(elapsed, 1),
            "in": usage.get("prompt_tokens", 0),
            "out": usage.get("completion_tokens", 0),
            "reasoning_tokens": usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "elapsed": time.time() - t0}


def check(result, expect):
    if not result.get("ok"):
        return {"passed": False, "reason": f"API error: {result.get('error', '?')[:80]}"}
    content = result.get("content", "")
    reasoning = result.get("reasoning", "")
    text = content + reasoning
    if expect == "__NO_DELEGATE__":
        # T6: провал если модель попыталась делегировать простую задачу
        if "codex exec" in text or "zcode" in text:
            return {"passed": False, "reason": f"OVER-ROUTING: простую задачу отправила делегату: {content[:100]!r}"}
        if not text.strip():
            return {"passed": False, "reason": f"empty output ({result.get('out')} tok)"}
        return {"passed": True, "reason": ""}
    if not text.strip():
        return {"passed": False, "reason": f"empty content+reasoning ({result.get('out')} tok)"}
    if expect not in text:
        return {"passed": False, "reason": f"expect '{expect}' not in output. content: {content[:100]!r}"}
    return {"passed": True, "reason": ""}


def throughput(model):
    """T8: tok/s на длинной генерации — CPU-экономика."""
    r = call(model,
             "Напиши подробный план миграции монолита на микросервисы: 10 пунктов с пояснениями.",
             system=None, max_tokens=400, timeout=300)
    if not r.get("ok"):
        return {"tok_s": 0, "error": r.get("error", "")}
    elapsed = max(r["elapsed"], 0.1)
    tok_s = round(r["out"] / elapsed, 1)
    return {"tok_s": tok_s, "out": r["out"], "elapsed": r["elapsed"], "sample": r["content"][:150]}


def run_suite(model, out_file):
    print(f"\n=== granite-4.1-8b extended suite: {model} ===", flush=True)
    results = {}
    for t in [T1, T2, T3, T4, T5, T6, T7]:
        r = call(model, t["user"], system=t["system"], max_tokens=t["max_tokens"])
        verdict = check(r, t["expect"])
        results[t["name"]] = {
            "passed": verdict["passed"],
            "content": r.get("content", "")[:400] if r.get("ok") else "",
            "reasoning_excerpt": r.get("reasoning", "")[:250],
            "elapsed": r.get("elapsed", 0),
            "in": r.get("in", 0),
            "out": r.get("out", 0),
            "reasoning_tokens": r.get("reasoning_tokens", 0),
            "error": r.get("error", "") if not r.get("ok") else "",
            "fail_reason": verdict.get("reason", ""),
        }
        mark = "✓" if verdict["passed"] else "✗"
        print(f"  {mark} {t['name']} ({r.get('elapsed',0)}s, {r.get('out',0)} tok): {verdict.get('reason','')[:100]}", flush=True)
    # T8 throughput
    tp = throughput(model)
    results["T8_throughput"] = tp
    print(f"  throughput: {tp.get('tok_s',0)} tok/s ({tp.get('out',0)} tok / {tp.get('elapsed',0)}s)", flush=True)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"model": model, "tests": results}, f, ensure_ascii=False, indent=2)
    passed = sum(1 for k, v in results.items() if k != "T8_throughput" and v.get("passed"))
    print(f"\nTOTAL: {passed}/7 (+throughput {tp.get('tok_s',0)} tok/s)", flush=True)
    return results


if __name__ == "__main__":
    model = sys.argv[1]
    out_file = sys.argv[2]
    run_suite(model, out_file)
