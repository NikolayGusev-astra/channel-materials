import json, time, os, socket, random, sys

os.environ['http_proxy']=''; os.environ['https_proxy']=''; os.environ['no_proxy']='*'

OUT = r"C:\Work\llm-wiki\wiki\content\статьи\_dossier-raw\needle_middle_results.jsonl"

def needle(n_tokens, position='middle', secret=None, seed=None):
    secret = secret or f"{random.randint(1000,9999)}A{random.randint(100,999)}"
    random.seed(seed)
    n_lines = int(n_tokens*3.6)//92
    half = (n_lines-1)//2 if position=='middle' else (n_lines-1 if position=='end' else 0)
    lines = []
    for i in range(half):
        lines.append(f"Строка журнала {random.randint(0,10**6)}: обработка заявки #{random.randint(10000,99999)} завершена штатно, ошибок нет.")
    lines.append(f"Важная заметка: код доступа {secret}.")
    for i in range(n_lines-1-half):
        lines.append(f"Строка журнала {random.randint(0,10**6)}: обработка заявки #{random.randint(10000,99999)} завершена штатно, ошибок нет.")
    body = "\n".join(lines) + "\n\nКакой код доступа указан в заметке? Ответь одной строкой кодом, без рассуждений."
    payload = json.dumps({'model':'lfm2.5-8b-a1b','temperature':0,'max_tokens':1500,
        'messages':[{'role':'user','content':body},
                    {'role':'assistant','content':''}]}).encode()
    # NOTE: assistant empty-turn not valid; use controlled reasoning suppression instead:
    payload = json.dumps({'model':'lfm2.5-8b-a1b','temperature':0,'max_tokens':1500,
        'messages':[{'role':'system','content':'Ты отвечаешь сразу, без размышлений. Только код.'},
                    {'role':'user','content':body+" (Без размышлений, сразу ответ: одна строка с кодом.)"}]}).encode()
    s = socket.create_connection(('127.0.0.1',1234), timeout=1200)
    req = (b"POST /v1/chat/completions HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n"
           b"Content-Length: "+str(len(payload)).encode()+b"\r\nConnection: close\r\n\r\n")
    s.sendall(req+payload)
    buf=b''; t0=time.time()
    try:
        while True:
            c=s.recv(65536)
            if not c: break
            buf+=c
    except socket.timeout: pass
    dt=time.time()-t0
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
    except Exception: return {'err':buf[:150].decode('utf-8','replace')}
    m=d['choices'][0]['message']
    ans=(m.get('content') or '').strip()
    rc=(m.get('reasoning_content') or '')
    return {'pos':position,'secret':secret,'seed':seed,'s':round(dt,1),
            'finish':d['choices'][0].get('finish_reason'),
            'raw_ans_len':len(ans),'rc_head':rc[:150],
            'hit_content': secret in ans, 'hit_any': secret in (ans+" "+rc),
            'ans':ans[:80]}

seeds = [int(x) for x in sys.argv[1:]] or [21,22]
print("seeds to run:", seeds)
with open(OUT, 'a', encoding='utf-8') as f:
    for seed in seeds:
        r = needle(30000,'middle',seed=seed)
        f.write(json.dumps(r, ensure_ascii=False)+"\n")
        f.flush()
        print(json.dumps(r, ensure_ascii=False))
