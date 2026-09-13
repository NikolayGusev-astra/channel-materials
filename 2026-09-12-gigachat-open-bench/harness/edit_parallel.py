# -*- coding: utf-8 -*-
"""Честный эксперимент: ОДНА сырая версия (git 2e7a72f) прогоняется через оба инструмента.
- Codex: gpt-5.6-terra, те же инструкции
- GigaChat-3-Ultra те же инструкции
Результаты -> edits/codex-edit-part-N-raw.md и edits/giga-edit-part-N-raw.md
Сырые статьи, до правок, с git-истории."""
import json, os, sys, time, subprocess, urllib.request, uuid, ssl, shutil, tempfile

TD = os.path.expandvars(r'%LOCALAPPDATA%\Temp')
D = r'C:\Work\Assist\gigachat-vs-free'
OUT = os.path.join(D, 'edits')
os.makedirs(OUT, exist_ok=True)

# сырые статьи на диск (уже сохранены в raw_articles/)
RAW1 = os.path.join(D, 'raw_articles', 'part-1-raw.md')
RAW2 = os.path.join(D, 'raw_articles', 'part-2-raw.md')

INSTR = """Вычитай и отредактируй статью. Стилевые правила (применять строго):
1. ЗАПРЕЩЕНО: em-dash (U+2014) — заменять на короткое тире с пробелами; кавычки-ёлочки («») — заменять на прямые двойные; англицизмы — русскими аналогами; английские вставки в теле русского поста.
2. НЕЛЬЗЯ резать текст при вычитке: исправлять только нарушения стиля (em-dash, ёлочки, CJK, опечатки, несогласованность). Не переписывать абзацы, не сокращать аргументы, не менять интонацию.
3. Русские термины: "токенизация" вместо "tokenization". Допустимы: токен, промпт, трансформер, MoE.
4. Не упоминать несуществующие инструменты. Не менять данные таблиц и замеров.
5. Проверка после правки: em-dash=0, guillemets=0.
6. Сохрани mutual-ссылки и ссылку на GitHub repo NikolayGusev-astra/channel-materials.
Выведи ПОЛНЫЙ исправленный текст статьи, ничего не сокращая, без вступлений и пояснений.
"""

# ------------------------------------------------- GigaChat
def giga_edit(part_file, out_file, model='GigaChat-3-Ultra'):
    ctx = ssl.create_default_context(cafile=os.path.join(TD, 'ru-ca-bundle.pem'))
    key = open(os.path.expanduser(r'~\secrets\gigachat-auth-key.txt')).read().strip()
    req = urllib.request.Request('https://ngw.devices.sberbank.ru:9443/api/v2/oauth',
        data=b'scope=GIGACHAT_API_PERS', method='POST',
        headers={'Content-Type':'application/x-www-form-urlencoded','Accept':'application/json',
                 'RqUID':str(uuid.uuid4()),'Authorization':'Basic '+key})
    tok = json.load(urllib.request.urlopen(req,timeout=60,context=ctx))['access_token']
    md = open(part_file, encoding='utf-8').read()
    prompt = INSTR + '\n\nСТАТЬЯ:\n\n' + md
    body = {'model':model,'messages':[{'role':'user','content':prompt}],'max_tokens':4000,'temperature':0.1}
    req2 = urllib.request.Request('https://api.giga.chat/v1/chat/completions',
        data=json.dumps(body,ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type':'application/json','Accept':'application/json',
                 'User-Agent':'hermes-edit/0.1','Authorization':'Bearer '+tok},method='POST')
    t0=time.time()
    d=json.load(urllib.request.urlopen(req2,timeout=240,context=ctx))
    u=d.get('usage') or {}
    lat=round(time.time()-t0,1)
    txt=d['choices'][0]['message']['content']
    open(out_file,'w',encoding='utf-8').write(txt)
    print(f'[giga] {os.path.basename(out_file)}: {u.get("prompt_tokens")}in/{u.get("completion_tokens")}out {lat}s')

# ------------------------------------------------- Codex
def codex_edit(part_file, out_file, workdir):
    prompt = INSTR.replace('Выведи ПОЛНЫЙ исправленный текст статьи, ничего не сокращая, без вступлений и пояснений.',
        f'Прочитай файл "{os.path.basename(part_file)}" в текущем каталоге. Отредактируй его СОГЛАСНО правилам выше и сохрани ИСПРАВЛЕННУЮ версию в файл "{os.path.basename(out_file)}". Не переписывай данные.')
    cmd = ['C:/Users/<user>/AppData/Roaming/npm/codex.cmd','exec','--dangerously-bypass-approvals-and-sandbox','-m','gpt-5.6-terra',prompt]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
        errors='replace', cwd=workdir, timeout=900)
    lat = round(time.time()-t0,1)
    # codex может писать вывод на консоль. Проверим файл.
    return lat, r.stdout[-800:] if r.stdout else r.stderr[-400:]

if __name__ == '__main__':
    side = sys.argv[1] if len(sys.argv) > 1 else 'both'
    if side in ('giga','both'):
        giga_edit(RAW1, os.path.join(OUT,'giga-edit-part-1-raw.md'))
        time.sleep(3)
        giga_edit(RAW2, os.path.join(OUT,'giga-edit-part-2-raw.md'))
    if side in ('codex','both'):
        wd = tempfile.mkdtemp(prefix='codex_edit_')
        # codex требует git repo, копируем сырые + git init
        shutil.copy(RAW1, os.path.join(wd,'part-1-raw.md'))
        shutil.copy(RAW2, os.path.join(wd,'part-2-raw.md'))
        subprocess.run(['git','init','-q'], cwd=wd, capture_output=True)
        subprocess.run(['git','add','-A'], cwd=wd, capture_output=True)
        subprocess.run(['git','commit','-qm','raw'], cwd=wd, capture_output=True)
        out1 = os.path.join(wd,'codex-part-1.md'); out2 = os.path.join(wd,'codex-part-2.md')
        lat1, log1 = codex_edit(os.path.join(wd,'part-1-raw.md'), out1, wd)
        print(f'[codex] part-1: {log1[:100]} {lat1}s')
        lat2, log2 = codex_edit(os.path.join(wd,'part-2-raw.md'), out2, wd)
        print(f'[codex] part-2: {log2[:100]} {lat2}s')
        # вытянуть файлы в OUT
        for src, dst in [(out1, os.path.join(OUT,'codex-edit-part-1-raw.md')),
                         (out2, os.path.join(OUT,'codex-edit-part-2-raw.md'))]:
            if os.path.exists(src):
                shutil.copy(src, dst)
                print('   saved:', dst)
            else:
                print('   MISSING:', src)
    print('DONE', side)
