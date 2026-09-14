# -*- coding: utf-8 -*-
"""Агрегатор результатов bench: сравнение GigaChat vs opencode-go моделей.

Собирает 3 файла результатов, строит:
 1. Токен-экономику: prompt_tokens на идентичный русский текст (per-genre) + completion на коротких ответах
 2. Качество по категориям через checker'ы (factcheck = не выдумал ли, reasoning = число верное, format = соблюдение)
 3. Латенс-статистику
Выход: summary.md (для статьи) + summary.json
"""
import json, re, statistics, os

D = r'C:\Work\Assist\gigachat-vs-free'
OUT_MD = os.path.join(D, 'summary.md')
OUT_JSON = os.path.join(D, 'summary.json')

def load(name):
    p = os.path.join(D, 'results', name)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else []

giga = load('gigachat.json')
og = load('opencode-go.json')
og_c = load('opencode-go-catchup.json')
rows = og + og_c + giga
# дисперсия: opencode-go глупые дубли (модели с RegionError) не пере-пере-учитываем: ok rows только
ok_rows = [r for r in rows if r.get('ok')]
tasks = {t['id']: t for t in json.load(open(os.path.join(D,'bench_tasks.json'), encoding='utf-8'))['tasks']}

models = sorted({r['model'] for r in ok_rows})

# ---------------------------------------------------------------- токен-экономика
# только RF и opencode-go, идентичные промпты. p_tok на каждую задачу.
tok = {m: {} for m in models}
for r in ok_rows:
    tok[r['model']][r['tid']] = r.get('p_tok') or 0

ZA = ['Z01','Z02','Z03','Z04','Z05']  # variety задач для prompt_tokens
tokenize_rows = []
for tid in ZA:
    line = {'tid': tid}
    for m in models:
        line[m] = tok[m].get(tid)
    tokenize_rows.append(line)

# completion на exact коротких (T03, T05, R03, R09) - кто сколько токенов на один и тот же краткий ответ
exact_tids = ['T03','T05','R03','R09']
comp_rows = []
for tid in exact_tids:
    line = {'tid': tid}
    for m in models:
        # брать completion конкретного вызова
        r = [x for x in ok_rows if x['model']==m and x['tid']==tid]
        line[m] = r[0].get('c_tok') if r else None
    comp_rows.append(line)

# ---------------------------------------------------------------- качество
def grade(r, tid):
    """Грубый чекер по категории. Возвращает 1 (ok), 0.5 (partial), 0 (fail), None (неизвестно)."""
    t = tasks[tid]; cat = t['cat']; content = (r.get('content') or '') + ' ' + (r.get('reasoning') or '')
    content_l = content.lower()
    if cat == 'factcheck':
        # F01/F09 = ловушки (must not exist) — правильное поведение: отказ/ссылка на отсутствие
        if tid in ('F01','F09'):
            refuse_markers = ['не существует','нет такой','не найдена','не установлена','не является некоррект','отсутствует','нет такой статьи','не могу найти','не обнаруж','некорректн','не подтверждаю','обезличена','опечатка','битая','некоррект','некорректно','неоднозначно','некорректный вопрос','некорректная','сомнительно','не является стандартной','не соответствует','не слышал','точных данных нет','проверить','не могу подтвердить','не является действующей','неизвестн','uther','нет информации','нет определ','не удалось найти','не найдено','отсутств.', 'выглядит', 'искажен']
            return 1 if any(mk in content_l for mk in refuse_markers) else 0
        # F05 = искалеченный вопрос
        if tid == 'F05':
            mark = ['неоднознач','некорректн','не понятн','уточнит','испорчен','опечат','неясн','смешанн','кажется']
            return 1 if any(mk in content_l for mk in mark) else 0
        # F02/F06/F08(Have a factual check via ref)
        if tid == 'F02': return 1 if ('30' in content or '22' in content or '5.1' in content or 'сфр' in content_l or 'сфр' in content_l) else 0.5
        if tid == 'F03': return 1 if ('15' in content and 'день' in content_l) else 0.5
        if tid == 'F04': return 1 if ('13' in content) else 0.5
        if tid == 'F06': return 1 if ('8 марта' in content or '8-е марта' in content_l or 'женский день' in content_l) else 0.5
        if tid == 'F07': return 1 if ('60' in content or 'усн' in content_l or '149' in content) else 0.5
        if tid == 'F08': return 1 if ('заруб' in content_l or 'отдых' in content_l) else 0.5
        if tid == 'F10': return 1 if ('13.11' in content or '60' in content or '100' in content) else 0.5
    if cat == 'reasoning':
        refs = {'R03':' больше',' R09':'1579','R09':'1579'}
        if tid == 'R01': return 1 if ('2250' in content and '750' in content) else (0.5 if ('2250' in content or '750' in content) else 0)
        if tid == 'R02': return 1 if ('48' in content) else 0
        if tid == 'R03': return 1 if ('больше' in content_l and 'равно' not in content_l) or ('0.0007' in content and '>' in content) else 0.5
        if tid == 'R06': return 1 if ('4.63' in content or '0.46' in content) else 0.5
        if tid == 'R07': return 1 if ('10.0.0.1' in content) else 0.5
        if tid == 'R08': return 1 if ('96' in content or '12' in content or 'хватает' in content_l) else 0.5
        if tid == 'R09': return 1 if ('1579' in content) else 0
        if tid == 'R10': return 1 if ('78' in content) else 0
        if tid == 'R05': return 0.5  # сложная математика — partial по умолчанию без ручной проверки
    if cat == 'format':
        if tid == 'T01':
            m = re.search(r'"result"\s*:\s*(\d+)', content)
            return 1 if (m and m.group(1) == '303') else (0.5 if m else 0)
        if tid == 'T02':
            return 1 if (content.count('|') >= 8 and 'алла' in content_l and 'борис' in content_l) else 0.5
        if tid == 'T03': return 1 if ('python' in content_l and len(content_l.split()) <= 2) else 0.5
        if tid == 'T04':
            items = re.findall(r'^\s*[-*•]\s', content, re.M)
            return 1 if len(items) == 3 else 0.5
        if tid == 'T05': return 1 if (content.strip().lower().rstrip('. ') == 'logging') else 0.5
        if tid == 'T06': return 1 if ('число:' in content_l.lower() and 'км/с' in content_l) else 0.5
    # writing / tokenize — без автопроверки на качество, только непустой ответ
    return 0.75 if len(content.strip()) > 20 else 0

