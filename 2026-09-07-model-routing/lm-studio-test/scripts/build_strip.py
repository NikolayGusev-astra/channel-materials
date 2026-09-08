"""Сборка стрипа 2x3 из панелей jill_route + подписи."""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = r"C:\Work\Assist\comfyui\app\output"
DEST = r"C:\Work\Assist\channel-materials\2026-09-07-model-routing\jill-dispatcher-strip.png"

panels = [
    ("jill_route_01_00001_.png", "01 / Входящие задачи: очередь на трёх мониторах"),
    ("jill_route_02_00001_.png", "02 / Сортировка: quick, free, deep, architect"),
    ("jill_route_03_00001_.png", "03 / Шейкер делегации: субагентам по стакану"),
    ("jill_route_04_00001_.png", "04 / Подача результата клиенту"),
    ("jill_route_05_00001_.png", "05 / Табло смены: бюджет токенов спасён"),
    ("jill_route_06_00001_.png", "06 / Смена закрыта, собаки у ног"),
]

W, H = 896, 672
GAP = 12
CAPTION = 44
COLS, ROWS = 3, 2

cell_w = W
cell_h = H + CAPTION
strip_w = COLS * cell_w + (COLS + 1) * GAP
strip_h = ROWS * cell_h + (ROWS + 1) * GAP + 70  # 70 = заголовок

img = Image.new("RGB", (strip_w, strip_h), (16, 14, 24))
draw = ImageDraw.Draw(img)

font_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 34)
font_cap = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 20)
font_badge = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 16)

# Заголовок
title = "Джилл разрулила: локальный диспетчер за 2 ГБ"
tw = draw.textlength(title, font=font_title)
draw.text(((strip_w - tw) // 2, 18), title, fill=(220, 210, 255), font=font_title)

for idx, (fname, caption) in enumerate(panels):
    col, row = idx % COLS, idx // COLS
    x = GAP + col * (cell_w + GAP)
    y = 70 + GAP + row * (cell_h + GAP)
    # панель
    p = Image.open(os.path.join(OUT, fname)).resize((W, H))
    img.paste(p, (x, y))
    # рамка
    draw.rectangle([x - 2, y - 2, x + W + 1, y + H + 1], outline=(90, 70, 160), width=2)
    # плашка подписи
    draw.rectangle([x, y + H, x + W, y + H + CAPTION], fill=(28, 24, 44))
    draw.text((x + 10, y + H + 11), caption, fill=(200, 195, 220), font=font_cap)
    # бейдж номера
    draw.rectangle([x + W - 40, y + 8, x + W - 8, y + 34], fill=(120, 80, 220))
    draw.text((x + W - 33, y + 13), f"{idx+1:02d}", fill=(255, 255, 255), font=font_badge)

img.save(DEST, "PNG")
print("SAVED:", DEST, img.size)
