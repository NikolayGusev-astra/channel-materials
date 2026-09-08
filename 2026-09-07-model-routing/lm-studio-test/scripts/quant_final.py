"""Финальная дискретная сюита: 3 кванта x 4 категории, байт-точные вчерашние tools.
По очереди, изоляция unload после каждого. Результат - истина для статьи.
"""
import subprocess, time, json, os, requests

BASH = 'C:/Program Files/Git/usr/bin/bash.exe'
LMS = '/c/Users/n.gusev/.lmstudio/bin/lms'
OUT = r"C:\Users\n.gusev\AppData\Local\Temp\lm_test\quant_final.json"

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

TESTS = [
    ("quick", "переименуй переменную data2 в buffer", "answer_self", None),
    ("standard", "найди все использования deprecated API и почини", "delegate_task", "standard"),
    ("deep", "нужно распараллелить загрузку данных и починить race condition в трёх модулях пайплайна", "delegate_task", "deep"),
    ("architect", "спроектируй архитектуру платежного микросервиса с безопасностью и идемпотентностью", "delegate_task", "architect"),
]

QUANTS = [("q4", "minicpm5-2b@q4_k_m"), ("q8", "minicpm5-2b@q8_0"), ("f16", "minicpm5-2b@f16")]


def run(cmd, timeout=300):
    try:
        r = subprocess.run([BASH, '-c', cmd], capture_output=True, text=True, errors='replace', timeout=timeout)
        return (r.stdout or "") + (r.stderr or ""), r.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", -1


if __name__ == "__main__":
    summary = {}
    for tag, key in QUANTS:
        print(f"\n=== {tag} ({key}) ===", flush=True)
        run(f'{LMS} unload --all', timeout=90)
        time.sleep(4)
        out, _ = run(f'{LMS} load "{key}" --gpu max -c 65536 -y', timeout=900)
        if "loaded successfully" not in out:
            print("  LOAD FAILED", flush=True)
            summary[tag] = {"load_failed": True}
            continue
        ident = key.replace("@", "-")  # identifier = последний сегмент с @ заменой? нет - LM Studio вернёт свой
        # Достаём фактический identifier из вывода
        ident = [l.split('"')[1] for l in out.split("\n") if 'use the identifier' in l]
        ident = ident[0] if ident else key
        print(f"  identifier: {ident}", flush=True)
        time.sleep(4)

        res = {"passed": 0}
        for cat, task, want_fn, want_hint in TESTS:
            t0 = time.time()
            r = requests.post("http://127.0.0.1:1234/v1/chat/completions", timeout=300, json={
                "model": ident,
                "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}],
                "tools": TOOLS, "tool_choice": "auto", "max_tokens": 1500, "temperature": 0})
            el = round(time.time() - t0, 1)
            d = r.json()
            m = d["choices"][0]["message"]
            tc = m.get("tool_calls") or []
            fn = tc[0]["function"]["name"] if tc else None
            hint, goal = None, ""
            if tc:
                try:
                    a = json.loads(tc[0]["function"]["arguments"])
                    hint, goal = a.get("model_hint"), a.get("goal", a.get("answer", ""))[:90]
                except Exception:
                    pass
            ok = fn == want_fn and (want_hint is None or hint == want_hint)
            res["passed"] += ok
            res[cat] = {"ok": ok, "fn": fn, "hint": hint, "text": goal, "elapsed": el,
                        "out": d["usage"]["completion_tokens"]}
            print(f"  {cat}: {'OK' if ok else 'FAIL'} ({el}s) fn={fn} hint={hint} out={res[cat]['out']}", flush=True)
            print(f"    text: {goal!r}", flush=True)

        # throughput
        t0 = time.time()
        r = requests.post("http://127.0.0.1:1234/v1/chat/completions", timeout=300, json={
            "model": ident,
            "messages": [{"role": "user", "content": "Напиши подробный план миграции монолита на микросервисы: 10 пунктов с пояснениями."}],
            "max_tokens": 400, "temperature": 0})
        el = max(time.time() - t0, 0.1)
        d = r.json()
        out_t = d["usage"]["completion_tokens"]
        res["throughput"] = round(out_t / el, 1)
        print(f"  throughput: {res['throughput']} tok/s", flush=True)

        summary[tag] = res
        run(f'{LMS} unload --all', timeout=90)
        time.sleep(3)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\n=== ФИНАЛ ===", flush=True)
    for tag, r in summary.items():
        print(f"  {tag}: {r['passed']}/4 | {r.get('throughput')} tok/s", flush=True)
    print("QUANT_FINAL_DONE", flush=True)
