# Bonsai 2 27B: замер на RTX 4060 8 ГБ

38 задач из сюиты [2026-09-15-yandexgpt-gigachat-38-tasks](https://github.com/NikolayGusev-astra/channel-materials/tree/master/2026-09-15-yandexgpt-gigachat-38-tasks)
(та же методика, что в статье «38 задач, 8 русских моделей»), прогнанные локально
через PrismML llama.cpp fork.

## Модель

- `prism-ml/Ternary-Bonsai-2-27B-gguf`, файл `Ternary-Bonsai-2-27B-PTQ1_0.gguf` (5,95 ГБ)
- база Qwen3.8-27B, гибридное внимание (~75% линейного), 1.72 бита/вес
- Apache 2.0, llama.cpp форк PrismML обязателен (сток не открывает PTQ1_0/PQ2_0)

## Запуск

```
llama-server.exe -m Ternary-Bonsai-2-27B-PTQ1_0.gguf \
  --port 8601 -ngl 99 -fa on -c 65536 \
  --temp 1.0 --top-p 0.95 --top-k 20 --jinja
```

Семплер - thinking-mode из карточки модели. Дефолтный reasoning effort - xhigh.

## Прогон

```
python harness/bench_local.py <имя> 8601   # 38 задач, флеш после каждой
python harness/grade_local.py <имя>        # тот же чекер, что в сюите 38 задач
```

## Результаты (RTX 4060 8 ГБ, ноутбук-LDLC, 2026-09-18)

- декод 9,0 tok/s e2e среднее (10-11 короткие, 7,3-7,6 длинные генерации)
- prefill 43,8 tok/s (замер на 4096 токенов; полный prefill-бенч в статье)
- VRAM 7,68 ГБ из 8,19 (модель + KV 64к) - плотно, но полностью на GPU
- качество (грубый чекер): reasoning 87,5 / writing 75 / format 75 / factcheck 60
- xhigh-режим: 10 задач из 38 сожгли бюджет 3072 токенов на thinking, ответ не выдан

## Выводы

- Заявленные «98,2% интеллекта» - это про xhigh с полным бюджетом. На практике
  на 8 ГБ это медленный режим для батчей: реальная вилка xhigh vs medium
  замеряется в этой же папке (см. статью).
- 27B-модель целиком в 8 ГБ VRAM - главный результат: локально тянется
  Qwen3.8-класс с 64к контекстом.