quality = {}
for m in models:
    per_cat = {}
    for cat in ['factcheck','writing','reasoning','format']:
        vals = []
        for r in ok_rows:
            if r['model'] == m and tasks[r['tid']]['cat'] == cat:
                g = grade(r, r['tid'])
                if g is not None:
                    vals.append(g)
        per_cat[cat] = round(statistics.mean(vals)*100, 1) if vals else None
    quality[m] = per_cat

# ---------------------------------------------------------------- латенс
lat = {m: {c: [] for c in ['factcheck','writing','reasoning','format','tokenize']} for m in models}
for r in ok_rows:
    cat = tasks[r['tid']]['cat']
    lat[r['model']].setdefault(cat, []).append(r.get('latency') or 0)
lat_avg = {m: {c: round(statistics.mean(v),1) if v else None for c,v in d.items() if c in ['factcheck','writing','reasoning','format']} for m,d in lat.items()}

# ---------------------------------------------------------------- output
summary = {'tokenize_prompt': tokenize_rows, 'exact_completion': comp_rows,
           'quality_pct': quality, 'latency_avg': lat_avg,
           'total_valid': len(ok_rows), 'per_model_count': {m: sum(1 for r in ok_rows if r['model']==m) for m in models}}
json.dump(summary, open(OUT_JSON,'w',encoding='utf-8'), ensure_ascii=False, indent=1)

# markdown
lines = ['# Сводка GigaChat vs opencode-go', '', f'Валидных прогонов: {len(ok_rows)} (из {len(rows)} попыток)', '']
lines += ['## 1. Токен-экономика: prompt_tokens на одинаковый русский текст', '',
          '| tid | ' + ' | '.join(models) + ' |', '|---|' + '---|'*len(models)]
for line in tokenize_rows:
    lines.append('| ' + line['tid'] + ' | ' + ' | '.join(str(line.get(m) or '-') for m in models) + ' |')
lines += ['', '## 2. Completion tokens на коротких точных ответах (T03/T05/R03/R09)', '',
          '| tid | ' + ' | '.join(models) + ' |', '|---|' + '---|'*len(models)]
for line in comp_rows:
    lines.append('| ' + line['tid'] + ' | ' + ' | '.join(str(line.get(m) or '-') for m in models) + ' |')
lines += ['', '## 3. Качество по категориям (грубый чекер, % от максимума)', '',
          '| модель | factcheck | writing | reasoning | format |', '|---|---|---|---|---|']
for m in models:
    q = quality[m]
    lines.append('| ' + m + ' | ' + ' | '.join(str(q.get(c) or '-') for c in ['factcheck','writing','reasoning','format']) + ' |')
lines += ['', '## 4. Средний латенс по категориям, сек', '', '| модель | factcheck | writing | reasoning | format |', '|---|---|---|---|---|']
for m in models:
    la = lat_avg[m]
    lines.append('| ' + m + ' | ' + ' | '.join(str(la.get(c) or '-') for c in ['factcheck','writing','reasoning','format']) + ' |')
open(OUT_MD,'w',encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines[:60]))
print('...')
print('summary.md / summary.json saved')
