# Замер: SKILL.state vs ReAct vs compress+search на LFM2.5-8B-A1B (12.09.2026)

Материалы к статье «State на своей 4060: ReAct, SKILL.state и поиск на 8 ГБ» - часть 3 цикла про длинные сессии AI-агентов.
👉 https://telegra.ph/State-na-svoej-4060-ReAct-SKILLstate-i-poisk-na-8-GB-09-12

## Что здесь

Живой замер трёх механик длинных сессий на RTX 4060 8GB + две контрольные модели через openCode.

### Конфигурации 25-ходового бенча (bench_25turns.py)

| Конфигурация | Промпт (ход 1 → ход 25) | Recall | Средняя латентность |
|---|---|---|---|
| A. ReAct (полный транскрипт) | 194 → 3712 токенов (×19) | 1/3 сидов | 2.8 c |
| B. SKILL.state (state + патчи) | 330 → 371 токенов (флэт) | 0/3 сидов | 6.3 c |
| C. compress + session_search | 102 → 354 токенов (флэт) | 0/3 моделью, **3/3 через поиск** | 4.5 c |

Модель: LFM2.5-8B-A1B Q4_K_M (LM Studio, 128k контекст). 3 сида (301/302/303), 25 ходов.

### Needle-тест, lost-in-the-middle (needle_middle.py)

Факт в середине 30k-токенового журнала: **0 из 7** корректных ответов.
Факт в конце: стабильно HIT. Позиция определяет recall.

### Три независимых измерения needle-middle (4 сида)

| Ветка | Модель / механика | Контекст | Результат |
|---|---|---|---|
| 1 | LFM2.5-8B-A1B (голое внимание) | 128k | **0/7 HIT** |
| 2 | big-pickle (opencode zen, агент + Grep) | 200k | **4/4 HIT** |
| 3 | muse-spark-1.3 (Meta, агент + Read/Grep) | 1M | **4/4 HIT** |

Вывод: забывание середины - свойство малого stateless-декодера без инструментов, а не больших контекстов вообще.

## Файлы

- `bench_25turns.py` - бенч 25 ходов: ReAct vs SKILL.state (LM Studio API)
- `bench_hermes_sim.py` - конфигурация C: compress + session_search-симуляция
- `needle_middle.py` - needle-тест lost-in-the-middle (позиция факта)
- `gen_needle_files.py` - генератор фейковых журналов с секретами
- `muse_needle.sh` - прогон needle через opencode CLI (big-pickle / muse-spark-1.3)
- `needle_files/` - 4 сидa фейковых журналов (секреты: 6304A620/2203A900/5584A225/9442A988)
- `bench_results_25turns.jsonl` - сырые результаты бенча
- `needle_middle_results.jsonl` - сырые результаты needle-теста
- логи прогонов: bench_301/302/303.log, bench_hermes.log, muse_needle.log, muse_pickle_needle.log

## Воспроизведение

1. LM Studio: загрузить LFM2.5-8B-A1B Q4_K_M с контекстом 131072
2. `python bench_25turns.py 301 302 303` - бенч A/B
3. `python bench_hermes_sim.py 301 302 303` - конфигурация C
4. `python gen_needle_files.py && python needle_middle.py <seeds>` - needle-тест
5. Для веток 2/3: `bash muse_needle.sh` (нужен opencode CLI; muse - с прокси из РФ)

Модель в бенчах: `lfm2.5-8b-a1b` на http://127.0.0.1:1234 (OpenAI-совместимый API LM Studio).
