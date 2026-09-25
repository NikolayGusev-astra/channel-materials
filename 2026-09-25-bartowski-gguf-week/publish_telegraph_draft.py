import importlib.util
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(r"C:\Work\Assist\channel-materials\2026-09-25-bartowski-gguf-week")
ARTICLE = ROOT / "article.md"
SCRIPT = Path(r"C:\Users\n.gusev\AppData\Local\hermes\skills\content\writer\scripts\telegraph-publish-direct.py")
TITLE = "Бартовски за неделю упаковал девять моделей. Две уже стали хитами - ЧЕРНОВИК для вычитки"
AUTHOR = "Гусев Николай"
PATH = "Bartovski-za-nedelyu-upakoval-devyat-modelej-Dve-uzhe-stali-hitami-09-25"


def load_module():
    spec = importlib.util.spec_from_file_location("telegraph_writer", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_token(env_path: Path) -> str:
    if not env_path.exists():
        raise RuntimeError(f"Missing {env_path}")
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        if raw.strip().startswith("TELEGRAPH_TOKEN="):
            return raw.strip().partition("=")[2].strip().strip('"\'')
    raise RuntimeError("TELEGRAPH_TOKEN not found")


def call_api(endpoint: str, payload: dict) -> dict:
    fd, tmp_name = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        cmd = [
            "curl", "--silent", "--show-error", "--socks5-hostname", "127.0.0.1:12334",
            "--connect-timeout", "20", "--max-time", "60", "-H", "Content-Type: application/json",
            "--data-binary", f"@{tmp}", f"https://api.telegra.ph/{endpoint}",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or f"curl exit {proc.returncode}")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid API JSON: {proc.stdout[:300]}") from exc
    finally:
        tmp.unlink(missing_ok=True)


def main():
    mod = load_module()
    text = ARTICLE.read_text(encoding="utf-8")
    if not ARTICLE.exists():
        raise RuntimeError("article.md missing")
    checks = {
        "em_dash": text.count("\u2014"),
        "guillemets": text.count("\u00ab") + text.count("\u00bb"),
        "cjk": len(re.findall(r"[\u4e00-\u9fff]", text)),
    }
    if any(checks.values()):
        raise RuntimeError(f"Blocked glyphs: {checks}")

    # Markdown images are converted to Telegraph img nodes with absolute HTTPS URLs.
    token = get_token(Path.home() / ".hermes" / ".env")
    lines = []
    image_nodes = []
    for line in text.splitlines():
        match = re.fullmatch(r"!\[([^\]]*)\]\((https://[^)]+)\)\s*", line.strip())
        if match:
            if image_nodes:
                lines.append("")
            image_nodes.append({"tag": "img", "attrs": {"src": match.group(2)}})
        else:
            lines.append(line)
    md = "\n".join(lines)
    body = mod.md_to_dom(md)
    first_body_index = next((i for i, node in enumerate(body) if node.get("tag") != "hr"), 0)
    dom = body[:first_body_index]
    for node in image_nodes:
        dom.append(node)
    dom.extend(body[first_body_index:])
    data = call_api("editPage", {
        "access_token": token,
        "path": PATH,
        "title": TITLE,
        "author_name": AUTHOR,
        "author_url": "https://hermes-agent.ru",
        "content": dom,
    })
    if not data.get("ok"):
        raise RuntimeError(data)
    print(json.dumps({"url": data["result"]["url"], "checks": checks, "nodes": len(dom)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
