---
site:
  slug: gpu-lexer-webgpu-code-highlighting
  tags: [webgpu, gpu-lexer, frontend, llm]
  cover: cover.png
---
# Подсветка кода за 27 килобайт: gpu-lexer учит браузер понимать любой язык

Сложность: средняя

Vercel выложил gpu-lexer - синтаксическую подсветку без грамматик: крошечная модель, обученная размечать код, работает в браузере через WebGPU. Вся модель - 41 321 вес по 6 бит, 27,64 КиБ в Brotli. Для сравнения: ядро prism.js - 58 КБ ещё без грамматик, а грамматика нужна отдельным файлом под каждый язык, и языка, которого в наборе нет, он не знает вовсе.

Как это устроено. CPU делает один механический проход: рубит исходник на простые части - слова, пробелы, переносы, символы - и снимает с каждой части языконезависимые признаки: тип, длину, краевые символы, хэши, пары соседних символов. Дальше работает GPU: признаки встраиваются в 32 обученных канала, аффинные сканы в обе стороны добавляют локальный контекст, а бинарное дерево с общими весами собирает блоки по 32 части снизу вверх, прокидывает контекст всего файла обратно вниз - и классификатор параллельно размечает каждую часть одним из девяти визуальных классов: plain, comment, string, number, keyword, type, function, constant, operator. Соседние одинаковые классы сливаются в итоговые спаны.

Слово "модель" здесь не маркетинг: обучение - PyTorch против разметки Shiki, чекпоинт 20260916T055435.785Z вышел с 83,02% agreement и 77,73% macro F1 на отложенной выборке, несвязанной с обучающей по репозиториям. Автор честно называет это экспериментом: agreement с Shiki - не объективная правильность, а на неоднозначном синтаксисе модель может уверенно ошибаться. Но девять визуальных классов - это не разбор AST, задача сильно проще компиляции, и её реально решить моделью в 27 килобайт.

Фишка - language-agnostic. Язык не передаётся, грамматики не выбираются. Модель угадывает тип каждой части из окружающего кода - в том числе на языках, которых не видела при обучении. Вот три примера из этой статьи: их подсвечивает не prism и не highlight.js, а та самая модель - прямо в твоём браузере, при загрузке страницы.

Python:

```python
def pull_model(name: str, quant: str = "int8") -> dict:
    """Тянуть модель с провайдера и вернуть её карточку."""
    resp = requests.get(f"https://api.example.com/v1/models/{name}",
                        params={"quantization": quant}, timeout=30)
    if resp.status_code == 404:
        raise ModelNotFound(f"{name}: нет в реестре")
    card = resp.json()
    return {"name": card["id"], "params_b": card["parameters"] / 1e9}
```

Rust:

```rust
fn find_hot_path(traces: &[Trace], threshold_ms: u64) -> Vec<&Trace> {
    let mut hot: Vec<&Trace> = traces
        .iter()
        .filter(|t| t.duration_ms > threshold_ms)
        .collect();
    hot.sort_by_key(|t| t.duration_ms);
    tracing::info!("hot traces: {}", hot.len());
    hot
}
```

SQL:

```sql
SELECT m.name, COUNT(l.id) AS requests, AVG(l.latency_ms) AS p50
FROM models m
JOIN call_log l ON l.model_id = m.id
WHERE l.created_at >= NOW() - INTERVAL '7 days'
GROUP BY m.name
HAVING COUNT(l.id) > 100
ORDER BY p50 DESC
LIMIT 10;
```

![Джилл с лупой и словарём разбирает чистый код без подсветки](/gpu-lexer-jill-before.png)

Внедрить у себя - тридцать строк. Пакет без зависимостей, публичный экспорт один:

```bash
npm install gpu-lexer
```

Компонент для React-сайта (у нас - Next.js со статическим экспортом): после гидрации находим все pre>code, прогоняем текст через parse() и оборачиваем спаны в цветные элементы. Если WebGPU нет - код остаётся как есть, деградации никакой:

```js
import { useEffect, useRef } from "react";

const CLASSES = {
  comment: "gl-comment", string: "gl-string", number: "gl-number",
  keyword: "gl-keyword", type: "gl-type", function: "gl-function",
  constant: "gl-constant", operator: "gl-operator",
};

export function GpuHighlighter({ children }) {
  const ref = useRef(null);
  useEffect(() => {
    let cancelled = false;
    const root = ref.current;
    const blocks = root?.querySelectorAll("pre") ?? [];
    (async () => {
      const { parse } = await import("gpu-lexer"); // лениво: 27 КиБ только там, где есть код
      for (const pre of blocks) {
        const code = pre.querySelector("code") ?? pre;
        const text = code.textContent ?? "";
        const spans = await parse(text);
        if (cancelled) return;
        const frag = document.createDocumentFragment();
        let pos = 0;
        for (const s of spans) {
          if (s.start > pos) frag.append(text.slice(pos, s.start));
          const cls = CLASSES[s.type];
          if (cls) {
            const el = document.createElement("span");
            el.className = cls;
            el.textContent = text.slice(s.start, s.end);
            frag.append(el);
          } else frag.append(text.slice(s.start, s.end));
          pos = s.end;
        }
        if (pos < text.length) frag.append(text.slice(pos));
        code.replaceChildren(frag);
      }
    })();
    return () => { cancelled = true; };
  }, []);
  return <div ref={ref}>{children}</div>;
}
```

И палитра к нему - девять классов, каждый на свой вкус:

```css
.gl-comment { color: #7c88a8; font-style: italic; }
.gl-string { color: #9ece8a; }
.gl-number { color: #e8a860; }
.gl-keyword { color: #6f9fff; }
.gl-type { color: #5fd0d0; }
.gl-function { color: #e0d080; }
.gl-constant { color: #d08ee0; }
.gl-operator { color: #a0b0d8; }
```

![Джилл через лупу рассматривает тот же код, подсвеченный моделью](/gpu-lexer-jill-after.png)

Ограничения названы прямо в README: это не парсер, не компилятор, не линтер и не security-инструмент. Смещения спанов - UTF-16 code units (как js-slice), нужен WebGPU и защищённый контекст; Firefox на Android пока мимо. На неоднозначном синтаксисе модель может уверенно ошибаться - но цена ошибки визуальная: не тот цвет, а не сломанный билд.

Что мне нравится в этом направлении: классическая задача, которую двадцать лет решали грамматиками и словарями ключевых слов, оказалась обучаемой ровно до размера "положить в чанк рядом с картинкой". Не "LLM заменяет инструменты" - а узкая модель под узкую задачу, дешевле грамматик и без зоопарка конфигов под каждый язык. Репозиторий: github.com/vercel-labs/gpu-lexer, демо с живым сравнением по языкам: gpu-lexer.vercel.app.
