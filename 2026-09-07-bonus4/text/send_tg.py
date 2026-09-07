import json, os

import requests
from requests.adapters import HTTPAdapter, Retry

# --- token: env var first, then fallback to .env ---
tok = os.environ.get("TELEGRAM_BOT_TOKEN")
if not tok:
    env_path = os.path.expandvars(r'$LOCALAPPDATA\Local\hermes\.env')
    if os.path.exists(env_path):
        with open(env_path, encoding='utf-8') as f:
            for line in f:
                s = line.strip()
                if s.startswith('TELEGRAM_BOT_TOKEN='):
                    v = s.split('=', 1)[1].strip().strip('"').strip("'")
                    if v:
                        tok = v
                        break

if not tok:
    raise SystemExit('TELEGRAM_BOT_TOKEN is not set')

payload_path = os.path.expandvars(r'$LOCALAPPDATA\Temp\bonus4_tg_payload.json')
if not os.path.exists(payload_path):
    raise SystemExit(f'Payload not found: {payload_path}')

with open(payload_path, 'rb') as f:
    payload = f.read()

url = f'https://api.telegram.org/bot{tok}/sendMessage'

session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504, 429])
session.mount('https://', HTTPAdapter(max_retries=retries))

try:
    r = session.post(url, data=payload, headers={'Content-Type': 'application/json'}, timeout=30)
    print(r.text[:600])
    if not r.ok:
        print('HTTP', r.status_code, file=__import__('sys').stderr)
except requests.RequestException as e:
    print('STDERR:', str(e)[:200], file=__import__('sys').stderr)
