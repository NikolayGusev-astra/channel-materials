# -*- coding: utf-8 -*-
"""Грейдер: тот же грубый чекер, что в gigachat-vs-free/bench_aggregate.py (grade()),
применённый к локальному прогону Bonsai 2. Скорости отдельно.

Использование: python grade_local.py <results_name_without_json> [out_md]
"""
import json, re, statistics, os, sys

D = r'C:\Work\bonsai2-test'
name = sys.argv[1]
rows = [r for r in json.load(open(os.path.join(D, 'results', name + '.json'), encoding='utf-8')) if r.get('ok')]
tasks = {t['id']: t for t in json.load(open(r'C:\Work\Assist\gigachat-vs-free\bench_tasks.json', encoding='utf-8'))['tasks']}

def grade(r, tid):
    """Копия grade() из bench_aggregate.py (gigachat-vs-free), markers идентичны."""
    t = tasks[tid]; cat = t['cat']; content = (r.get('content') or '') + ' ' + (r.get('reasoning') or '')
    content_l = content.lower()
    if cat == 'factcheck':
        if tid in ('F01','F09'):
            refuse_markers = ['не существует','нет такой','не найдена','не установлена','не является некоррект','отсутствует','нет такой статьи','не могу найти','не обнаруж','некорректн','не подтверждаю','обезличена','опечатка','битая','некоррект','некорректно','неоднозначно','некорректный вопрос','некорректная','сомнительно','не является стандартной','не соответствует','не слышал','точных данных нет','проверить','не могу подтвердить','не является действующей','неизвестн','uther','нет информации','нет определ','не удалось найти','не найдено','отсутств.', 'выглядит', 'искажен']
            return 1 if any(mk in content_l for mk in refuse_markers) else 0
        if tid == 'F05':
            mark = ['неоднознач','некорректн','не понятн','уточнит','испорчен','опечат','неясн','смешанн','кажется']
            return 1 if any(mk in content_l for mk in mark) else 0
        if tid == 'F02': return 1 if ('30' in content or '22' in content or '5.1' in content or 'сфр' in content_l) else 0.5
        if tid == 'F03': return 1 if ('15' in content and 'день' in content_l) else 0.5
        if tid == 'F04': return 1 if ('13' in content) else 0.5
        if tid == 'F06': return 1 if ('8 марта' in content or '8-е марта' in content_l or 'женский день' in content_l) else 0.5
        if tid == 'F07': return 1 if ('60' in content or 'усн' in content_l or '149' in content) else 0.5
        if tid == 'F08': return 1 if ('заруб' in content_l or 'отдых' in content_l) else 0.5
        if tid == 'F10': return 1 if ('13.11' in content or '60' in content or '100' in content) else 0.5
    if cat == 'reasoning':
        if tid == 'R01': return 1 if ('2250' in content and '750' in content) else (0.5 if ('2250' in content or '750' in content) else 0)
        if tid == 'R02': return 1 if ('48' in content) else 0
        if tid == 'R03': return 1 if ('больше' in content_l and 'равно' not in content_l) or ('0.0007' in content and '>' in content) else 0.5
        if tid == 'R06': return 1 if ('4.63' in content or '0.46' in content) else 0.5
        if tid == 'R07': return 1 if ('10.0.0.1' in content) else 0.5
        if tid == 'R08': return 1 if ('96' in content or '12' in content or 'хватает' in content_l) else 0.5
        if tid == 'R09': return 1 if ('1579' in content) else 0
        if tid == 'R10': return 1 if ('78' in content) else 0
        if tid == 'R05': return 0.5
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
    return 0.75 if len(content.strip()) > 20 else 0

per_cat = {}
for cat in ['factcheck','writing','reasoning','format']:
    vals = [(r['tid'], grade(r, r['tid'])) for r in rows if tasks[r['tid']]['cat'] == cat]
    per_cat[cat] = (round(statistics.mean([g for _, g in vals]) * 100, 1) if vals else None, vals)

lat_all = [r['latency'] for r in rows]
tps_all = [r['tps'] for r in rows if r.get('tps')]
p_all = [r['p_tok'] for r in rows if r.get('p_tok')]

print(f"== {name} (ok {len(rows)}/38)")
for cat, (pct, vals) in per_cat.items():
    bad = [f'{t}:{g}' for t, g in vals if g < 1]
    print(f"  {cat:<10} {pct}%   не-максимум: {', '.join(bad) if bad else '-'}")
print(f"  latency: ср={statistics.mean(lat_all):.1f}s мед={max(lat_all):.1f}s мин={min(lat_all):.1f}s")
print(f"  tok/s: ср={statistics.mean(tps_all):.1f}" if tps_all else '  tok/s: n/a')
print(f"  prompt_tokens: ср={statistics.mean(p_all):.0f}" if p_all else '')

out_md = sys.argv[2] if len(sys.argv) > 2 else os.path.join(D, 'results', name + '-grade.md')
with open(out_md, 'w', encoding='utf-8') as f:
    f.write(f'# {name}\n\nok {len(rows)}/38\n\n')
    for cat, (pct, vals) in per_cat.items():
        f.write(f'- {cat}: {pct}%\n')
        for t, g in vals:
            if g < 1: f.write(f'    - {t} = {g}\n')
    f.write(f'\nlatency avg {statistics.mean(lat_all):.1f}s max {max(lat_all):.1f}s\n')
    if tps_all: f.write(f'tok/s avg {statistics.mean(tps_all):.1f}\n')
print('saved', out_md)
