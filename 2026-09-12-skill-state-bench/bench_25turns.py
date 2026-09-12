#!/usr/bin/env python3
"""Бенч: ReAct vs SKILL.state на LFM2.5-8B-A1B, 25 ходов x 3 сида.
Сценарий: журнал обработки заявок; клиентский факт (secret code) появляется
на ходу ~3 и запрашивается на ходу 25. Сравнение точности и токенов.

Протокол чистоты (из skill_state_bench-STATE.md):
- обе конфигурации: temperature=0, max_tokens=512, system запрет рассуждений;
- контент needle одно и то же, сиды уникальны;
- LM Studio prefix-cache: между экспериментами сиды меняются; в пределах одного
  прогона повторов нет.
"""
import json, os, socket, random, time, sys

os.environ['http_proxy']=''; os.environ['https_proxy']=''; os.environ['no_proxy']='*'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bench_results_25turns.jsonl')
MODEL = 'lfm2.5-8b-a1b'
TEMP = 0.0
MAXTOK = 512
N_TURNS = 25
SEEDS = (301, 302, 303)
LOG_LINE = "Строка журнала {}: обработка заявки №{} завершена штатно, ошибок нет."

def http_post(payload, timeout=900):
    s = socket.create_connection(('127.0.0.1',1234), timeout=timeout)
    body = json.dumps(payload).encode('utf-8')
    req = (b"POST /v1/chat/completions HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n"
           b"Content-Length: "+str(len(body)).encode()+b"\r\nConnection: close\r\n\r\n")
    s.sendall(req+body)
    buf=b''; t0=time.time()
    try:
        while True:
            c=s.recv(65536)
            if not c: break
            buf+=c
    except socket.timeout: pass
    s.close(); dt=time.time()-t0
    raw = buf.split(b'\r\n\r\n',1)[-1]
    if b'\r\n' in raw[:25]:
        out=b''; rest=raw
        while True:
            try: sl,rest=rest.split(b'\r\n',1)
            except ValueError: break
            try: sz=int(sl,16)
            except Exception: break
            if sz==0: break
            out+=rest[:sz]; rest=rest[sz+2:]
        raw=out
    try: d=json.loads(raw.decode('utf-8','replace'))
    except Exception: return {'err':raw[:200].decode('utf-8','replace')}
    u=d.get('usage') or {}
    m=d['choices'][0]['message']
    return {'s':round(dt,1),'prompt':u.get('prompt_tokens'),'completion':u.get('completion_tokens'),
            'content':(m.get('content') or '').strip(),
            'reasoning':(m.get('reasoning_content') or ''),
            'finish':d['choices'][0].get('finish_reason')}

def build_log(seed, n_lines):
    random.seed(seed)
    secret = f"{random.randint(1000,9999)}A{random.randint(100,999)}"
    chunk = n_lines // 6  # ~4 turns between secrets
    secrets = []
    lines = []
    for turn in range(1, N_TURNS+1):
        batch = []
        for _ in range(chunk):
            lines.append(LOG_LINE.format(random.randint(0,10**6), random.randint(10000,99999)))
        s = f"{random.randint(1000,9999)}A{random.randint(100,999)}"
        secrets.append(s)
        lines.append(f"ВАЖНО: по заявке №{random.randint(10000,99999)} назначен контрольный код {s}.")
    return lines, secrets

SYS = "Ты оператор обработки заявок. Отвечай кратко, без рассуждений и без размышлений. Если вопрос о контрольном коде - назови ровно один код."

