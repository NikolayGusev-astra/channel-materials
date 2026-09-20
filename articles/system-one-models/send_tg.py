import subprocess, shutil, sys

env = {}
with open(r"C:\Users\redacted\.hermes\.env", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

token = env.get("TELEGRAM_BOT_TOKEN")
chat_id = "-1003712049089"

title = "System One Models: дешёвые вероятности вместо дорогих строк"
url = "https://telegra.ph/System-One-Models-deshyovye-veroyatnosti-vmesto-dorogih-strok-09-16-5"

html = (
    f"<b>{title}</b>\n"
    "Сложность: средняя\n\n"
    "TypeSafe выкатила Jev - модель без генерации строк: параллельные решения "
    "с калиброванными вероятностями за 70-500 мс. Разбираю, почему это не "
    "революция, а классика инженерии от реле до Калмана, и какие аналоги уже живут в проде.\n\n"
    f'\u2192 <a href="{url}">Читать на Telegra.ph</a>\n\n'
    "\U0001F310 hermes-agent.ru"
)

payload = {
    "chat_id": chat_id,
    "text": html,
    "parse_mode": "HTML",
    "disable_web_page_preview": False,
    "link_preview_options": {"url": url, "prefer_large_media": True},
}

import json
with open("_payload.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)

curl = shutil.which("curl") or "curl"
r = subprocess.run(
    [curl, "-s", "-X", "POST",
     f"https://api.telegram.org/bot{token}/sendMessage",
     "-H", "Content-Type: application/json",
     "--data-binary", "@_payload.json"],
    capture_output=True, text=True, encoding="utf-8", timeout=60)
print("STDOUT:", r.stdout[:600])
print("STDERR:", r.stderr[:300])
# em-dash/guillemet gate
raw = open("_payload.json", encoding="utf-8").read()
print("em-dash:", raw.count("\u2014"), "guillemet:", raw.count("\u00ab") + raw.count("\u00bb"))
