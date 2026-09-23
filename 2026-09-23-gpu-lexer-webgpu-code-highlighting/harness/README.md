# gpu-lexer: подсветка кода на сайте (харнесс из статьи)

Клиентская подсветка кода моделью gpu-lexer (27,64 КиБ, WebGPU) для Next.js-сайта
со статическим экспортом. Рабочий код, который стоит на hermes-agent.ru.

## Установка

1. Пакет:

```bash
npm install gpu-lexer
```

2. Скопировать `GpuHighlighter.tsx` в `src/components/` своего проекта.

3. Обернуть рендер тела статьи (или любого блока с кодом):

```tsx
import { GpuHighlighter } from "@/components/GpuHighlighter";

<GpuHighlighter>
  <MarkdownBody article={article} />
</GpuHighlighter>
```

4. Палитру из `gpu-lexer-palette.css` добавить в глобальные стили
   (или `import "./gpu-lexer-palette.css"` в layout).

## Как это работает

- `GpuHighlighter` - клиентский компонент (`"use client"`). После гидрации находит
  все `pre` внутри, текст каждого прогоняет через `parse()` из gpu-lexer и
  оборачивает типизированные спаны в цветные элементы.
- Модель грузится лениво (`await import("gpu-lexer")`) - 27 КиБ попадают в браузер
  только на страницах с кодом.
- Нет WebGPU (старый браузер, Firefox Mobile) - код остаётся без подсветки,
  ничего не ломается.
- Смещения спанов - UTF-16 code units, совпадают с JS-строками, обрезка безопасна.

## Ограничения (из README проекта)

Это не парсер и не линтер: 83% agreement с Shiki, на неоднозначном синтаксисе
модель может уверенно ошибаться. Цена ошибки - не тот цвет, а не сломанный билд.

Репозиторий: github.com/vercel-labs/gpu-lexer - демо: gpu-lexer.vercel.app