def react_run(seed):
    """Классический ReAct: полный транскрипт. Needle: контрольный код 1-го хода."""
    random.seed(seed)
    lines, secrets = build_log(seed, 40)   # пер-лог per turn ~20 lines
    target_secret = secrets[0]  # injected on turn 1
    messages = [{'role':'system','content':SYS}]
    per_turn = []
    for t in range(1, N_TURNS+1):
        batch = lines[(t-1)//4*4 : ((t-1)//4+1)*4 if t<=24 else len(lines)]
        # emit per-turn chunk of ~5 lines for context growth
        chunk = "\n".join(lines[(t-1)*4:(t)*4])
        q = f"Новый фрагмент журнала:\n{chunk}\n\nПродолжаем обработку."
        if t == N_TURNS:
            q += "\n\nКакой контрольный код был назначен в самом первом фрагменте журнала? Назови ровно код."
        messages.append({'role':'user','content':q})
        r = http_post({'model':MODEL,'temperature':TEMP,'max_tokens':MAXTOK,'messages':messages})
        if 'err' in r:
            per_turn.append({'turn':t,'err':True}); messages.append({'role':'assistant','content':''}); continue
        per_turn.append({'turn':t,'prompt':r['prompt'],'completion':r['completion'],
                         's':r['s'],'finish':r['finish'],
                         'hit': target_secret in (r['content']+" "+r['reasoning']) if N_TURNS==t else None,
                         'ans':r['content'][:40] if N_TURNS==t else ''})
        messages.append({'role':'assistant','content': (r['content'] or '(обработано)')[:60]})
    return {'mode':'react','seed':seed,'target':target_secret,'turns':per_turn}

def state_run(seed):
    """SKILL.state: фикс-схема стейта, только P+Sigma+O на ход. Needle: контрольный код 1-го фрагмента."""
    random.seed(seed)
    lines, secrets = build_log(seed, 100)
    target_secret = secrets[0]
    state = {"codes_seen": {}, "last_request_id": None, "notes": ""}
    per_turn = []
    schema_desc = ('Схема состояния: {"codes_seen": {заявка: код}, "last_request_id": str, "notes": str}. '
                   'Замечание: по каждой заявке с контрольным кодом добавляй запись в codes_seen.')
    for t in range(1, N_TURNS+1):
        chunk = "\n".join(lines[(t-1)*4:(t)*4])
        q = (f"{schema_desc}\n\nТЕКУЩЕЕ СОСТОЯНИЕ:\n{json.dumps(state, ensure_ascii=False)}\n\n"
             f"НОВОЕ НАБЛЮДЕНИЕ (фрагмент {t}):\n{chunk}\n\n"+"Определи, есть ли во фрагменте заявка с контрольным кодом. Если есть - назови заявку и код одной строкой; иначе ответь 'нет нового кода'.")
        r = http_post({'model':MODEL,'temperature':TEMP,'max_tokens':MAXTOK,
                       'messages':[{'role':'system','content':SYS},{'role':'user','content':q}]})
        if 'err' in r:
            per_turn.append({'turn':t,'err':r.get('err','')[:80]}); continue
        # deterministic state merge: find "№NNNNN ... код XXXX" pattern
        import re
        m = re.search(r'№(\d+).*?(\d{4}A\d{3})', r['content']+" "+r['reasoning'])
        m2 = re.search(r'№(\d+).*?(\d{4}A\d{3})', r['content'])
        matched = m2 or m
        if matched:
            state['codes_seen'][matched.group(1)] = matched.group(2)
            state['last_request_id'] = matched.group(1)
        per_turn.append({'turn':t,'prompt':r['prompt'],'completion':r['completion'],'s':r['s'],
                         'hit_turn1_code': (target_secret in ((m2.group(2) if m2 else ''))) if t==2 else None,
                         'ans_probe':(r['content'] or '')[:80],
                         'rc_has_secret': target_secret in r['reasoning'],
                         'n_codes_in_state': len(state['codes_seen'])})
    # final probe: state contains turn-1 code?
    reconstructed = json.dumps(state, ensure_ascii=False)
    probe_q = (f"{schema_desc}\n\nТЕКУЩЕЕ СОСТОЯНИЕ:\n{reconstructed}\n\n"
               "Какой контрольный код был назначен в САМОМ ПЕРВОМ фрагменте? Назови код одной строкой.")
    pr = http_post({'model':MODEL,'temperature':TEMP,'max_tokens':MAXTOK,
                    'messages':[{'role':'system','content':SYS},{'role':'user','content':probe_q}]})
    final_hit = target_secret in (pr['content']+" "+pr['reasoning']) if 'err' not in pr else None
    final_state_has = any(v==target_secret for v in state['codes_seen'].values())
    return {'mode':'state','seed':seed,'target':target_secret,
            'final_state_codes':state['codes_seen'],
            'probe_hit_state':final_state_has,'probe_hit_answer': (pr['content'][:60] if 'err' not in pr else None),
            'probe_hit': final_hit,
            'turns':per_turn}

if __name__ == '__main__':
    seeds = [int(x) for x in sys.argv[1:]] or list(SEEDS)
    with open(OUT, 'a', encoding='utf-8') as f:
        for seed in seeds:
            print(f"=== SEED {seed}: REACT ===")
            a = react_run(seed)
            f.write(json.dumps(a, ensure_ascii=False)+"\n"); f.flush()
            print("react tail:", json.dumps(a['turns'][-1], ensure_ascii=False))
            print(f"=== SEED {seed}: STATE ===")
            b = state_run(seed)
            f.write(json.dumps(b, ensure_ascii=False)); f.flush()
            print("state probe:", json.dumps({'probe_hit_answer':b['probe_hit_answer'],
                                              'probe_hit_state':b['probe_hit_state'],
                                              'n_codes':len(b['final_state_codes'])}, ensure_ascii=False))
    print("DONE")
