"""Догоняющий прогон для моделей, упавших на opencode-go:
- deepseek-flash (mnEE version v4-flash недоступна Regions China opt-in) — chat/completions
- grok-4.6 — через /responses (OpenAI Responses API), а не chat/completions
Результаты дописываются в opencode-go-catchup.json в том же формате rows.
"""
import json, os, urllib.request, urllib.error, time

BASE = 'https://opencode.ai/zen/go/v1'
OUT = r'C:\Work\Assist\gigachat-vs-free\results\opencode-go-catchup.json'
SESSION = 'giga-bench-catchup'

def get_key():
    for line in open(r'<hermes-env-file>', encoding='utf-8', errors='replace'):
        if line.startswith('OPENCODE_GO_API_KEY='):
            return line.split('=', 1)[1].strip().strip('"').strip("'")

KEY = get_key()
HDR = {'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json',
       'x-opencode-session': SESSION, 'User-Agent': 'opencode/1.18.30'}

def chat_cc(model, prompt, mt=700):
    t0 = time.time()
    body = {'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': mt}
    d = json.load(urllib.request.urlopen(urllib.request.Request(
        BASE + '/chat/completions', data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers=HDR, method='POST'), timeout=180))
    return _fmt(d, round(time.time() - t0, 1), ['choices'])

def chat_responses(model, prompt, mt=700):
    t0 = time.time()
    body = {'model': model, 'input': prompt, 'max_output_tokens': mt}
    d = json.load(urllib.request.urlopen(urllib.request.Request(
        BASE + '/responses', data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers=HDR, method='POST'), timeout=180))
    u = d.get('usage') or {}
    return {'ok': True, 'content': _txt(d), 'reasoning': '',
            'p_tok': u.get('input_tokens'), 'c_tok': u.get('output_tokens'), 'rt': u.get('output_tokens_details', {}).get('reasoning_tokens', 0),
            'latency': round(time.time() - t0, 1), 'finish': d.get('status'), 'cost': d.get('cost')}

def _txt(d):
    if d.get('output_text'): return d['output_text'].strip()
    txt = ''
    for o in d.get('output', []):
        if o.get('type') == 'message':
            txt += ''.join(c.get('text', '') for c in o.get('content', []))
    return txt.strip()

def _fmt(d, lat, _):
    ch = d['choices'][0]; msg = ch.get('message') or {}; u = d.get('usage') or {}
    return {'ok': True,
            'content': (msg.get('content') or '').strip(),
            'reasoning': (msg.get('reasoning_content') or msg.get('reasoning') or ''),
            'p_tok': u.get('prompt_tokens'), 'c_tok': u.get('completion_tokens'),
            'rt': (u.get('completion_tokens_details') or {}).get('reasoning_tokens', 0) if isinstance(u.get('completion_tokens_details'), dict) else 0,
            'latency': lat, 'finish': ch.get('finish_reason'), 'cost': d.get('cost')}

TASKS = json.load(open(r'C:\Work\Assist\gigachat-vs-free\bench_tasks.json', encoding='utf-8'))['tasks']
PLAN = [
    ('deepseek-flash', chat_cc),
    ('grok-4.6', chat_responses),
]

rows = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else []
done = {(r['model'], r['tid']) for r in rows if r.get('ok')}
for model, fn in PLAN:
    print(f'=== {model} ===', flush=True)
    n = 0
    for tk in TASKS:
        if (model, tk['id']) in done:
            continue
        try:
            r = fn(model, tk['q'])
        except Exception as e:
            r = {'ok': False, 'error': f'{type(e).__name__}: {str(e)[:150]}'}
        rows.append({'backend': 'opencode-go', 'model': model, 'tid': tk['id'], 'cat': tk['cat'], **r})
        print(f"  {tk['id']} {tk['cat']:<10} {'ok' if r.get('ok') else 'FAIL'} p={r.get('p_tok')} c={r.get('c_tok')} lat={r.get('latency')}", flush=True)
        n += 1
        time.sleep(1)
    json.dump(rows, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{model}: {n} rows')
print('DONE catchup', len(rows))
