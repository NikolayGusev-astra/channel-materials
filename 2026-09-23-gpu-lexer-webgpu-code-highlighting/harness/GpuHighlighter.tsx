"use client";

import { useEffect, useRef } from "react";

const CLASS_BY_TYPE: Record<string, string> = {
  comment: "gl-comment",
  string: "gl-string",
  number: "gl-number",
  keyword: "gl-keyword",
  type: "gl-type",
  function: "gl-function",
  constant: "gl-constant",
  operator: "gl-operator",
};

type Span = { type: string; start: number; end: number };

/**
 * Клиентская подсветка кода через gpu-lexer (WebGPU, 27 KiB модель).
 * Находит <pre><code> внутри контейнера, прогоняет текст через parse()
 * и оборачивает спаны в цветные <span>. Fallback: без WebGPU код остаётся как есть.
 */
export function GpuHighlighter({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    const root = ref.current;
    if (!root) return;
    const blocks = Array.from(root.querySelectorAll("pre"));
    if (blocks.length === 0) return;

    (async () => {
      let parse: ((code: string) => Promise<Span[]>) | null = null;
      try {
        const mod = await import("gpu-lexer");
        parse = mod.parse;
      } catch {
        return; // WebGPU недоступен - код остаётся без подсветки
      }
      for (const pre of blocks) {
        if (cancelled) return;
        const code = pre.querySelector("code") ?? pre;
        const text = code.textContent ?? "";
        if (!text.trim()) continue;
        try {
          const spans = await parse(text);
          if (cancelled) return;
          const frag = document.createDocumentFragment();
          let pos = 0;
          for (const span of spans) {
            if (span.start > pos) {
              frag.appendChild(document.createTextNode(text.slice(pos, span.start)));
            }
            const cls = CLASS_BY_TYPE[span.type];
            const piece = text.slice(span.start, span.end);
            if (cls) {
              const el = document.createElement("span");
              el.className = cls;
              el.textContent = piece;
              frag.appendChild(el);
            } else {
              frag.appendChild(document.createTextNode(piece));
            }
            pos = span.end;
          }
          if (pos < text.length) {
            frag.appendChild(document.createTextNode(text.slice(pos)));
          }
          code.replaceChildren(frag);
          pre.dataset.gpuHighlighted = "1";
        } catch {
          // один блок не подсветился - остальные пробуем дальше
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div ref={ref}>
      {children}
    </div>
  );
}
