"""Шаг 1: выгрузка писем через IMAP (тема + домен + кусок тела).
Запуск: python 01_fetch_imap.py --folder INBOX --limit 10000 --out mails.json
Креды: env IMAP_HOST, IMAP_USER, IMAP_PASS (или app-password для Gmail).
"""
import imaplib, ssl, email, json, argparse, re, time
from email.header import decode_header

def decode_subj(raw):
    if not raw: return ""
    try:
        return str(make_header(decode_header(raw)))
    except Exception:
        return raw or ""

def clean_html(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", default="INBOX")
    ap.add_argument("--limit", type=int, default=10000)
    ap.add_argument("--out", default="mails.json")
    ap.add_argument("--body-chars", type=int, default=1500)
    args = ap.parse_args()

    import os
    host, user, pwd = os.environ["IMAP_HOST"], os.environ["IMAP_USER"], os.environ["IMAP_PASS"]
    ctx = ssl.create_default_context()
    M = imaplib.IMAP4_SSL(host, 993, ssl_context=ctx)
    M.login(user, pwd)
    typ, _ = M.select(args.folder, readonly=True)
    assert typ == "OK", "cannot open folder"

    typ, data = M.search(None, "ALL")
    ids = data[0].split()
    # равномерная выборка по всему ящику
    if len(ids) > args.limit:
        step = len(ids) / args.limit
        ids = [ids[int(i * step)] for i in range(args.limit)]
    print(f"fetching {len(ids)} of {data[0].count(b' ') + 1} messages")

    out, t0 = [], time.time()
    for n, mid in enumerate(ids, 1):
        typ, md = M.fetch(mid, "(RFC822)")
        if typ != "OK": continue
        msg = email.message_from_bytes(md[0][1])
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                if ct in ("text/plain", "text/html"):
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="replace")
                        if ct == "text/html": body = clean_html(body)
                        break
                    except Exception: pass
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
                if msg.get_content_type() == "text/html": body = clean_html(body)
        frm = msg.get("From") or ""
        dom_m = re.search(r"@([\w.-]+)", frm)
        out.append({
            "subject": decode_subj(msg.get("Subject")),
            "from_domain": dom_m.group(1).lower() if dom_m else "",
            "body_snippet": body[:args.body_chars],
        })
        if n % 100 == 0:
            json.dump(out, open(args.out + ".partial", "w", encoding="utf-8"), ensure_ascii=False)
            print(f"{n} fetched, {time.time()-t0:.0f}s", flush=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"DONE {len(out)} in {time.time()-t0:.0f}s -> {args.out}")
    M.logout()

if __name__ == "__main__":
    main()
