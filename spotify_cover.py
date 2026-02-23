#!/usr/bin/env python3
import glob
import hashlib
import os
import subprocess
import urllib.request
import cairo

# --- НАСТРОЙКИ ---
CACHE_DIR = os.path.expanduser("./spotify_covers")
MAX_FILES = 6

# Размер итогового изображения
CANVAS_WIDTH = 600
CANVAS_HEIGHT = 100

# Позиции на канвасе
COVER_SIZE = 64
COVER_X = 180
COVER_Y = 18

TEXT_X = 260
TEXT_Y_TITLE = 45
TEXT_Y_ARTIST = 65

# Цвета (RGB 0-1)
COLOR_TITLE = (224 / 255, 152 / 255, 122 / 255)  # #E0987A
COLOR_ARTIST = (168 / 255, 83 / 255, 47 / 255)  # #A8532F

MAX_LEN_TITLE = 25
MAX_LEN_ARTIST = 35


def truncate_text(text, max_length):
    if len(text) > max_length:
        return text[:max_length].strip() + "..."
    return text


def get_metadata():
    try:
        fmt = "{{status}}||{{mpris:artUrl}}||{{title}}||{{artist}}"
        output = subprocess.check_output(
            ["playerctl", "-p", "spotify", "metadata", "--format", fmt], text=True
        ).strip()
        return output.split("||")
    except:
        return None


def download_cover(url):
    if not url:
        return None
    url = url.replace("https://open.spotify.com", "http://i.scdn.co")
    file_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
    final_path = os.path.join(CACHE_DIR, f"raw_{file_hash}.jpg")

    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    if not os.path.exists(final_path):
        try:
            urllib.request.urlretrieve(url, final_path)
        except:
            return None
    return final_path


def create_composite_image(raw_cover_path, title, artist):
    unique_str = f"{title}_{artist}_{raw_cover_path}"
    composite_hash = hashlib.md5(unique_str.encode("utf-8")).hexdigest()
    composite_path = os.path.join(CACHE_DIR, f"comp_{composite_hash}.png")

    if os.path.exists(composite_path):
        return composite_path

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, CANVAS_WIDTH, CANVAS_HEIGHT)
    ctx = cairo.Context(surface)

    if raw_cover_path and os.path.exists(raw_cover_path):
        try:
            temp_png = os.path.join(CACHE_DIR, "temp_cover.png")
            subprocess.run(
                [
                    "convert",
                    raw_cover_path,
                    "-resize",
                    f"{COVER_SIZE}x{COVER_SIZE}!",
                    temp_png,
                ],
                check=True,
            )

            img_surf = cairo.ImageSurface.create_from_png(temp_png)

            ctx.save()
            x, y, w, h = COVER_X, COVER_Y, COVER_SIZE, COVER_SIZE
            r = 15

            ctx.new_path()
            ctx.arc(x + w - r, y + r, r, -1.57, 0)
            ctx.arc(x + w - r, y + h - r, r, 0, 1.57)
            ctx.arc(x + r, y + h - r, r, 1.57, 3.14)
            ctx.arc(x + r, y + r, r, 3.14, -1.57)
            ctx.close_path()

            ctx.clip()
            ctx.set_source_surface(img_surf, x, y)
            ctx.paint()
            ctx.restore()

            if os.path.exists(temp_png):
                os.remove(temp_png)
        except Exception:
            pass

    # 2. Рисуем Текст
    ctx.select_font_face(
        "Clash Display", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL
    )
    ctx.set_font_size(18)
    ctx.set_source_rgb(*COLOR_TITLE)
    ctx.move_to(TEXT_X, TEXT_Y_TITLE)
    ctx.show_text(title)

    ctx.select_font_face(
        "Clash Display", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL
    )
    ctx.set_font_size(14)
    ctx.set_source_rgb(*COLOR_ARTIST)
    ctx.move_to(TEXT_X, TEXT_Y_ARTIST)
    ctx.show_text(artist)

    surface.write_to_png(composite_path)

    files = glob.glob(os.path.join(CACHE_DIR, "comp_*.png"))
    files.sort(key=os.path.getmtime)
    while len(files) > MAX_FILES:
        try:
            os.remove(files[0])
        except:
            pass
        files.pop(0)

    return composite_path


def main():
    data = get_metadata()
    if not data or len(data) < 4:
        return

    status, url, title, artist = data[:4]

    if status.lower() not in ["playing", "paused"]:
        return

    raw_cover = download_cover(url)
    title = truncate_text(title, MAX_LEN_TITLE)
    artist = truncate_text(artist, MAX_LEN_ARTIST).lower()

    final_img = create_composite_image(raw_cover, title, artist)

    print(f"${{image {final_img} -p 170,540 -s {CANVAS_WIDTH}x{CANVAS_HEIGHT}}}")


if __name__ == "__main__":
    main()
