#!/usr/bin/env python3
import os
import subprocess
import hashlib
import glob
import urllib.request

# --- НАСТРОЙКИ ---
CACHE_DIR = os.path.expanduser("./spotify_covers")
MAX_FILES = 6

# Настройки отображения
IMG_POS = "-p 200,530"
IMG_W = 64
IMG_H = 64
IMG_SIZE = f"-s {IMG_W}x{IMG_H}"
RADIUS = 20
TEXT_X = 280

# === НАСТРОЙКИ ОБРЕЗКИ ТЕКСТА (N символов) ===
# Если длина превышает это число, текст обрежется и добавится "..."
MAX_LEN_TITLE = 20  # Для названия (шрифт крупнее, места меньше)
MAX_LEN_ARTIST = 30  # Для исполнителя

# Цвета
COLOR_TEXT = "${color #E0987A}"
COLOR_SUB = "${color #A8532F}"

# Бар
BAR_WIDTH = 18
CHAR_EMPTY = "—"
CHAR_FILLED = "—"
CHAR_KNOB = "●"


def format_time(microseconds):
    seconds = int(microseconds / 1000000)
    return f"{seconds // 60}:{seconds % 60:02d}"


def truncate_text(text, max_length):
    """Обрезает текст и добавляет многоточие, если он слишком длинный"""
    if len(text) > max_length:
        return text[:max_length].strip() + "..."
    return text


def get_metadata():
    try:
        fmt = "{{status}}||{{mpris:artUrl}}||{{title}}||{{artist}}||{{position}}||{{mpris:length}}"
        output = subprocess.check_output(
            ["playerctl", "-p", "spotify", "metadata", "--format", fmt], text=True
        ).strip()
        return output.split("||")
    except:
        return None


def process_image(url):
    if not url:
        return None
    url = url.replace("https://open.spotify.com", "http://i.scdn.co")
    file_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
    final_path = os.path.join(CACHE_DIR, f"{file_hash}.png")
    temp_path = os.path.join(CACHE_DIR, "temp_download.jpg")

    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    if not os.path.exists(final_path):
        try:
            urllib.request.urlretrieve(url, temp_path)
            subprocess.run(
                [
                    "convert",
                    temp_path,
                    "-resize",
                    f"{IMG_W}x{IMG_H}^",
                    "-gravity",
                    "center",
                    "-extent",
                    f"{IMG_W}x{IMG_H}",
                    "-alpha",
                    "set",
                    "(",
                    "+clone",
                    "-alpha",
                    "transparent",
                    "-fill",
                    "white",
                    "-draw",
                    f"roundrectangle 0,0,{IMG_W},{IMG_H},{RADIUS},{RADIUS}",
                    ")",
                    "-compose",
                    "DstIn",
                    "-composite",
                    final_path,
                ],
                check=True,
            )
        except:
            return None
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    else:
        os.utime(final_path, None)

    files = glob.glob(os.path.join(CACHE_DIR, "*.png"))
    files.sort(key=os.path.getmtime)
    while len(files) > MAX_FILES:
        os.remove(files[0])
        files.pop(0)

    return final_path


def main():
    data = get_metadata()
    if not data or len(data) < 6:
        return

    status, url, title, artist, position, length = data

    if status.lower() not in ["playing", "paused"]:
        return

    img_path = process_image(url)

    # === ПРИМЕНЯЕМ ОБРЕЗКУ ===
    title = truncate_text(title, MAX_LEN_TITLE)
    artist = truncate_text(artist, MAX_LEN_ARTIST).lower()

    # Бар и время
    try:
        pos_micros = float(position)
        len_micros = float(length)
        if len_micros > 0:
            pct = pos_micros / len_micros
            idx = int(pct * BAR_WIDTH)
            idx = max(0, min(idx, BAR_WIDTH - 1))
            bar = (CHAR_FILLED * idx) + CHAR_KNOB + (CHAR_EMPTY * (BAR_WIDTH - idx - 1))
            time_str = f"{format_time(pos_micros)} / {format_time(len_micros)}"
        else:
            bar = ""
            time_str = ""
    except:
        bar = ""
        time_str = ""

    # Вывод
    if img_path:
        print(f"${{image {img_path} {IMG_POS} {IMG_SIZE}}}")

    print(
        f"${{voffset 0}}${{goto {TEXT_X}}}{COLOR_TEXT}${{font Clash Display:weight=Medium:size=18}}{title}${{font}}"
    )
    print(
        f"${{voffset 4}}${{goto {TEXT_X}}}{COLOR_SUB}${{font Clash Display:weight=Medium:size=14}}{artist}${{font}}"
    )


if __name__ == "__main__":
    main()
