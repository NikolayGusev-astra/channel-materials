#!/usr/bin/env python3
"""Эксперимент C: механика Hermes на LFM2.5-8B-A1B (та же модель LM Studio).

Симуляция Hermes-механики (bounded memory + autho-compress + session_search):
- ход = обычный accumulating transcript (ReAct-стиль),
- но при превышении бюджета контекста срабатывает compress: старые ходы заменяются
  summary (защищены последние protect_last_n=4 хода, как protect_last_n=20 масштабно меньше),
- "session_search" по архиву: точный substring-поиск по исходным строкам архива
  (в Hermes это FTS5; для честного замера ищем точный секрет, не семантику).

Итоговая точка: A (ReAct, без compress) C (ReAct+compress+search) B (state-runtime).
Каждая - 25 ходов x 3 сида.
"""
import json, os, socket, random, time, sys

os.environ['http_proxy']=''; os.environ['https_proxy']=''; os.environ['no_proxy']='*'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bench_results_25turns.jsonl')
MODEL='lfm2.5-8b-a1b'; TEMP=0.0; MAXTOK=512; N_TURNS=25
PROTECT_LAST = 4      # в Hermes реальные 20 ходов; здесь 4 хода из 25 (~same share) - как 20/120
COMPRESS_BUDGET_CHAR = 400  # максимум знаков в выпуске summary
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

SYS = "Ты оператор обработки заявок. Отвечай кратко, без рассуждений и без размышлений. Если вопрос о контрольном коде - назови ровно один код."

def build_log(seed):
    random.seed(seed)
    secrets = []
    for _ in range(N_TURNS):
        secrets.append(f"{random.randint(1000,9999)}A{random.randint(100,999)}")
    return secrets

def hermes_run(seed):
    """C: accumulating transcript, авто-compress через бюджет, величины как в Hermes."""
    secrets = build_log(seed)
    transcript = []  # [[role, content]]
    summary = ""      # накопленный summary скомпакченной истории
    archive_texts = []  # строки, ушедшие в архив (для session_search-симуляции)
    per_turn = []
    tot_tokens = 0
    for t in range(1, N_TURNS+1):
        chunk = f"Новый фрагмент журнала (ход {t}): фоновые заявки обработаны штатно. По заявке №{random.randint(10000,99999)} назначен контрольный код {secrets[t-1]}."
        q = chunk if t < N_TURNS else (chunk + "\n\nКакой контрольный код был назначен на ХОДЕ 1? Назови ровно один код.")
        user_msg = q
        # assemble context: summary +protect transcript tail
        ctx = ([{'role':'system','content':SYS}]
               + ([{'role':'system','content':'РЕЗЮМЕ РАННЕЙ ИСТОРИИ:\n'+summary}] if summary else [])
               + [{'role':'user' if i%2==0 else 'assistant','content':c} for i,(role,c) in enumerate(transcript[-2*PROTECT_LAST:])])
        ctx.append({'role':'user','content':q})
        r = http_post({'model':MODEL,'temperature':TEMP,'max_tokens':MAXTOK,'messages':ctx})
        if 'err' in r:
            per_turn.append({'turn':t,'err':r['err'][:80]}); transcript.append(['user',q]); transcript.append(['assistant','(ошибка)']); continue
        hit = secrets[0] in (r['content']+" "+r['reasoning']) if t==N_TURNS else None
        per_turn.append({'turn':t,'prompt':r['prompt'],'completion':r['completion'],'s':r['s'],'finish':r['finish'],
                         'hit': hit if t==N_TURNS else None})
        transcript.append(['user', q]); transcript.append(['assistant', (r['content'] or '(обработано)')[:60]])
        archive_texts.append(q)
        # auto-compress when transcript too long (simulate Hermes criterion: char budget)
        if sum(len(c) for _,c in transcript) > 6000:
            # summarize everything except protect tail
            keep = transcript[-2*PROTECT_LAST:]
            older = transcript[:-2*PROTECT_LAST]
            older_text = "\n".join(c for _,c in older)
            # Hermes-style summary via the model itself (cheap: cap 120 chars + keep key facts)
            sr = http_post({'model':MODEL,'temperature':TEMP,'max_tokens':160,
                'messages':[{'role':'system','content':'Сжимай историю в 2-3 предложения. Сохраняй упомянутые контрольные коды и номера заявок дословно.'},
                            {'role':'user','content':("ТЕКУЩИЙ SUMMARY:\n"+summary+"\n\nДОБАВИТЬ:\n"+older_text+"\n\nНовый summary:")}]})
            if 'err' not in sr:
                summary = (sr['content'] or summary)[:COMPRESS_BUDGET_CHAR]
                # side-effect: archiving means old texts remain searchable via session_search:
                archive_texts.extend(c for _,c in older)
            transcript = keep
    # session_search probe: exact substring search over archive (simulating FTS5)
    search_hit = any(secrets[0] in txt for txt in archive_texts)
    return {'mode':'hermes_sim','seed':seed,'target':secrets[0],
            'final_summary':summary[:200],
            'search_hit':search_hit,
            'turns':per_turn}

if __name__=='__main__':
    seeds=[int(x) for x in sys.argv[1:]] or [301,302,303]
    with open(OUT,'a',encoding='utf-8') as f:
        for seed in seeds:
            print(f"=== SEED {seed}: HERMES_SIM ===")
            c = hermes_run(seed)
            f.write(json.dumps(c, ensure_ascii=False)+"\n"); f.flush()
            print(json.dumps({'mode':c['mode'],'seed':seed,'search_hit':c['search_hit'],
                              'probe_answer': (c['turns'][-1].get('ans') if c['turns'] else None),
                              'final_turn': json.dumps(c['turns'][-1], ensure_ascii=False)[:160] if c['turns'] else None}, ensure_ascii=False))
    print("C DONE")
