# Проверенные сниппеты пайплайнов (все запускались в этой сессии)

## Общая обвязка: LLM через LM Studio (локально, без прокси!)

```python
import json, urllib.request

# ВАЖНО: пустой ProxyHandler - иначе корпоративный прокси перехватит localhost и вернёт 502
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def llm(messages, max_tokens=700):
    req = urllib.request.Request(
        "http://127.0.0.1:1234/v1/chat/completions",
        data=json.dumps({
            "model": "yandexgpt-5-lite-8b-instruct",
            "messages": messages,
            "temperature": 0.3,   # рекомендация Яндекса: 0.3 / top_p 0.9
            "max_tokens": max_tokens,
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    with opener.open(req, timeout=240) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"]["content"], d["usage"]
```

## Пайплайн 1: RAG-ответчик

```python
def rag_answer(query, chunks):
    # chunks - результат ретрива (векторный поиск по базе знаний)
    context = "\n\n".join(
        f"### Источник {i+1}\n{c}" for i, c in enumerate(chunks)
    )
    messages = [
        {"role": "system", "content":
         "Ты отвечаешь на вопросы по документации, используя ТОЛЬКО "
         "приведённый контекст. Указывай номера источников. Если ответа "
         "в контексте нет - скажи об этом прямо."},
        {"role": "user", "content": f"Контекст:\n{context}\n\nВопрос: {query}"},
    ]
    answer, usage = llm(messages)
    return answer, usage
```

Пример реального ответа (вопрос про переустановку реплики ALD Pro):

```
Чтобы переустановить некорректно настроенную реплику, выполните:
1. Удалите реплику и выйдите из домена (astra-freeipa-server -U, astra-freeipa-client -U).
2. Удалите пакеты: sudo apt purge 'aldpro*' 'freeipa*' 'sssd*' ...
3. Проверьте список профилей в домашнем каталоге.
4. Повторно введите реплику в домен.
Источник: [1]
```

Пример честного отказа (спросили порт LDAP, которого в контексте не было):

```
В приведённом контексте нет ответа на вопрос о том, какой порт
использует LDAP.
```

## Пайплайн 2: ответчик над поисковой выдачей (мини-Perplexity)

```python
from hermes_tools import web_search, web_extract

def search_answer(question):
    # шаг 1: поиск
    hits = web_search(question, limit=4)["data"]["web"]
    # шаг 2: вытянуть текст топ-2 страниц
    pages = web_extract([h["url"] for h in hits[:2]], char_limit=2500)
    # шаг 3: контекст с номерами источников
    parts = [
        f"[{i}] {p.get('title','')}\n{(p.get('content') or '')[:2200]}"
        for i, p in enumerate(pages["results"], 1)
    ]
    messages = [
        {"role": "system", "content":
         "Ты отвечаешь на вопрос по приведённым материалам. Указывай "
         "номера источников в квадратных скобках. Если данных "
         "недостаточно - так и скажи."},
        {"role": "user", "content":
         "Материалы:\n" + "\n\n".join(parts) + f"\n\nВопрос: {question}"},
    ]
    return llm(messages)
```

Реальный пример: "как включить отладку регулярных выражений в Python"

```
Чтобы включить отладку регулярных выражений в Python, нужно
использовать флаг `re.DEBUG` в методе `re.compile` [1].
```

722 prompt-токена, 1.2 секунды генерации.

## Питфолл: нерелевантная выдача

Если поиск вернул похожую, но не ту статью (искали фичи Python 3.14,
нашли статью про старые фичи Python), модель не притянется за уши:

```
В предоставленных материалах нет информации о ключевых
особенностях Python версии 3.14 [1][2].
```

Это правильно: генератор не должен "додумывать" поверх шумной выдачи.
Ответственность за релевантность retrieval - на этапе поиска, не генерации.

## Питфолл: противоречивые источники

Два источника с разными датами релиза - модель выстроила хронологию
и показала оба:

```
Версия X.Y была запланирована к выходу на 15 марта 2027 года,
однако позже выход был перенесён на апрель 2027 года из-за
проблем с сертификацией [1], [2].
```

## Железо и производительность

- Модель: YandexGPT-5-Lite-8B-instruct, Q4_K_M GGUF, 4.6 GB
- Влезает целиком в 8 GB VRAM (RTX 4060)
- Скорость: ~29 токенов/сек
- Контекст: 32k токенов (топ-10 чанков свободно)
- RAG-ответ на 193 prompt-токенах: 6.5 сек
- Загрузка через LM Studio: скачать GGUF, положить в папку моделей, выбрать в UI

## Ссылки

- Модель: https://huggingface.co/yandex/YandexGPT-5-Lite-8B-instruct
- GGUF: https://huggingface.co/yandex/YandexGPT-5-Lite-8B-instruct-GGUF
- LM Studio: https://lmstudio.ai
