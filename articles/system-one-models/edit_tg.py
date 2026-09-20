import subprocess, shutil, json

env = {}
with open(r"C:\Users\redacted\.hermes\.env", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

token = env["TELEGRAM_BOT_TOKEN"]
chat = "-1003712049089"
url = "https://telegra.ph/System-One-Models-deshyovye-veroyatnosti-vmesto-dorogih-strok-09-16-5"

GH = "https://github.com/NikolayGusev-astra/channel-materials"
GF = "https://gitflic.ru/manve-sulimo2/channel-materials"

html = (
    "<b>System One Models: дешёвые вероятности вместо дорогих строк</b>\n"
    "Сложность: средняя\n\n"
    "TypeSafe выкатила Jev - модель без генерации строк: параллельные решения "
    "с калиброванными вероятностями за 70-500 мс. Разбираю, почему это не "
    "революция, а классика инженерии от реле до Калмана, и какие аналоги уже живут в проде.\n\n"
    f'\u2192 <a href="{url}">Читать на Telegra.ph</a>\n\n'
    "\U0001F310 hermes-agent.ru\n"
    f"\U0001F4E6 Материалы и харнессы: <a href=\"{GH}\">GitHub</a> | <a href=\"{GF}\">GitFlic</a>\n"
    "\u2139\uFE0F Хотите попробовать, но нет времени разбираться? Напишите в контакты на сайте - поможем с настройкой и подбором сценария под ваши задачи.\n"
    "\U0001F6E0 Наши сервисы: pii-guard.ru | llm.pii-guard.ru | hermes-agent.ru | shturman.ai - сотрудничество и вопросы: TG @sneg1313"
)

payload = {
    "chat_id": chat,
    "message_id": 226,
    "text": html,
    "parse_mode": "HTML",
    "link_preview_options": {"url": url, "prefer_large_media": True},
}
with open("_edit_payload.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)

curl = shutil.which("curl") or "curl"
r = subprocess.run(
    [curl, "-s", "-X", "POST",
     f"https://api.telegram.org/bot{token}/editMessageText",
     "-H", "Content-Type: application/json",
     "--data-binary", "@_edit_payload.json"],
    capture_output=True, text=True, encoding="utf-8", timeout=60)
print(r.stdout[:900])
