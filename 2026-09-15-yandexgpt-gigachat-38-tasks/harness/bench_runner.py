"""Гибкий раннер bench: задачи из bench_tasks.json против двух бэкендов.

Бэкенды:
- gigachat (RF): OAuth через ngw.devices.sberbank.ru, OAuth scope GIGACHAT_API_PERS, CA-бандл РФ.
  Внимание: GigaChat-3-Pro не принимает temperature/max_tokens -> шлём минимальный body.
- opencode-go: base https://opencode.ai/zen/go/v1, нужен заголовок x-opencode-session (session affinity)
  и User-Agent. Кириллица через json.dumps с ensure_ascii=False в raw utf-8. Thinking-модели
  отдают content=None c reasoning_content в message. reasoning_tokens в usage.completion_tokens_details.

Честность замеров:
- токенизация измеряется только по prompt_tokens на ОДИН И ТОТ ЖЕ текст
- latency на каждый вызов своя
- 1 поток на GigaChat — всё строго последовательно
"""
import json, os, ssl, time, urllib.request, urllib.error, uuid, sys

TD = os.path.expandvars(r'%LOCALAPPDATA%\Temp')
OUT = r'C:\Work\Assist\gigachat-vs-free\results'
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- _gigachat
def _gigachat_ctx():
    return ssl.create_default_context(cafile=os.path.join(TD, 'ru-ca-bundle.pem'))

def gigachat_token():
    ctx = _gigachat_ctx()
    key = open(os.path.expanduser(r'~\secrets\gigachat-auth-key.txt')).read().strip()
    req = urllib.request.Request('https://ngw.devices.sberbank.ru:9443/api/v2/oauth',
        data=b'scope=GIGACHAT_API_PERS', method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json',
                 'RqUID': str(uuid.uuid4()), 'Authorization': 'Basic ' + key})
    d = json.load(urllib.request.urlopen(req, timeout=60, context=ctx))
    return d['access_token']

def gigachat_chat(model, prompt, token, max_tokens=None):
    body = {'model': model, 'messages': [{'role': 'user', 'content': prompt}]}
    if model != 'GigaChat-3-Pro':
        body['max_tokens'] = max_tokens or 512
        body['temperature'] = 0.0
    req = urllib.request.Request('https://api.giga.chat/v1/chat/completions',
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Accept': 'application/json',
                 'User-Agent': 'hermes-bench/0.1', 'Authorization': 'Bearer ' + token},
        method='POST')
    t0 = time.time()
    d = json.load(urllib.request.urlopen(req, timeout=180, context=_gigachat_ctx()))
    dt = round(time.time() - t0, 1)
    ch = d['choices'][0]
    msg = ch.get('message') or {}
    u = d.get('usage') or {}
    return {
        'content': (msg.get('content') or '').strip(),
        'reasoning': (msg.get('reasoning_content') or msg.get('reasoning') or ''),
        'p_tok': u.get('prompt_tokens'), 'c_tok': u.get('completion_tokens'),
        'rt': (u.get('completion_tokens_details') or {}).get('reasoning_tokens', 0) if isinstance(u.get('completion_tokens_details'), dict) else 0,
        'latency': dt, 'finish': ch.get('finish_reason'), 'ok': True,
    }

