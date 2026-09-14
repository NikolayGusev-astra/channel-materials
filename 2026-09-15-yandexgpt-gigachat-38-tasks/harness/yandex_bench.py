# -*- coding: utf-8 -*-
"""Бенч Яндекса: те же 38 задач, формат записи как в gigachat.json.
Модели: yandexgpt/rc (флагман 5.1) + yandexgpt-lite/latest.
Запуск: python yandex_bench.py <model_uri_suffix> <outfile>
"""
import json, os, sys, time, urllib.request, urllib.error

BASE = r'C:\Work\Assist\gigachat-vs-free'
FID = os.environ.get('YC_FOLDER_ID', '<your-folder-id>')
URL = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'

key = open(os.environ.get('YC_API_KEY_FILE', '<path-to-api-key-file>')).read().strip()

tasks = json.load(open(os.path.join(BASE, 'bench_tasks.json'), encoding='utf-8'))['tasks']

def call(model_uri, q, max_tokens=800, temp=0.1):
    body = {'modelUri': model_uri,
            'completionOptions': {'stream': False, 'temperature': temp, 'maxTokens': max_tokens},
            'messages': [{'role': 'user', 'text': q}]}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
        headers={'Authorization': f'Api-Key {key}', 'x-folder-id': FID, 'Content-Type': 'application/json'})
    t0 = time.time()
    try:
        d = json.load(urllib.request.urlopen(req, timeout=180))
        el = round(time.time() - t0, 2)
        r = d['result']
        u = r['usage']
        alt = r['alternatives'][0]
        return {'p_tok': int(u['inputTextTokens']), 'c_tok': int(u['completionTokens']),
                'latency': el, 'ok': alt['status'] == 'ALTERNATIVE_STATUS_FINAL',
                'content': alt['message']['text'], 'finish': alt['status'], 'err': None}
    except urllib.error.HTTPError as e:
        return {'p_tok': 0, 'c_tok': 0, 'latency': round(time.time()-t0,2), 'ok': False,
                'content': '', 'finish': 'ERROR', 'err': f'HTTP {e.code}: {e.read()[:150]}'}
    except Exception as e:
        return {'p_tok': 0, 'c_tok': 0, 'latency': round(time.time()-t0,2), 'ok': False,
                'content': '', 'finish': 'ERROR', 'err': str(e)[:150]}

def run(model_name, model_uri, outfile):
    rows = []
    t_start = time.time()
    for t in tasks:
        mt = 2000 if t['cat'] in ('factcheck','writing','reasoning') else 400
        r = call(model_uri, t['q'], max_tokens=mt)
        row = {'backend': 'yandex-api', 'model': model_name, 'tid': t['id'], 'cat': t['cat'],
               'checker': t.get('checker'), 'ref': t.get('ref'), 'note': t.get('note'), **r}
        rows.append(row)
        mark = 'ok' if r['ok'] else 'ERR'
        print(f"[{t['id']:4}] {mark:3} in={r['p_tok']:5} out={r['c_tok']:5} {r['latency']:6}s {r['err'] or ''}", flush=True)
        time.sleep(0.4)  # бережём квоту
    json.dump(rows, open(outfile, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ok = sum(1 for r in rows if r['ok'])
    print(f'== {model_name}: {ok}/{len(rows)} ok за {round(time.time()-t_start)}с -> {outfile}')

if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'both'
    if which in ('both', 'lite'):
        run('YandexGPT-5-Lite', f'gpt://{FID}/yandexgpt-lite/latest', os.path.join(BASE, 'results', 'yandex-lite.json'))
    if which in ('both', 'pro'):
        run('YandexGPT-5.1-Pro', f'gpt://{FID}/yandexgpt/rc', os.path.join(BASE, 'results', 'yandex-pro.json'))
