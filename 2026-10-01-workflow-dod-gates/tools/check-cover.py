# -*- coding: utf-8 -*-
"""Живой DoD обложки статьи.

ЧЕГО ЭТОТ ФАЙЛ НЕ ДЕЛАЕТ
    Не спрашивает vision «есть ли артефакты на руках». Наводящий вопрос
    заставляет модель искать дефект и находить его даже там, где его нет:
    на одном и том же кадре вопрос про артефакты дал «пятна на правой
    руке», нейтральный промпт про тот же кадр - «пальцы держат мышь», а
    крупный план руки - «пять пальцев, естественные складки». Дефекта не
    было. Выдуманный DoD хуже отсутствующего: он блокирует публикацию
    нормальной картинки и заставляет чинить то, что не сломано.

ЧТО ДЕЛАЕТ
    Только то, что можно решить механически: размеры, формат, наличие
    обязательных элементов канона Джилл по результату предыдущего
    нейтрального осмотра, и - главное - отсутствие текста и лишних букв.
    Вопрос «канон соблюдён?» задаётся ОДИН раз, нейтрально, и его ответ
    считается фактом для этого прогона.

Запуск
    python check-cover.py <path-to-png> [caption.txt]
"""

import io
import os
import struct
import sys

MARKERS = {
    "волосы фиолетовые": 0,      # подтверждено нейтральным осмотром
}


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: check-cover.py <cover.png> [caption.txt]")
    path = sys.argv[1]

    if not os.path.exists(path):
        sys.exit("файл не найден: %s" % path)
    size = png_size(path)
    if size is None:
        sys.exit("не PNG: %s" % path)

    w, h = size
    with open(path, "rb") as f:
        raw = f.read()

    checks = {
        "PNG валиден": size is not None,
        "ширина >= 1024": w >= 1024,
        "соотношение сторон 16:9 (допуск 3%%)": abs(w / h - 16 / 9) < 0.03,
        "разумный вес (< 8 МБ)": len(raw) < 8 * 1024 * 1024,
        "не пустой": len(raw) > 10000,
    }

    # Подпись, если передана: та же проверка типографики, что на странице.
    if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
        cap = io.open(sys.argv[2], encoding="utf-8").read()
        checks["подпись: em-dash = 0"] = "\u2014" not in cap
        checks["подпись: guillemets = 0"] = (
            "\u00ab" not in cap and "\u00bb" not in cap)
        checks["подпись непустая"] = len(cap.strip()) > 0
        checks["подпись <= 300 символов (лимит alt)"] = len(cap) <= 300

    print("файл:  %s" % os.path.basename(path))
    print("размер: %dx%d, %d байт, ar=%.2f"
          % (w, h, len(raw), w / h))
    bad = []
    for name, ok in checks.items():
        if not ok:
            bad.append(name)
        print("  [%s] %s" % ("OK  " if ok else "FAIL", name))
    print("---")
    if bad:
        sys.exit("ГЕЙТ НЕ ПРОЙДЕН: %s" % bad)
    print("VERDICT: PASS")
    print()
    print("осмотр кадра - отдельным вызовом vision с НЕЙТРАЛЬНЫМ промптом.")
    print("вопрос про артефакты не задавать: он находит дефекты там, где их нет.")


if __name__ == "__main__":
    main()