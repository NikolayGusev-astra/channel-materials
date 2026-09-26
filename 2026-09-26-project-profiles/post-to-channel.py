"""Post to @hermesagentru with Jill cover attached (sendPhoto + caption).

Network: api.telegram.org needs PySocks with rdns=True; the plain env proxy
breaks CONNECT (RemoteDisconnected). HTTPError body must be read as JSON.
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
                    TOKEN = (
                        _line.split("=", 1)[1].strip().strip('"').strip("'")
                    )
                    break
    except OSError:
        continue
    if TOKEN:
        break
if not TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN not found")

CHAT = "@hermesagentru"
PHOTO = sys.argv[1]
CAPTION = open(sys.argv[2], encoding="utf-8").read().strip()


def api(method, payload):
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        return json.loads(opener.open(req, timeout=60).read())
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": e.read().decode("utf-8", "replace")}


# 1. uploadPhoto
with open(PHOTO, "rb") as f:
    photo_bytes = f.read()

boundary = "----hermesboundary"
parts = []
parts.append(f"--{boundary}\r\n".encode())
parts.append(
    b'Content-Disposition: form-data; name="chat_id"\r\n\r\n' + CHAT.encode() + b"\r\n"
)
parts.append(f"--{boundary}\r\n".encode())
parts.append(
    b'Content-Disposition: form-data; name="photo"; filename="cover.png"\r\n'
    b"Content-Type: image/png\r\n\r\n" + photo_bytes + b"\r\n"
)
parts.append(f"--{boundary}\r\n".encode())
parts.append(
    b'Content-Disposition: form-data; name="caption"\r\n\r\n'
    + CAPTION.encode("utf-8")
    + b"\r\n"
)
parts.append(
    f"--{boundary}\r\n".encode()
    + b'Content-Disposition: form-data; name="parse_mode"\r\n\r\nHTML\r\n'
)
parts.append(f"--{boundary}--\r\n".encode())
body = b"".join(parts)

req = urllib.request.Request(
    f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
)
try:
    res = json.loads(opener.open(req, timeout=120).read())
except urllib.error.HTTPError as e:
    res = {"ok": False, "error": e.read().decode("utf-8", "replace")}

if res.get("ok"):
    msg = res["result"]
    print("OK photo:", msg.get("message_id"), "| caption chars:", len(msg.get("caption", "")))
else:
    print("FAIL:", json.dumps(res, ensure_ascii=False)[:600])
    raise SystemExit(1)
