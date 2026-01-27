#!/usr/bin/env python3
import cairo
import psutil
import math
import os
import time
import glob

# Папка и шаблон имени (в /tmp)
TMP_DIR = "/tmp"
FILE_PATTERN = "conky_rings_*.png"
WIDTH, HEIGHT = 600, 100

COLOR_FG = (168 / 255, 83 / 255, 47 / 255)
COLOR_BG = (0.2, 0.2, 0.2)

RINGS = [
    {"name": "cpu", "x": 185, "radius": 28, "val": 0},
    {"name": "ram", "x": 300, "radius": 28, "val": 0},
    {"name": "ssd", "x": 415, "radius": 28, "val": 0},
]
THICKNESS = 4


def get_stats():
    # Важно: interval > 0, чтобы psutil успел замерить нагрузку
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    ssd = psutil.disk_usage(os.path.expanduser("~")).percent
    return [cpu, ram, ssd]


def cleanup_old_files():
    # Удаляем старые картинки колец
    files = glob.glob(os.path.join(TMP_DIR, FILE_PATTERN))
    for f in files:
        try:
            os.remove(f)
        except:
            pass


def draw():
    # 1. Получаем данные
    stats = get_stats()

    # 2. Генерируем уникальное имя файла
    timestamp = int(time.time() * 1000)
    filename = os.path.join(TMP_DIR, f"conky_rings_{timestamp}.png")

    # 3. Рисуем
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    ctx = cairo.Context(surface)
    cy = HEIGHT // 2

    for i, ring in enumerate(RINGS):
        cx = ring["x"]
        radius = ring["radius"]
        value = stats[i]

        start_angle = -math.pi / 2
        # Фон кольца
        ctx.set_line_width(THICKNESS)
        ctx.set_source_rgba(*COLOR_BG, 0.3)
        ctx.arc(cx, cy, radius, 0, 2 * math.pi)
        ctx.stroke()

        # Прогресс
        progress_end = start_angle + (value / 100.0) * (2 * math.pi)
        ctx.set_source_rgb(*COLOR_FG)
        ctx.arc(cx, cy, radius, start_angle, progress_end)
        ctx.stroke()

    # 4. Чистим старые и сохраняем новый
    cleanup_old_files()
    surface.write_to_png(filename)

    # 5. ВАЖНО: Выводим команду для Conky
    print(f"${{image {filename} -p 0,390 -s 600x100}}")


if __name__ == "__main__":
    draw()
