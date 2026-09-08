"""Дуэль квантов MiniCPM5-2B: Q4_K_M / Q8_0 / Q8_0+draft(Q4) / F16+draft(Q4).
СТРОГАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ. GPU full offload (--gpu max), контекст 65536.
Спекулятивный декодинг: Q4_K_M как draft для старших квантов.
"""
import subprocess, time, json, os

BASH = 'C:/Program Files/Git/usr/bin/bash.exe'
LMS = '/c/Users/n.gusev/.lmstudio/bin/lms'
OUT_DIR = r"C:\Users\n.gusev\AppData\Local\Temp\lm_test"
os.makedirs(OUT_DIR, exist_ok=True)

# Конфиги: (тег, load-команда args)
# A/B дизайн: каждый квант с драфтом и без - измеряем и скорость, и влияет ли драфт на точность/результаты.
# Ключи моделей: lms ls показывает "minicpm5-2b@q4_k_m" формат (не HF-путь!).
CONFIGS = [
    ("q4",         'load "minicpm5-2b@q4_k_m" --gpu max -c 65536 --identifier minicpm-q4 -y'),
    ("q8",         'load "minicpm5-2b@q8_0" --gpu max -c 65536 --identifier minicpm-q8 -y'),
    ("q8_draft",   'load "minicpm5-2b@q8_0" --gpu max -c 65536 --identifier minicpm-q8d '
                   '--speculative-draft-simple --speculative-draft-model "minicpm5-2b@q4_k_m" '
                   '--speculative-draft-max-tokens 8 --speculative-draft-min-continue-probability 0.5 -y'),
    ("f16",        'load "minicpm5-2b@f16" --gpu max -c 65536 --identifier minicpm-f16 -y'),
    ("f16_draft",  'load "minicpm5-2b@f16" --gpu max -c 65536 --identifier minicpm-f16d '
                   '--speculative-draft-simple --speculative-draft-model "minicpm5-2b@q4_k_m" '
                   '--speculative-draft-max-tokens 8 --speculative-draft-min-continue-probability 0.5 -y'),
]

TOOLS = None
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


def run(cmd, timeout=300):
    try:
        r = subprocess.run([BASH, '-c', cmd], capture_output=True, text=True, errors='replace', timeout=timeout)
        return (r.stdout or "") + (r.stderr or ""), r.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", -1


def get_tools():
    return [
        {"type": "function", "function": {
            "name": "delegate_task",
            "description": "Delegate a task to a subagent. Pass the full task description in goal.",
            "parameters": {"type": "object", "properties": {
                "goal": {"type": "string"},
                "model_hint": {"type": "string", "description": "quick/standard/deep/architect"},
            }, "required": ["goal"]},
        }},
        {"type": "function", "function": {
            "name": "answer_self",
            "description": "Answer directly without delegation. ONLY for trivial tasks.",
            "parameters": {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]},
        }},
    ]


import requests


def tc_suite(model_id):
    """4 категории tool-call. Возвращает passed/4 и детали."""
    res = {}
    passed = 0
    for cat, task, want_fn, want_hint in TESTS:
        body = {
            "model": model_id,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}],
            "tools": get_tools(), "tool_choice": "auto",
            "max_tokens": 600, "temperature": 0,
        }
        t0 = time.time()
        try:
            r = requests.post("http://127.0.0.1:1234/v1/chat/completions", timeout=300, json=body)
            el = round(time.time() - t0, 1)
            d = r.json()
            if "choices" not in d:
                res[cat] = {"passed": False, "err": json.dumps(d, ensure_ascii=False)[:120]}
                print(f"    {cat}: ERR {res[cat]['err'][:80]}", flush=True)
                continue
            m = d["choices"][0]["message"]
            tc = m.get("tool_calls") or []
            fn = tc[0]["function"]["name"] if tc else None
            hint, goal = None, ""
            if tc:
                try:
                    a = json.loads(tc[0]["function"]["arguments"])
                    hint, goal = a.get("model_hint"), a.get("goal", "")[:70]
                except Exception:
                    pass
            ok = fn == want_fn and (want_hint is None or hint == want_hint)
            passed += ok
            res[cat] = {"passed": ok, "fn": fn, "hint": hint, "goal": goal, "elapsed": el,
                        "out": d["usage"]["completion_tokens"]}
            print(f"    {cat}: {'OK' if ok else 'FAIL'} ({el}s) fn={fn} hint={hint}", flush=True)
            print(f"      goal: {goal!r}", flush=True)
        except Exception as e:
            res[cat] = {"passed": False, "err": str(e)[:120]}
            print(f"    {cat}: EXC {str(e)[:80]}", flush=True)
    res["passed"] = f"{passed}/4"
    return res


def throughput(model_id):
    """Изолированный tok/s на 400 токенах."""
    body = {"model": model_id,
            "messages": [{"role": "user", "content": "Напиши подробный план миграции монолита на микросервисы: 10 пунктов с пояснениями."}],
            "max_tokens": 400, "temperature": 0}
    t0 = time.time()
    try:
        r = requests.post("http://127.0.0.1:1234/v1/chat/completions", timeout=300, json=body)
        el = max(time.time() - t0, 0.1)
        d = r.json()
        if "choices" not in d:
            return {"err": json.dumps(d, ensure_ascii=False)[:120]}
        out = d["usage"]["completion_tokens"]
        ts = round(out / el, 1)
        print(f"    throughput: {ts} tok/s ({out} tok / {el:.1f}s)", flush=True)
        return {"tok_s": ts, "out": out, "elapsed": round(el, 1)}
    except Exception as e:
        return {"err": str(e)[:120]}


if __name__ == "__main__":
    summary = {}
    for tag, load_args in CONFIGS:
        print(f"\n=== {tag} ===", flush=True)
        run(f'{LMS} unload --all', timeout=60)
        time.sleep(3)
        out, rc = run(f'{LMS} {load_args}', timeout=900)
        if "loaded successfully" not in out:
            print(f"  LOAD FAILED: {out[-200:]}", flush=True)
            summary[tag] = {"load_failed": out[-200:]}
            continue
        # Определяем identifier (последний --identifier в команде)
        ident = load_args.split("--identifier ")[1].split(" ")[0].strip("'\"")
        # Верификация: какой реальный GGUF загрузился (лмс сам выбрал из репо)
        ps_out, _ = run(f'{LMS} ps', timeout=30)
        loaded_model_line = [l for l in ps_out.split("\n") if ident in l]
        real_model = loaded_model_line[0].split()[1] if loaded_model_line else "?"
        print(f"  loaded as {ident} (model: {real_model})", flush=True)
        summary[tag] = {"loaded_model": real_model}
        time.sleep(4)  # прогрев

        s = {"tc": tc_suite(ident), "throughput": throughput(ident)}
        summary[tag].update(s)

        # Гигиена: всё выгрузить после каждого конфига
        run(f'{LMS} unload --all', timeout=60)
        time.sleep(2)

    with open(os.path.join(OUT_DIR, "quant_duel_results.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\n=== СВОДКА ===", flush=True)
    for tag, s in summary.items():
        if s.get("load_failed"):
            print(f"  {tag}: LOAD FAILED", flush=True)
            continue
        tp = s.get("throughput", {}).get("tok_s", "?")
        print(f"  {tag}: TC {s['tc'].get('passed')} | {tp} tok/s", flush=True)
    print("QUANT_DUEL_DONE", flush=True)
