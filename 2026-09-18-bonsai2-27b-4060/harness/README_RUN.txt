# -*- coding: utf-8 -*-
"""Прогон 38 задач (gigachat-vs-free bench_tasks.json) против локального llama-server.

Перед запуском очистить VRAM (все модели LM Studio выгрузить):

    lms unload <model>   # pа каждую загруженную
    nvidia-smi --query-gpu=memory.used --format=csv,noheader   # ~900 MiB система

Старт сервера:

    llama-server.exe -m Ternary-Bonsai-2-27B-PTQ1_0.gguf \
      --port 8601 -ngl 99 -fa on -c 65536 \
      --temp 1.0 --top-p 0.95 --top-k 20 --jinja

Замер:
    python bench_local.py <out_name> [port]    # 38 задач, флеш после каждой
    python grade_local.py <out_name>           # чекер из сюиты gigachat-vs-free

Свободная переменная окружения:
    BENCH_MT=<tokens>   max_tokens (дефолт 3072, лимит для reasoning-модели)
"""
