# -*- coding: utf-8 -*-
"""Фетч полного INBOX (44к писем) для NER-корпуса PII Guard.
Креды читает из Hermes .env сам; партиал каждые 500 писем.
Запуск: python corpus_fetch_all.py
Выход: corpus/mails.json (НЕ коммитить - ПДн корреспондентов).
"""
import os, io, ssl, sys, time

def load_env():
    env = {}
    for line in io.open(r'C:/Users/redacted/AppData/Local/hermes/.env', encoding='utf-8'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env

ENV = load_env()
os.environ['IMAP_HOST'] = ENV['EMAIL_IMAP_HOST']
os.environ['IMAP_USER'] = ENV['EMAIL_ADDRESS']
os.environ['IMAP_PASS'] = ENV['EMAIL_PASSWORD']

import imaplib, email, json, re, socket
from email.header import decode_header, make_header

imaplib._MAXLINE = 10_000_000

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mails.json')
PARTIAL = OUT + '.partial'
BODY_CHARS = 2000

def decode_subj(raw):
    if not raw:
        return ""
    try:
        return str(make_header(decode_header(raw)))
    except Exception:
        return str(raw)

def clean_html(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def main():
    host = os.environ['IMAP_HOST']; user = os.environ['IMAP_USER']; pwd = os.environ['IMAP_PASS']
    M = imaplib.IMAP4_SSL(host, 993, ssl_context=ssl.create_default_context())
    M.login(user, pwd)
    typ, data = M.select('INBOX', readonly=True)
    total = int(data[0].decode())
    print(f"INBOX total: {total}", flush=True)
    typ, ids_raw = M.search(None, 'ALL')
    ids = ids_raw[0].split()
    print(f"ids: {len(ids)}", flush=True)

    out, t0 = [], time.time()
    if os.path.exists(PARTIAL):
        out = json.load(io.open(PARTIAL, encoding='utf-8'))
        print(f"resume from partial: {len(out)}", flush=True)
    done = len(out)
    retries = 0
    for n, mid in enumerate(ids, 1):
        if n <= done:
            continue
        try:
            typ, md = M.fetch(mid, "(RFC822)")
            if typ != "OK":
                continue
            msg = email.message_from_bytes(md[0][1])
        except (imaplib.IMAP4.abort, imaplib.IMAP4.error, OSError, socket.timeout) as e:
            retries += 1
            print(f"[{n}] conn error ({e}), reconnect #{retries}", flush=True)
            if retries > 30:
                print("too many reconnects, saving and exiting", flush=True)
                break
            try: M.logout()
            except Exception: pass
            time.sleep(min(30, 5 * retries))
            M = imaplib.IMAP4_SSL(host, 993, ssl_context=ssl.create_default_context())
            M.login(user, pwd)
            M.select('INBOX', readonly=True)
            continue  # этот mid не сохранён - retry счётчик сработал, письмо доберём на след. обходе
        retries = 0
        try:
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ct = part.get_content_type()
                    if ct in ("text/plain", "text/html"):
                        try:
                            payload = part.get_payload(decode=True)
                            charset = part.get_content_charset() or "utf-8"
                            body = payload.decode(charset, errors="replace")
                            if ct == "text/html":
                                body = clean_html(body)
                            break
                        except Exception:
                            pass
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
                    if msg.get_content_type() == "text/html":
                        body = clean_html(body)
            frm = str(msg.get("From") or "")
            dom_m = re.search(r"@([\w.-]+)", frm)
            date = str(msg.get("Date") or "")
            out.append({
                "subject": decode_subj(msg.get("Subject")),
                "from_domain": dom_m.group(1).lower() if dom_m else "",
                "date": date,
                "body_snippet": body[:BODY_CHARS],
            })
        except Exception as e:
            print(f"[{n}] parse error: {e}", flush=True)
        if n % 500 == 0:
            json.dump(out, io.open(PARTIAL, 'w', encoding='utf-8'), ensure_ascii=False)
            rate = (n - done) / max(time.time() - t0, 1)
            print(f"{n}/{len(ids)} saved={len(out)} rate={rate:.1f}/s elapsed={time.time()-t0:.0f}s", flush=True)
    json.dump(out, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f"DONE {len(out)} in {time.time()-t0:.0f}s -> {OUT}", flush=True)
    M.logout()

if __name__ == "__main__":
    main()
