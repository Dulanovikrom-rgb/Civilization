#!/usr/bin/env python3
"""Разбирает Word-файл (source/ или корень репозитория) на отдельные выпуски.

Создаёт:
  articles/NN.md   - текст выпуска
  prompts/NN.txt   - промпт для иллюстрации
  data/registry.json - реестр выпусков (статус, источники, наличие картинки)

Ничего не публикует. Если проверка не пройдена, файлы не меняются.
"""
import glob
import json
import os
import re
import sys

import docx

MARKER = "ПРОМПТ ДЛЯ ИЛЛЮСТРАЦИИ"
IDEA = "Главная мысль:"
IMAGE_EXTS = ("jpg", "jpeg", "png", "webp")


def parse(path):
    document = docx.Document(path)
    items = []
    current = None
    stage = "body"
    for p in document.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        m = re.match(r"^(\d{1,3})\.\s*(.+)$", text)
        if p.style.name.startswith("Heading 1") and m:
            current = {"num": int(m.group(1)), "title": m.group(2).strip(),
                       "body": [], "idea": "", "prompt": []}
            items.append(current)
            stage = "body"
            continue
        if current is None:
            continue
        if text.startswith(MARKER):
            stage = "prompt"
        elif stage == "prompt":
            current["prompt"].append(text)
        elif text.startswith(IDEA):
            current["idea"] = text[len(IDEA):].strip()
        else:
            current["body"].append(text)
    return items


def validate(items):
    errors = []
    nums = [i["num"] for i in items]
    if not items:
        errors.append("Не найдено ни одного выпуска")
    if nums != list(range(1, len(items) + 1)):
        errors.append("Номера выпусков идут не подряд: %s" % nums)
    for i in items:
        label = "Выпуск %02d" % i["num"]
        if not i["title"]:
            errors.append(label + ": нет заголовка")
        if not i["body"]:
            errors.append(label + ": нет основного текста")
        if not i["idea"]:
            errors.append(label + ": нет «Главной мысли»")
        if not i["prompt"]:
            errors.append(label + ": нет промпта для иллюстрации")
    return errors


def find_image(num):
    for ext in IMAGE_EXTS:
        path = "images/%02d.%s" % (num, ext)
        if os.path.exists(path):
            return path
    return None


def main():
    files = sorted(glob.glob("source/*.docx")) or sorted(glob.glob("*.docx"))
    if not files:
        print("ОШИБКА: не найден файл .docx ни в source/, ни в корне репозитория")
        return 1
    if len(files) > 1:
        print("ОШИБКА: найдено больше одного .docx: %s" % files)
        return 1
    print("Исходный файл:", files[0])
    items = parse(files[0])
    errors = validate(items)
    if errors:
        print("ПРОВЕРКА НЕ ПРОЙДЕНА:")
        for e in errors:
            print(" -", e)
        return 1

    old = {}
    if os.path.exists("data/registry.json"):
        with open("data/registry.json", encoding="utf-8") as f:
            old = {r["id"]: r for r in json.load(f)}

    for d in ("articles", "prompts", "data", "images"):
        os.makedirs(d, exist_ok=True)
    open("images/.gitkeep", "a").close()

    registry = []
    for i in items:
        nid = "%02d" % i["num"]
        with open("articles/%s.md" % nid, "w", encoding="utf-8") as f:
            f.write("# %s\n\n" % i["title"])
            f.write("\n\n".join(i["body"]) + "\n\n")
            f.write("**Главная мысль:** %s\n" % i["idea"])
        with open("prompts/%s.txt" % nid, "w", encoding="utf-8") as f:
            f.write("\n\n".join(i["prompt"]) + "\n")
        prev = old.get(nid, {})
        image = find_image(i["num"])
        registry.append({
            "id": nid,
            "title": i["title"],
            "article": "articles/%s.md" % nid,
            "prompt": "prompts/%s.txt" % nid,
            "image": image,
            "status": prev.get("status", "draft"),
            "sources": prev.get("sources", []),
        })
    with open("data/registry.json", "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with_img = sum(1 for r in registry if r["image"])
    no_src = sum(1 for r in registry if not r["sources"])
    lines = [
        "## Код цивилизации: отчёт",
        "",
        "- Выпусков разобрано: **%d**" % len(registry),
        "- С иллюстрацией: **%d** из %d" % (with_img, len(registry)),
        "- Без источников: **%d** из %d (к публикации не готовы)" % (no_src, len(registry)),
    ]
    missing = [r["id"] for r in registry if not r["image"]]
    if missing:
        lines.append("- Нет картинок для номеров: " + ", ".join(missing))
    report = "\n".join(lines)
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(report + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
