#!/usr/bin/env python3
"""
model-routing — детерминированный диспетчер моделей.

Использование:
  hermes-route "task text"     # → JSON {category, score, model, command}
  hermes-route --json "task"   # то же
  hermes-route --md "task"     # → markdown-таблица для вывода в чат

Не требует LLM. Делает скоринг по регексам, возвращает готовую команду
для delegate_task или прямого вызова. Используется как часть model-routing skill.
"""
import re
import sys
import json
import argparse
from pathlib import Path


# Скоринг: (паттерн, вес, имя_сигнала)
SIGNALS = [
    (r"\b(разбей|разделить|разбить|план[уа]?|фаза|3\+?\s*задач|3\+?\s*файл|многошаг)\b", 4, "subtasks_many"),
    (r"\b(найди\s+все|все\s+usages|все\s+вхождения|каждое\s+|все\s+файл|все\s+использовани)\b", 4, "exhaustive_search"),
    (r"(архитектур[а-я]*|ADR|архитектурн[а-я]*\s+(?:решени|паттерн|обзор)|спроектир[а-я]*|схема\s+БД|миграци[яи]\s+схем)", 3, "architecture_keywords"),
    (r"(прод(?:акт|uction)?|весь\s+пайплайн|все\s+репо|все\s+нод|все\s+сервис|production|deploy\s+на\s+прод)", 3, "impact_system_wide"),
    (r"(безопасност[ьи]?|security|деньг[иа]|необратим[а-я]*|аутентификац[ьи]?|авторизац[ьи]?|идемпотентност[ьи]?|pci\s+d|gdpr|152[\s\-]фз)", 2, "risk_keywords"),
    (r"(падае[тм]|429|500|таймаут|race\s+condition|утечк[аи]|репликаци[яи]|crash|exception|stack\s*trace|traceback)", 2, "debugging_keywords"),
    (r"(распараллель|параллельн[а-я]*|fan[\s\-]?out|одновременно\s+нескольк|субагент[а-я]*|delegate\s+task)", 2, "fanout_intent"),
    (r"(3\+?\s*файл|3\+?\s*модул|нескольк[а-я]*\s+(?:файл|модул|функц)|правки\s+в\s+\d+|рефакторинг[а-я]*|многофайл[а-я]*)", 2, "cross_file"),
    (r"\b(переимену[йт]|формат[а-я]*|опечатк[аи]|однострочник[а-я]*|мелоч[ьи]?)\b", -2, "simple_request"),
]

CATEGORIES = [
    (0, 2, "quick"),
    (3, 5, "standard"),
    (6, 9, "deep"),
    (10, 999, "architect"),
]

# Цепочки. Формат: category → [(provider, model, mode, fallback_command)]
# mode: "direct" = мой прямой вызов; "delegate" = субагент через delegate_task
CHAINS = {
    "quick": [
        # quick — ответить сама
        ("self", "self", "self", None),
    ],
    "standard": [
        ("codex", "gpt-5.6-terra", "delegate", 'codex exec -m gpt-5.6-terra "{task}"'),
        ("zcode", "glm-5.3", "delegate", 'zcode -p "{task}"'),
        ("openrouter", "tencent/hy3:free", "direct", 'curl -s https://openrouter.ai/api/v1/chat/completions -H "Authorization: Bearer $OPENROUTER_API_KEY" -d \'{{"model":"tencent/hy3:free","messages":[{{"role":"user","content":"{task}"}}]}}\''),
    ],
    "deep": [
        ("codex", "gpt-5.6-terra", "delegate", 'codex exec -m gpt-5.6-terra "{task}"'),
        ("zcode", "glm-5.3", "delegate", 'zcode -p "{task}"'),
        ("openrouter", "tencent/hy3:free", "direct", 'curl -s https://openrouter.ai/api/v1/chat/completions -H "Authorization: Bearer $OPENROUTER_API_KEY" -d \'{{"model":"tencent/hy3:free","messages":[{{"role":"user","content":"{task}"}}]}}\''),
    ],
    "architect": [
        ("codex", "gpt-5.6-sol", "delegate", 'codex exec -m gpt-5.6-sol "{task}"'),
        ("zcode", "glm-5.3", "delegate", 'zcode -p "{task}"'),
    ],
    "ultrabrain": [
        ("codex", "gpt-5.6-sol-xhigh", "delegate", 'codex exec -m gpt-5.6-sol --reasoning-effort xhigh "{task}"'),
    ],
}


def score_task(task: str) -> tuple[int, list[dict]]:
    """Подсчитать сигналы и вернуть (score, [matched_signals])."""
    text = task.lower()
    matches = []
    total = 0
    for pattern, weight, name in SIGNALS:
        m = re.search(pattern, text, re.IGNORECASE | re.UNICODE)
        if m:
            matches.append({
                "signal": name,
                "weight": weight,
                "matched": m.group(0),
            })
            total += weight
    return total, matches


def classify(score: int) -> str:
    for lo, hi, cat in CATEGORIES:
        if lo <= score <= hi:
            return cat
    return "quick"


def route(task: str) -> dict:
    """Главная функция: скоринг → категория → цепочка → команда."""
    score, signals = score_task(task)
    category = classify(score)
    if score >= 15:
        category = "ultrabrain"
    chain = CHAINS.get(category, CHAINS["standard"])
    return {
        "task": task[:200],
        "score": score,
        "signals": signals,
        "category": category,
        "chain": [
            {"provider": p, "model": m, "mode": mode, "command": cmd}
            for p, m, mode, cmd in chain
        ],
        "primary": {
            "provider": chain[0][0],
            "model": chain[0][1],
            "mode": chain[0][2],
            "command": chain[0][3].format(task=task) if chain[0][3] else None,
        } if chain[0][2] != "self" else {"mode": "self", "instruction": "ответь сам(а), без делегации"},
    }


def to_markdown(r: dict) -> str:
    """Красивый вывод для чата."""
    lines = []
    lines.append(f"## model-routing")
    lines.append(f"**Score:** {r['score']}  **Category:** `{r['category']}`")
    if r["signals"]:
        lines.append("")
        lines.append("**Сигналы:**")
        for s in r["signals"]:
            lines.append(f"- `{s['signal']}` +{s['weight']} (matched: `{s['matched']}`)")
    lines.append("")
    lines.append("**Цепочка:**")
    for i, link in enumerate(r["chain"], 1):
        lines.append(f"{i}. `{link['provider']}/{link['model']}` ({link['mode']})")
    p = r["primary"]
    if p.get("command"):
        lines.append("")
        lines.append(f"**Команда (звено 1):**")
        lines.append(f"```\n{p['command']}\n```")
    elif p.get("instruction"):
        lines.append("")
        lines.append(f"**Действие:** {p['instruction']}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Детерминированный диспетчер моделей.")
    ap.add_argument("task", nargs="?", help="Текст задачи")
    ap.add_argument("--json", action="store_true", help="Вывод в JSON")
    ap.add_argument("--md", action="store_true", help="Вывод в markdown")
    args = ap.parse_args()

    if not args.task:
        if sys.stdin.isatty():
            print("Usage: hermes-route 'task text'", file=sys.stderr)
            sys.exit(1)
        else:
            args.task = sys.stdin.read().strip()

    if not args.task:
        print("Empty task", file=sys.stderr)
        sys.exit(1)

    r = route(args.task)

    if args.md:
        print(to_markdown(r))
    elif args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        # default: JSON в stdout
        print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
