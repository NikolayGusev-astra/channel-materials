#!/usr/bin/env python3
"""Индексация изображений из PDF через EmbeddingGemma 2 (local, llama-server).

Стадия "index images" для PDF->текст пайпа: достаёт картинки через pymupdf,
прогоняет через embedding-сервер, складывает векторы в JSON с привязкой к странице.

Зависимости: pip install pymupdf requests
Сервер: llama-server --embedding --mmproj mmproj.gguf --port 8935 -ub 4096 ...
"""
import base64, glob, json, os, re, sys, time

import pymupdf
import requests

EMBED_URL = os.environ.get("EG2_URL", "http://127.0.0.1:8935")
MIN_SIZE = 80  # отсекаем линии, буллеты, разделители


def extract_images(pdf_path: str, out_dir: str) -> list[dict]:
    """Достаёт картинки из PDF, возвращает метаданные с номером страницы."""
    os.makedirs(out_dir, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    out, n = [], 0
    for pno, page in enumerate(doc):
        for img in page.get_images(full=True):
            pix = pymupdf.Pixmap(doc, img[0])
            if pix.width < MIN_SIZE or pix.height < MIN_SIZE:
                continue
            if pix.n - pix.alpha > 3:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            fname = f"p{pno+1:03d}_{n:03d}.png"
            pix.save(os.path.join(out_dir, fname))
            out.append({"page": pno + 1, "file": fname})
            n += 1
    return out


def embed_image(path: str) -> list[float]:
    """Картинка -> вектор. ВАЖНО: media ходит через chat-формат content parts,
    прямой image_url в /v1/embeddings сервер не принимает."""
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    r = requests.post(f"{EMBED_URL}/v1/embeddings", json={
        "input": [{"role": "user", "content": [
            {"type": "text", "text": "task: search result | "},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]}],
        "model": "embeddinggemma-2",
    }, timeout=120)
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]


def embed_query(text: str) -> list[float]:
    r = requests.post(f"{EMBED_URL}/v1/embeddings", json={
        "input": [{"role": "user", "content": [
            {"type": "text", "text": "task: search result | query: " + text},
        ]}],
        "model": "embeddinggemma-2",
    }, timeout=60)
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]


def cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def main():
    if len(sys.argv) < 3:
        print("usage: index_pdf_images.py <doc.pdf> <out_dir> [query]")
        sys.exit(1)
    pdf, out_dir = sys.argv[1], sys.argv[2]
    index_file = os.path.join(out_dir, "index.json")

    if not os.path.exists(index_file):
        metas = extract_images(pdf, out_dir)
        index, t0 = [], time.time()
        for m in metas:
            emb = embed_image(os.path.join(out_dir, m["file"]))
            index.append({**m, "emb": emb})
            print(f"  p{m['page']:>3} {m['file']}")
        json.dump(index, open(index_file, "w"))
        print(f"indexed {len(index)} images in {time.time()-t0:.1f}s")

    if len(sys.argv) > 3:
        qv = embed_query(sys.argv[3])
        index = json.load(open(index_file))
        hits = sorted(index, key=lambda it: cos(qv, it["emb"]), reverse=True)[:5]
        for m in hits:
            print(f"  {cos(qv, m['emb']):.3f}  page {m['page']:>3}  {m['file']}")


if __name__ == "__main__":
    main()
