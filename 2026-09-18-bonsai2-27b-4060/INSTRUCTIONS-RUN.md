# Bonsai 2 27B: запуск и подключение к Hermes Agent (Windows, RTX 4060 8 ГБ)

LM Studio Bonsai 2 из коробки НЕ поддерживает: модель в кастомном тернарном
формате PTQ1_0/PQ2_0 с Hadamard-поворотом весов. Стоковый рантайм либо
отклонит файл, либо (файлы Q2_0 старого Bonsai) загрузит молча и выдаст
мусор. Правильный путь: llama.cpp-форк PrismML, а Hermes подключать к нему
как к обычному OpenAI-совместимому API.

## 1. Скачать (один раз)

Бинарники (форк PrismML, сборка b10685 от 15.09.2026; в свежем b10687
выложили только cudart-DLL без самих бинарников, рабочий - предыдущий релиз):

- https://github.com/PrismML-Eng/llama.cpp/releases/download/prism-b10685-7dffb15/llama-prism-b10685-7dffb15-bin-win-cuda-12.4-x64.zip  (241 МБ)
- https://github.com/PrismML-Eng/llama.cpp/releases/download/prism-b10685-7dffb15/cudart-llama-bin-win-cuda-12.4-x64.zip  (373 МБ, CUDA DLL)

Модель (PTQ1_0 - быстрее на Ada-картах вроде 4060; PQ2_0 7,21 ГБ быстрее на H100/Blackwell):

- https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/resolve/main/Ternary-Bonsai-2-27B-PTQ1_0.gguf  (5,95 ГБ)

Распаковать оба архива В ОДНУ папку (cudart.zip даёт cublas64_12.dll,
cublasLt64_12.dll, cudart64_12.dll), например C:\Work\bonsai2\bin\
Модель положить в C:\Work\bonsai2\model\

## 2. Освободить VRAM

Перед запуском выгрузить все модели LM Studio, иначе 8 ГБ не хватит:

```
lms ls                # список загруженных
lms unload <имя>      # для каждой загруженной
nvidia-smi --query-gpu=memory.used --format=csv,noheader    # цель: ~900 MiB (система)
```

## 3. Запустить сервер

```
cd C:\Work\bonsai2\bin
llama-server.exe -m C:\Work\bonsai2\model\Ternary-Bonsai-2-27B-PTQ1_0.gguf ^
  --port 8601 -ngl 99 -fa on -c 65536 ^
  --temp 1.0 --top-p 0.95 --top-k 20 --jinja
```

Ключевые флаги:
- `-ngl 99`  - все слои на GPU
- `-fa on`   - fast attention (карточка PrismML рекомендует)
- `-c 65536` - окно контекста (максимум 262144; полное внимание только на 16 из
  64 слоёв - гибридная архитектура, KV растёт медленно, 128кл влезает в 8 ГБ)
- `--temp 1.0 --top-p 0.95 --top-k 20` - thinking-сэмплер из карточки модели
- `--jinja`  - чат-шаблон из GGUF (у модели свой шаблон с thinking-тегами)

Смок-тест: `curl http://127.0.0.1:8601/health` -> `{"status":"ok"}`,
затем любой запрос на /v1/chat/completions.

Семплинг по карточке модели:
- thinking-режим: temp=1.0, top_p=0.95, top_k=20, min_p=0, rep_pen=1.0
- instruct-режим: temp=0.7, top_p=0.80, top_k=20, min_p=0, presence_penalty=1.5

Полезные серверные флаги (длина рассуждений):

```
--reasoning-budget N      # лимит токенов на thinking: -1 (без лимита, дефолт),
                          # 0 (не думать), N>0 (бюджет)
--reasoning-budget-message "..."   # что вписать в ответ, если бюджет исчерпан
--reasoning-effort medium # minimal/low/medium/high/xhigh/max
                          # (low этой моделью не поддерживается - ведёт как xhigh)
```

Практичный фон/агентский сценарий: `--reasoning-effort medium` (PrismML:
короче, скорость/точность сбалансированы) или `--reasoning-budget 1024`.

## 4. Подключить в Hermes Agent

Обычная OpenAI-совместимая точка. В конфиге профиля
(`AppData\Local\hermes\profiles\<профиль>\config.yaml`) добавить provider:

```yaml
providers:
  - name: bonsai-local
    base_url: http://127.0.0.1:8601/v1
    api_key: none
    type: openai
    model: bonsai2-27b          # имя любое - сервер один, модель одна
    context_window: 65536       # как в -c на сервере
```

Перезапустить сессию Hermes, проверить простым «Привет». Модель возвращает
reasoning_content (думает по-английски, отвечает на языке вопроса) - это её
штатный режим.

### Ловушки (проверено на живом прогоне)

1. **Прокси-интерференция**: клиенты Hermes/Python гоняют даже localhost через
   системный прокси - curl работает, а python получает 502/connection-reset.
   Лечение: окружению процесса `http_proxy='' https_proxy='' no_proxy='*'`.
2. **Мегапромпты**: не передавать 100к+-токенные тексты как аргументы команд -
   Windows режет argv (WinError 206). Писать в файл и отправлять из файла.
3. **После перезапуска сервера** кэш префиксов пуст - первые запросы медленные,
   это норма.
4. **raries xhigh-режим**: жёсткий дефолт; без budget/effort сложные вопросы
   могут целиком уйти в thinking и не дать ответа (замер: 10 из 38 задач).

## 5. Настройки под сценарии

- Быстрый чат: `--reasoning-effort medium -c 32768` - примерно 2x скорость,
  качество чуть ниже.
- Максимальное качество (одиночные сложные вопросы): заводской xhigh, но
  max_tokens в запросе 4096+ либо `--reasoning-budget 2048` - иначе бюджет
  ответа съест рассуждение.
- Vision (картинки): добавить mmproj-файл:

```
llama-server.exe -m Ternary-Bonsai-2-27B-PTQ1_0.gguf ^
  --mmproj C:\Work\bonsai2\model\Ternary-Bonsai-2-27B-mmproj-Q8_0.gguf ^
  --port 8601 -ngl 99 -fa on -c 32768 --jinja
```

mmproj (0,63 ГБ) нужен только для картинок; для чистого текста можно не грузить.
