import json, re, subprocess, os

env = open(r'C:\Users\n.gusev\AppData\Local\hermes\.env', encoding='utf-8').read()
tok = None
for line in env.splitlines():
    s = line.strip()
    if s.startswith('TELEGRAM_BOT_TOKEN='):
        v = s.split('=', 1)[1].strip().strip('"').strip("'")
        if v:
            tok = v

payload_path = os.path.expandvars(r'$LOCALAPPDATA\Temp\bonus4_tg_payload.json')
r = subprocess.run(['curl', '-s', '--max-time', '30', '-X', 'POST',
                    f'https://api.telegram.org/bot{tok}/sendMessage',
                    '-H', 'Content-Type: application/json',
                    '--data-binary', '@' + payload_path],
                   capture_output=True, text=True, encoding='utf-8')
print(r.stdout[:600])
if r.stderr:
    print('STDERR:', r.stderr[:200])