# ---------------------------------------------------------------- _opencode-go
def go_chat(model, prompt, mt=700, session='giga-bench-1'):
    base = 'https://opencode.ai/zen/go/v1'
    key = None
    for line in open(r'<hermes-env-file>', encoding='utf-8', errors='replace'):
        if line.startswith('OPENCODE_GO_API_KEY='):
            key = line.split('=', 1)[1].strip().strip('"').strip("'")
    headers = {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json',
               'x-opencode-session': session, 'User-Agent': 'opencode/1.18.30'}
    body = {'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': mt}
    if model.startswith(('nemotron', 'step', 'ling')):  # thinking-модели: не ограничиваем жёстко
        body['max_tokens'] = max(mt, 2000)
    req = urllib.request.Request(base + '/chat/completions',
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers=headers, method='POST')
    t0 = time.time()
    try:
        d = json.load(urllib.request.urlopen(req, timeout=180))
    except urllib.error.HTTPError as e:
        return {'ok': False, 'error': f'HTTP {e.code}: ' + e.read().decode()[:160], 'latency': round(time.time() - t0, 1)}
    ch = d['choices'][0]
    msg = ch.get('message') or {}
    u = d.get('usage') or {}
    return {
        'content': (msg.get('content') or '').strip(),
        'reasoning': (msg.get('reasoning_content') or msg.get('reasoning') or ''),
        'p_tok': u.get('prompt_tokens'), 'c_tok': u.get('completion_tokens'),
        'rt': (u.get('completion_tokens_details') or {}).get('reasoning_tokens', 0) if isinstance(u.get('completion_tokens_details'), dict) else 0,
        'latency': round(time.time() - t0, 1), 'finish': ch.get('finish_reason'), 'ok': True,
        'cost': d.get('cost'),
    }

# ---------------------------------------------------------------- run one backend
MODELS = {
    'gigachat': [
        # (model_id, prompt_cap_max_tokens[GigaChat-3-Pro игнорируется], замер от RF API)
        'GigaChat-2', 'GigaChat-2-Max', 'GigaChat-2-Pro',
        'GigaChat-3-Lightning', 'GigaChat-3-Pro', 'GigaChat-3-Ultra',
    ],
    'opencode-go': [
        'glm-5.3-flash', 'glm-5.3', 'deepseek-v4-flash', 'deepseek-v4.1-flash',
        'qwen3.8-flash', 'qwen3.8-max', 'kimi-k3', 'deepseek-v4-pro', 'grok-4.6',
    ],
}

def run(backend, models, tasks, out_json):
    if backend == 'gigachat':
        token = gigachat_token()
        print('GigaChat token OK, expires', bool(token))
    else:
        token = None
    rows = []
    for mi, model in enumerate(models, 1):
        print(f'\n[{mi}/{len(models)}] === {model} ===', flush=True)
        for tk in tasks:
            qid, cat, q = tk['id'], tk['cat'], tk['q']
            try:
                if backend == 'gigachat':
                    r = gigachat_chat(model, q, token)
                else:
                    r = go_chat(model, q)
            except Exception as e:
                r = {'ok': False, 'error': f'{type(e).__name__}: {str(e)[:150]}'}
            row = {'backend': backend, 'model': model, 'tid': qid, 'cat': cat, **r}
            rows.append(row)
            mark = 'ok' if r.get('ok') else 'FAIL'
            print(f"  {qid} {cat:<10} {mark} p={r.get('p_tok')} c={r.get('c_tok')} rt={r.get('rt')} lat={r.get('latency')}", flush=True)
            if backend == 'gigachat':
                time.sleep(1.5)
        # flush после каждой модели
        json.dump(rows, open(out_json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\nDONE', backend, len(rows), 'rows')
    # баланс после (gigachat)
    if backend == 'gigachat':
        tok = gigachat_token()
        req = urllib.request.Request('https://api.giga.chat/v1/balance',
            headers={'Accept': 'application/json', 'User-Agent': 'hermes-bench/0.1', 'Authorization': 'Bearer ' + tok})
        print('balance:', urllib.request.urlopen(req, timeout=30, context=_gigachat_ctx()).read().decode()[:400])

if __name__ == '__main__':
    which = sys.argv[1]
    tasks = json.load(open(r'C:\Work\Assist\gigachat-vs-free\bench_tasks.json', encoding='utf-8'))['tasks']
    out = rf'C:\Work\Assist\gigachat-vs-free\results\{which}.json'
    run(which, MODELS[which], tasks, out)

