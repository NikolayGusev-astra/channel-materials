# -*- coding: utf-8 -*-
"""Прогон 38 задач (gigachat-vs-free bench_tasks.json) против локального llama-server.

Использование:
  python bench_local.py <out_name> [port]

v2 (после разведки):
- max_tokens=3072: Bonsai 2 в xhigh-режиме тратит >2000 токенов на thinking,
  при 2048 ответ обрезался до пустого (finish=length, весь бюджет съело рассуждение)
- 2 прохода по списку задач: сначала короткие (format/tokenize), потом тяжёлые,
  чтобы первые результаты ложились раньше
"""
import json, time, urllib.request, urllib.error, sys, os

D = r'C:\Work\bonsai2-test'
TASKS = r'C:\Work\Assist\gigachat-vs-free\bench_tasks.json'
OUT = os.path.join(D, 'results', sys.argv[1] + '.json')
PORT = sys.argv[2] if len(sys.argv) > 2 else '8601'
BASE = f'http://127.0.0.1:{PORT}/v1/chat/completions'
MODEL_ID = 'bonsai2-27b'
MT = int(os.environ.get('BENCH_MT', '3072'))

tasks = json.load(open(TASKS, encoding='utf-8'))['tasks']
# короткие сначала: format (T), tokenize (Z), потом factcheck, writing, reasoning
order = {'T': 0, 'Z': 1, 'F': 2, 'W': 3, 'R': 4}
tasks = sorted(tasks, key=lambda t: order.get(t['id'][0], 9))

rows = []
if os.path.exists(OUT):  # resume
    rows = json.load(open(OUT, encoding='utf-8'))
done = {r['tid'] for r in rows if r.get('ok')}
print(f'план: {len(tasks)} задач, уже готово: {len(done)}, max_tokens={MT}', flush=True)

def chat(prompt, max_tokens=MT):
    body = {'model': MODEL_ID,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': 1.0, 'top_p': 0.95, 'top_k': 20,
            }
    req = urllib.request.Request(BASE,
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json'}, method='POST')
    t0 = time.time()
    try:
        d = json.load(urllib.request.urlopen(req, timeout=1500))
    except urllib.error.HTTPError as e:
        return {'ok': False, 'error': f'HTTP {e.code}: ' + e.read().decode()[:200],
                'latency': round(time.time() - t0, 1)}
    except Exception as e:
        return {'ok': False, 'error': f'{type(e).__name__}: {str(e)[:200]}',
                'latency': round(time.time() - t0, 1)}
    dt = round(time.time() - t0, 1)
    ch = d['choices'][0]
    msg = ch.get('message') or {}
    u = d.get('usage') or {}
    c_tok = u.get('completion_tokens') or 0
    return {
        'content': (msg.get('content') or '').strip(),
        'reasoning': (msg.get('reasoning_content') or msg.get('reasoning') or '')[:4000],
        'p_tok': u.get('prompt_tokens'), 'c_tok': c_tok,
        'tps': round(c_tok / dt, 2) if dt > 0 and c_tok else None,
        'latency': dt, 'finish': ch.get('finish_reason'), 'ok': True,
    }

for tk in tasks:
    qid, cat, q = tk['id'], tk['cat'], tk['q']
    if qid in done:
        print(f'  {qid} skip (готово)', flush=True)
        continue
    r = chat(q)
    row = {'tid': qid, 'cat': cat, **r}
    rows.append(row)
    mark = 'ok' if r.get('ok') else 'FAIL'
    print(f"  {qid} {cat:<10} {mark} p={r.get('p_tok')} c={r.get('c_tok')} "
          f"tps={r.get('tps')} lat={r.get('latency')} fin={r.get('finish')}", flush=True)
    json.dump(rows, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

okr = [r for r in rows if r.get('ok')]
tps = [r['tps'] for r in okr if r.get('tps')]
if tps:
    print(f'\nDONE {len(okr)}/{len(tasks)} | ср.tok/s={sum(tps)/len(tps):.1f}', flush=True)
else:
    print(f'\nDONE {len(okr)}/{len(tasks)}', flush=True)
