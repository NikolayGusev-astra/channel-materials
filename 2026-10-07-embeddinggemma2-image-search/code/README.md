# Индексация изображений PDF через EmbeddingGemma 2

Код к статье о поиске по скриншотам документации: стадия "index images"
для стандартного PDF->текст RAG-пайпа.

## Запуск

1. Поднять embedding-сервер (нужен свежий llama.cpp с поддержкой EmbeddingGemma 2,
   в рантайме LM Studio 2.53.0 поддержка уже есть):

```bash
llama-server \
  -m embeddinggemma-2-Q8_0.gguf \
  --mmproj mmproj-Q8_0.gguf \
  --embedding --pooling mean --port 8935 -ngl 999 -c 16384 -ub 4096 -b 4096
```

Веса: unsloth/embeddinggemma-2-GGUF на HuggingFace (текст 0.31 ГБ Q8 + mmproj 0.55 ГБ).

2. Индексировать PDF и искать:

```bash
pip install pymupdf requests
python index_pdf_images.py doc.pdf ./img-index "мастер создания доверия"
```

## Подводные камни

- Картинки в /v1/embeddings передаются ТОЛЬКО через chat-формат content parts
  (см. embed_image), прямой image_url даёт 400.
- Task-префикс "task: search result |" обязателен: без него модель не отличает
  релевант от шума.
- -ub 4096 нужен для аудио; для картинок хватает дефолта.
- FP16 даёт NaN в эмбеддингах, использовать Q8/BF16.
