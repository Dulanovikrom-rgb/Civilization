#!/usr/bin/env python3
"""Рисует единые обложки выпусков в стиле манускрипта.

Читает data/registry.json, создаёт covers/NN.jpg (1080 x 1350, формат 4:5).
Ничего не публикует. Результат одинаков при каждом запуске,
поэтому GitHub не создаёт лишних изменений.
"""
import json
import os
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1350
INK = (58, 40, 28)
ORANGE = (176, 84, 28)
PARCHMENT = (228, 208, 168)
EDGE = (150, 112, 70)

FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
    "/usr/share/fonts/TTF",
]


def font(name, size):
    for d in FONT_DIRS:
        path = os.path.join(d, name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    raise RuntimeError("Не найден шрифт %s (нужен пакет fonts-dejavu-core)" % name)


def background(seed):
    rnd = random.Random(seed)
    base = Image.new("RGB", (W, H), PARCHMENT)
    # пятна и зерно бумаги
    tile = Image.new("L", (135, 169))
    tile.putdata([rnd.randint(90, 255) for _ in range(135 * 169)])
    tile = tile.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(6))
    shade = Image.new("RGB", (W, H), EDGE)
    base = Image.composite(base, shade, tile.point(lambda v: min(255, v + 40)))
    # тёмные края (виньетка)
    mask = Image.radial_gradient("L").resize((W, H), Image.BICUBIC)
    mask = mask.point(lambda v: max(0, v - 110) * 2 // 3)
    edge = Image.new("RGB", (W, H), (96, 64, 36))
    return Image.composite(edge, base, mask)


def spaced(draw, cx, y, text, fnt, fill, gap):
    widths = [draw.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + gap * (len(text) - 1)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += w + gap


def wrap(draw, text, fnt, max_width):
    lines, line = [], ""
    for word in text.split():
        test = (line + " " + word).strip()
        if draw.textlength(test, font=fnt) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def diamond(draw, cx, cy, r, fill):
    draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)


def divider(draw, cy):
    draw.line([(190, cy), (500, cy)], fill=INK, width=3)
    draw.line([(580, cy), (890, cy)], fill=INK, width=3)
    diamond(draw, W // 2, cy, 14, ORANGE)


def make_cover(num, title, total):
    img = background(num)
    d = ImageDraw.Draw(img)
    # двойная рамка и угловые ромбы
    d.rectangle([40, 40, W - 40, H - 40], outline=INK, width=6)
    d.rectangle([62, 62, W - 62, H - 62], outline=INK, width=2)
    for x in (62, W - 62):
        for y in (62, H - 62):
            diamond(d, x, y, 16, ORANGE)

    spaced(d, W // 2, 130, "КОД ЦИВИЛИЗАЦИИ", font("DejaVuSerif-Bold.ttf", 40), INK, 8)
    divider(d, 215)

    f_num = font("DejaVuSerif-Bold.ttf", 230)
    num_text = "%02d" % num
    nw = d.textlength(num_text, font=f_num)
    d.text(((W - nw) / 2, 270), num_text, font=f_num, fill=ORANGE)

    size = 76
    while True:
        f_title = font("DejaVuSerif-Bold.ttf", size)
        lines = wrap(d, title, f_title, 800)
        if len(lines) <= 5 or size <= 48:
            break
        size -= 4
    line_h = int(size * 1.3)
    y = 640
    for line in lines:
        lw = d.textlength(line, font=f_title)
        d.text(((W - lw) / 2, y), line, font=f_title, fill=INK)
        y += line_h

    divider(d, H - 190)
    spaced(d, W // 2, H - 150, "ВЫПУСК %d ИЗ %d" % (num, total),
           font("DejaVuSerif-Bold.ttf", 32), INK, 6)
    return img


def main():
    if not os.path.exists("data/registry.json"):
        print("ОШИБКА: нет data/registry.json. Сначала запустите scripts/build.py")
        return 1
    with open("data/registry.json", encoding="utf-8") as f:
        registry = json.load(f)
    os.makedirs("covers", exist_ok=True)
    for r in registry:
        num = int(r["id"])
        make_cover(num, r["title"], len(registry)).save("covers/%s.jpg" % r["id"], quality=90)
    report = "- Обложек создано: **%d** (папка covers/)" % len(registry)
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(report + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
