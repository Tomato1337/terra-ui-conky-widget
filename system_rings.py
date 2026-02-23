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
# Увеличиваем высоту, чтобы влез текст снизу
WIDTH, HEIGHT = 600, 130

COLOR_ACCENT = (224 / 255, 152 / 255, 122 / 255)  # #E0987A
COLOR_BG = (0.2, 0.2, 0.2)

RINGS = [
    {"name": "CPU", "x": 185, "radius": 28, "val": 0},
    {"name": "RAM", "x": 300, "radius": 28, "val": 0},
    {"name": "SSD", "x": 415, "radius": 28, "val": 0},
]
THICKNESS = 4


def get_stats():
    # Важно: interval > 0, чтобы psutil успел замерить нагрузку
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    ssd = psutil.disk_usage(os.path.expanduser("~")).percent
    return [cpu, ram, ssd]


def cleanup_old_files():
    files = glob.glob(os.path.join(TMP_DIR, FILE_PATTERN))
    for f in files:
        try:
            os.remove(f)
        except:
            pass


def draw_text_centered(ctx, text, x, y, font_size, weight="Medium"):
    ctx.select_font_face(
        "Clash Display",
        cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_BOLD if weight == "Bold" else cairo.FONT_WEIGHT_NORMAL,
    )
    ctx.set_font_size(font_size)
    extents = ctx.text_extents(text)
    ctx.move_to(
        x - extents.width / 2 - extents.x_bearing,
        y - extents.height / 2 - extents.y_bearing,
    )
    ctx.show_text(text)


def draw():
    stats = get_stats()
    timestamp = int(time.time() * 1000)
    filename = os.path.join(TMP_DIR, f"conky_rings_{timestamp}.png")

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    ctx = cairo.Context(surface)

    # Центр колец по вертикали
    cy = 50

    for i, ring in enumerate(RINGS):
        cx = ring["x"]
        radius = ring["radius"]
        value = stats[i]
        label = ring["name"]

        start_angle = -math.pi / 2

        # Фон кольца
        ctx.new_path()
        ctx.set_line_width(THICKNESS)
        ctx.set_source_rgba(*COLOR_BG, 0.3)
        ctx.arc(cx, cy, radius, 0, 2 * math.pi)
        ctx.stroke()

        # Прогресс
        progress_end = start_angle + (value / 100.0) * (2 * math.pi)
        ctx.new_path()
        ctx.set_source_rgb(*COLOR_ACCENT)
        if value > 0:
            ctx.arc(cx, cy, radius, start_angle, progress_end)
            ctx.stroke()

        # Текст: Значение (Внутри кольца, по центру)
        draw_text_centered(ctx, f"{int(value)}%", cx, cy + 2, 12, "Medium")

        # Текст: Название (Снизу под кольцом)
        # cy + radius + 20px отступ
        draw_text_centered(ctx, label, cx, cy + radius + 20, 12, "Bold")

    cleanup_old_files()
    surface.write_to_png(filename)

    # Сдвигаем кольца вниз на Y=480, чтобы дать место длинной погоде
    print(f"${{image {filename} -p 450,430 -s {WIDTH}x{HEIGHT}}}")


if __name__ == "__main__":
    draw()
