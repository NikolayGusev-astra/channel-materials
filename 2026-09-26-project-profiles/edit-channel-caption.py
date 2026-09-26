"""Edit an existing channel post's CAPTION in place (photo post -> editMessageCaption).

Never republish to fix a broken link or a typo: a duplicate post is a failure,
the owner has to delete it by hand (incident 22.09.2026, msgs 263/264).

Usage:
  python edit-channel-caption.py <message_id> <caption_file.html>
"""
import json
import os
import socket
import sys

import socks
import urllib.error
import urllib.request

for v in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(v, None)

socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 12334, rdns=True)
socket.socket = socks.socksocket
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

TOKEN = ""
for _p in (
    os.path.expanduser("~/.hermes/.env"),
    os.path.expanduser("~/AppData/Local/hermes/.env"),
):
    try:
        with open(_p, encoding="utf-8") as f:
            for _line in f:
                if _line.strip().startswith("TELEGRAM_BOT_TOKEN="):
                    TOKEN = _line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    except OSError:
        continue
    if TOKEN:
        break
if not TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN not found")

message_id = sys.argv[1]
caption = open(sys.argv[2], encoding="utf-8").read().strip()

payload = {
    "chat_id": "@hermesagentru",
    "message_id": int(message_id),
    "caption": caption,
    "parse_mode": "HTML",
}
req = urllib.request.Request(
    f"https://api.telegram.org/bot{TOKEN}/editMessageCaption",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
try:
    res = json.loads(opener.open(req, timeout=60).read())
except urllib.error.HTTPError as e:
    res = {"ok": False, "error": e.read().decode("utf-8", "replace")}

if res.get("ok"):
    print("OK edited caption:", message_id, "| chars:", len(caption))
else:
    print("FAIL:", json.dumps(res, ensure_ascii=False)[:600])
    raise SystemExit(1)
