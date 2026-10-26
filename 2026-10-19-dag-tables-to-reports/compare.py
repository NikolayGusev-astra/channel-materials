import json, re, unicodedata

d = json.load(open("data/narrow.json", encoding="utf-8"))
facts = {f["slug"]: f for f in d["facts"]}
truth = {k: v["trend"] for k, v in facts.items()}

# Семантика вместо ярлыка: модель могла сказать верно другими словами
SEM = {
    "новинка":   ["вышла", "новая", "новинка", "недавно", "только что", "свежая", "публикации"],
    "рост":      ["растёт", "растет", "рост", "увеличил", "возрос", "интерес раст"],
    "спад":      ["спад", "угаса", "снизил", "падает", "меньше", "ослаб", "упал"],
    "стабильно": ["стабил", "сохран", "ровн", "держится", "не меня"],
}

def semantic(reason, expected):
    r = reason.lower()
    return any(k in r for k in SEM[expected])

print(f"{'статья':36} {'факт':10} {'модель':10} смысл")
print("-" * 78)
# берём прозу yandexgpt из прошлого прогона (в narrow.json только сводка) — восстановим из лога
import subprocess
txt = open("run_gemma2.log", encoding="utf-8", errors="replace").read() if __import__("os").path.exists("run_gemma2.log") else ""
print("(проверка смысла — после прогона gemma)")
