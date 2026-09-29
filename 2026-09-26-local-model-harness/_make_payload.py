import os
import sys
import json
import importlib.util

SCRIPT = r"<local-path>\Users\n.gusev\AppData\Local\hermes\skills\content\writer\scripts\telegraph-publish-direct.py"
spec = importlib.util.spec_from_file_location("tpd", SCRIPT)
tpd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tpd)

ART = r"<local-path>\Work\Assist\channel-materials\2026-09-26-local-model-harness\article.md"
OUT = os.path.join(os.environ["LOCALAPPDATA"], "Temp", "telegraph_local_harness.json")

with open(ART, encoding="utf-8") as f:
    md = f.read()

token = tpd.get_token()
if not token:
    sys.exit("NO_TOKEN")

dom = tpd.md_to_dom(md)
payload = {
    "access_token": token,
    "title": "Чем проще модель, тем сложнее инструкция (ЧЕРНОВИК для вычитки)",
    "author_name": "Гусев Николай",
    "content": json.dumps(dom, ensure_ascii=False),
    "return_content": "false",
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)

print("NODES:", len(dom))
print("PAYLOAD:", OUT)
print("SIZE:", os.path.getsize(OUT))
