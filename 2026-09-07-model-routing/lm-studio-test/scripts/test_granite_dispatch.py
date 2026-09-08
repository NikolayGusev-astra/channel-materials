"""Вариант А, финал: granite-3b как диспетчер через НАТИВНЫЙ tool-call.
Инструменты = delegate_task + ask_user. Большой timeout (модель медленно стартует с tools).
"""
import requests, json, time

TOOLS = [
    {"type": "function", "function": {
        "name": "delegate_task",
        "description": "Delegate a task to a subagent. Pass the full task description in goal.",
        "parameters": {"type": "object", "properties": {
            "goal": {"type": "string", "description": "Full task description"},
            "model_hint": {"type": "string", "description": "Suggested model: quick/standard/deep/architect"},
        }, "required": ["goal"]},
    }},
    {"type": "function", "function": {
        "name": "answer_self",
        "description": "Answer directly without delegation. Use ONLY for trivial tasks (rename, typo, one-liner).",
        "parameters": {"type": "object", "properties": {
            "answer": {"type": "string"},
        }, "required": ["answer"]},
    }},
]

SYSTEM = """You are a model-routing dispatcher. Score each task:
plan/split +4, find-all +4, architecture +3, production +3, security +2, bug +2, parallel +2, 3+files +2, trivial -2.
Categories: 0-2 quick, 3-5 standard, 6-9 deep, 10+ architect.
For quick tasks call answer_self. For standard/deep call delegate_task with model_hint=standard/deep. For architect call delegate_task with model_hint=architect.
NEVER solve the task yourself."""

def dispatch(model, task, timeout=300):
    t0 = time.time()
    r = requests.post("http://127.0.0.1:1234/v1/chat/completions", timeout=timeout, json={
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}],
        "tools": TOOLS,
        "tool_choice": "auto",
        "max_tokens": 500,
        "temperature": 0,
    })
    el = round(time.time() - t0, 1)
    d = r.json()
    m = d["choices"][0]["message"]
    tc = m.get("tool_calls") or []
    if tc:
        fn = tc[0]["function"]
        return {"verdict": "TOOL_CALL", "fn": fn["name"], "args": fn["arguments"][:220], "elapsed": el,
                "finish": d["choices"][0].get("finish_reason")}
    return {"verdict": "TEXT", "content": (m.get("content") or "")[:200], "elapsed": el,
            "finish": d["choices"][0].get("finish_reason")}

TESTS = [
    ("quick", "переименуй переменную data2 в buffer"),
    ("standard", "найди все использования deprecated API и почини"),
    ("deep", "нужно распараллелить загрузку данных и починить race condition в трёх модулях пайплайна"),
    ("architect", "спроектируй архитектуру платежного микросервиса с безопасностью и идемпотентностью"),
]

if __name__ == "__main__":
    import sys
    model = sys.argv[1] if len(sys.argv) > 1 else "granite-4.1-3b"
    results = {}
    for cat, task in TESTS:
        r = dispatch(model, task)
        results[cat] = r
        print(f"[{cat:>9}] {r['verdict']} ({r['elapsed']}s): {r.get('fn', '')} | {r.get('args') or r.get('content', '')[:150]}", flush=True)
    with open(r"C:\Users\n.gusev\AppData\Local\Temp\granite_tc_dispatch.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
