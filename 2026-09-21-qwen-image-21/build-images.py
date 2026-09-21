"""Build article illustrations: checker bg for RGBA, before/after strip for edit."""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = r"C:/Work/Assist/channel-materials/2026-09-21-qwen-image-21/images"
SRC = r"C:/Work/Assist/comfyui/app/output/qwen21"
RES = r"C:/Work/Assist/comfyui/qwen-image-2.1/results"
os.makedirs(OUT, exist_ok=True)
FONT = r"C:/Windows/Fonts/segoeuib.ttf"

# 1. RGBA dragon on checkerboard
img = Image.open(f"{SRC}/rgba_dragon_test_00001_.png").convert("RGBA")
W, H = img.size
cell = 64
checker = Image.new("RGB", (W, H), (255, 255, 255))
d = ImageDraw.Draw(checker)
for y in range(0, H, cell):
    for x in range(0, W, cell):
        if (x // cell + y // cell) % 2 == 0:
            d.rectangle([x, y, x + cell, y + cell], fill=(210, 210, 210))
checker.paste(img, (0, 0), img)
checker.save(f"{OUT}/rgba-dragon-checker.png")
print("checker ok")

# 2. Edit before/after strip
before = Image.open(r"C:/Work/Assist/comfyui/qwen-image-2.1/edit_input.png").convert("RGB")
after = Image.open(f"{SRC}/edit_beach_test_00001_.png").convert("RGB")
target_w = 900
def scale(im, w):
    h = round(im.height * w / im.width)
    return im.resize((w, h), Image.LANCZOS)
before, after = scale(before, target_w), scale(after, target_w)
pad, label_h = 16, 44
strip = Image.new("RGB", (target_w * 2 + pad * 3, max(before.height, after.height) + label_h + pad * 2), (24, 24, 28))
strip.paste(before, (pad, pad + label_h))
strip.paste(after, (target_w + pad * 2, pad + label_h))
dr = ImageDraw.Draw(strip)
f = ImageFont.truetype(FONT, 26)
dr.text((pad + 10, pad + 6), "Исходник", font=f, fill=(240, 240, 240))
dr.text((target_w + pad * 2 + 10, pad + 6), 'Правка: "Change the background to a sunset beach"', font=f, fill=(240, 240, 240))
strip.save(f"{OUT}/edit-before-after.png")
print("strip ok")

# 3. Copy neon int8 as-is
Image.open(f"{SRC}/t2i_neon_test_00002_.png").save(f"{OUT}/t2i-neon-int8.png")
print("neon ok")
