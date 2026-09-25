import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(r"C:\Work\Assist\channel-materials\2026-09-25-bartowski-gguf-week")
TELEGRAPH_URL = "https://telegra.ph/Bartovski-za-nedelyu-upakoval-devyat-modelej-Dve-uzhe-stali-hitami-09-25"
SITE_URL = "https://hermes-agent.ru/news/bartowski-gguf-week/"
CHANNEL_ID = "-1003712049089"


def read_active_env(path: Path) -> dict:
    values = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def send_photo(chat_id: str, photo: Path, caption: str) -> dict:
    fd, name = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    caption_path = Path(name)
    try:
        caption_path.write_text(caption, encoding="utf-8")
        proc = subprocess.run(
            [
                "curl", "--silent", "--show-error", "--socks5-hostname", "127.0.0.1:12334",
                "--connect-timeout", "20", "--max-time", "180", "-X", "POST",
                "-F", f"chat_id={chat_id}", "-F", f"parse_mode=HTML",
                "-F", "has_spoiler=false", "-F", f"caption=<{caption_path}",
                "-F", f"photo=@{photo}",
                f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendPhoto",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip() or f"curl exit {proc.returncode}")
        data = json.loads(proc.stdout)
        if not data.get("ok"):
            raise RuntimeError(data)
        return data["result"]
    finally:
        caption_path.unlink(missing_ok=True)


def main():
    env = read_active_env(Path.home() / ".hermes" / ".env")
    os.environ["TELEGRAM_BOT_TOKEN"] = env["TELEGRAM_BOT_TOKEN"]
    os.environ["TELEGRAM_CHAT_ID"] = env.get("TELEGRAM_CHAT_ID", "")
    caption = (ROOT / "channel_post.html").read_text(encoding="utf-8").strip()
    checks = {
        "em_dash": caption.count("\u2014"),
        "guillemets": caption.count("\u00ab") + caption.count("\u00bb"),
        "cjk": sum("\u4e00" <= c <= "\u9fff" for c in caption),
        "has_both_canonical_links": "Читать на Telegra.ph" in caption and "Полная версия с иллюстрациями" in caption,
    }
    if any(checks[k] for k in ("em_dash", "guillemets", "cjk")) or not checks["has_both_canonical_links"]:
        raise RuntimeError(f"Caption gate failed: {checks}")
    result = send_photo(CHANNEL_ID, ROOT / "cover-channel.jpg", caption)
    print(json.dumps({
        "message_id": result["message_id"],
        "chat_id": result["chat"]["id"],
        "chat_title": result["chat"]["title"],
        "photo_count": len(result.get("photo", [])),
        "checks": checks,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
