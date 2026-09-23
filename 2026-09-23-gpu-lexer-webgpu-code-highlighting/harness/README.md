# gpu-lexer харнесс: клиентская подсветка кода для hermes-agent.ru

Рабочий код из статьи. Подключение:

1. `npm install gpu-lexer`
2. Положить `GpuHighlighter.tsx` в компоненты, обернуть им рендер тела статьи.
3. `gpu-lexer-palette.css` - в глобальные стили.

Модель лениво грузится только на страницах с кодом. Без WebGPU - код остаётся без подсветки.

Проверено: Next.js 16 static export, Chrome 153 (WebGPU).
