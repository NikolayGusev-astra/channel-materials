import json, urllib.request, os, time
from pathlib import Path

env = Path(os.path.expanduser("~/.hermes/.env")).read_text(encoding="utf-8")
token = None
for l in env.splitlines():
    if l.startswith("TELEGRAM_BOT_TOKEN="):
        token = l.split("=", 1)[1].strip().strip('"').strip("'")
proxy = os.environ.get("HTTPS_PROXY") or "http://127.0.0.1:12334"

html = """<b>Нейросети в играх: королева-собутыльник и зачем Minecraft-агенту зрение</b>

Сложность: средняя

Voices of the Court превращает CK3 в настолку с живым мастером: персонажи болтают через LLM и выполняют реальные игровые действия. Разбираю архитектуру мода, платформу Player2, связку CK3+Bannerlord и главный вопрос агентного Minecraft: Voyager играет вслепую и обгоняет всех, а зрение нужно только когда агент управляет игрой мышью по пикселям.

→ Читать на Telegra.ph: https://telegra.ph/Nejroseti-v-igrah-koroleva-sobutylnik-i-zachem-Minecraft-agentu-zrenie-09-08-2

🌐 hermes-agent.ru
📦 Материалы и харнессы: [GitHub](https://github.com/NikolayGusev-astra/channel-materials) | [GitFlic](https://gitflic.ru/manve-sulimo2/channel-materials)
ℹ️ Хотите попробовать, но нет времени разбираться? Напишите в контакты на сайте — поможем с настройкой и подбором сценария под ваши задачи.
🛠 Наши сервисы: pii-guard.ru | llm.pii-guard.ru | hermes-agent.ru | shturman.ai — сотрудничество и вопросы: TG @sneg1313"""

payload = json.dumps({
    "chat_id": -1003712049089,
    "text": html,
    "parse_mode": "HTML",
    "disable_web_page_preview": True,
}).encode("utf-8")

opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
resp = opener.open(urllib.request.Request(
    f"https://api.telegram.org/bot{token}/sendMessage",
    data=payload, headers={"Content-Type": "application/json"}), timeout=30)
d = json.loads(resp.read())
print(json.dumps(d, ensure_ascii=False)[:300])

# Verify: forward to same channel, check entities, then delete
if d.get("ok"):
    mid = d["result"]["message_id"]
    fp = json.dumps({"chat_id": -1003712049089, "from_chat_id": -1003712049089, "message_id": mid}).encode()
    r2 = json.loads(opener.open(urllib.request.Request(
        f"https://api.telegram.org/bot{token}/forwardMessage",
        data=fp, headers={"Content-Type": "application/json"}), timeout=30).read())
    ents = r2.get("result", {}).get("entities", [])
    print("forward entities:", [(e["type"], r2["result"]["text"][e["offset"]:e["offset"]+40]) for e in ents][:8])
    dp = json.dumps({"chat_id": -1003712049089, "message_id": r2["result"]["message_id"]}).encode()
    r3 = json.loads(opener.open(urllib.request.Request(
        f"https://api.telegram.org/bot{token}/deleteMessage",
        data=dp, headers={"Content-Type": "application/json"}), timeout=30).read())
    print("cleanup:", r3.get("ok"))
