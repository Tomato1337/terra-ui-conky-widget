#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.request
import cairo
import math

# --- НАСТРОЙКИ ---
DEBUG = False
WEATHER_RETRY_COUNT = 3
WEATHER_RETRY_DELAY_SEC = 1.5
AUTO_DETECT = True
DEFAULT_LAT = "52.54"
DEFAULT_LON = "85.21"

CACHE_FILE = os.path.expanduser("./weather_location.json")
LOCATION_UPDATE_INTERVAL = 14400

# Графика
TMP_DIR = "/tmp"
IMG_WIDTH = 900
IMG_HEIGHT = 100
FONT_MAIN = "Clash Display"
COLOR_PRIMARY = (224 / 255, 152 / 255, 122 / 255)  # #E0987A

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Drizzle",
    53: "Drizzle",
    55: "Drizzle",
    56: "Freezing Drizzle",
    57: "Freezing Drizzle",
    61: "Rain",
    63: "Rain",
    65: "Heavy Rain",
    66: "Freezing Rain",
    67: "Freezing Rain",
    71: "Snow",
    73: "Snow",
    75: "Heavy Snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Rain showers",
    82: "Violent showers",
    85: "Snow showers",
    86: "Snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm",
    99: "Thunderstorm",
}


def log(msg):
    if DEBUG:
        sys.stderr.write(f"[WeatherDebug] {msg}\n")


def draw_sun(ctx, x, y, size, color):
    """Рисует аккуратное солнце с закругленными лучами"""
    ctx.set_source_rgb(*color)
    ctx.set_line_width(size * 0.08)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    ctx.new_path()
    ctx.arc(x, y, size * 0.22, 0, 2 * math.pi)
    ctx.stroke()

    ctx.save()
    ctx.translate(x, y)
    for i in range(8):
        ctx.new_path()
        ctx.move_to(size * 0.35, 0)
        ctx.line_to(size * 0.48, 0)
        ctx.stroke()
        ctx.rotate(math.pi / 4)
    ctx.restore()


def draw_cloud_shape(ctx, x, y, size):
    """Рисует идеальный контур облака с помощью кривых Безье"""
    ctx.new_path()
    ctx.move_to(x - size * 0.35, y + size * 0.2)

    ctx.curve_to(
        x - size * 0.5,
        y + size * 0.2,
        x - size * 0.5,
        y - size * 0.1,
        x - size * 0.2,
        y - size * 0.05,
    )

    ctx.curve_to(
        x - size * 0.2,
        y - size * 0.35,
        x + size * 0.25,
        y - size * 0.35,
        x + size * 0.25,
        y - size * 0.05,
    )

    ctx.curve_to(
        x + size * 0.5,
        y - size * 0.05,
        x + size * 0.5,
        y + size * 0.2,
        x + size * 0.35,
        y + size * 0.2,
    )

    ctx.close_path()


def draw_cloud(ctx, x, y, size, color):
    ctx.set_source_rgb(*color)
    ctx.set_line_width(size * 0.08)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    draw_cloud_shape(ctx, x, y, size)
    ctx.stroke()


def draw_partly_cloudy(ctx, x, y, size, color):
    ctx.save()
    draw_sun(ctx, x + size * 0.15, y - size * 0.15, size * 0.75, color)
    ctx.restore()

    ctx.save()
    draw_cloud_shape(ctx, x - size * 0.05, y + size * 0.05, size * 0.85)
    ctx.set_operator(cairo.OPERATOR_CLEAR)
    ctx.fill_preserve()

    ctx.set_operator(cairo.OPERATOR_OVER)
    ctx.set_source_rgb(*color)
    ctx.set_line_width(size * 0.08)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    ctx.restore()


def draw_rain_drops(ctx, x, y, size, color):
    ctx.set_source_rgb(*color)
    ctx.set_line_width(size * 0.05)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    # 3 аккуратные, симметричные капли: (смещение_X, начало_Y, конец_Y)
    drops = [
        (-0.15, 0.28, 0.42),
        (0.0, 0.35, 0.49),
        (0.19, 0.28, 0.42),
    ]
    for dx, y1, y2 in drops:
        ctx.new_path()
        ctx.move_to(x + size * dx, y + size * y1)
        ctx.line_to(x + size * (dx - 0.05), y + size * y2)
        ctx.stroke()


def draw_snow_flakes(ctx, x, y, size, color):
    ctx.set_source_rgb(*color)
    ctx.set_line_width(size * 0.04)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    flakes = [(-0.15, 0.35), (0.15, 0.4), (-0.05, 0.6)]
    for dx, dy in flakes:
        fx, fy = x + size * dx, y + size * dy
        r = size * 0.0
        for i in range(3):
            ctx.new_path()
            angle = i * (math.pi / 3)
            ctx.move_to(fx - r * math.cos(angle), fy - r * math.sin(angle))
            ctx.line_to(fx + r * math.cos(angle), fy + r * math.sin(angle))
            ctx.stroke()


def draw_bolt(ctx, x, y, size, color):
    ctx.set_source_rgb(*color)
    ctx.set_line_width(size * 0.02)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)

    ctx.new_path()
    bx, by = x, y + size * 0.15
    ctx.move_to(bx + size * 0.05, by)
    ctx.line_to(bx - size * 0.08, by + size * 0.3)
    ctx.line_to(bx + size * 0.05, by + size * 0.3)
    ctx.line_to(bx - size * 0.02, by + size * 0.5)
    ctx.line_to(bx + size * 0.12, by + size * 0.2)
    ctx.line_to(bx - size * 0.02, by + size * 0.2)
    ctx.close_path()

    ctx.fill_preserve()
    ctx.stroke()


def draw_cloud_rain(ctx, x, y, size, color):
    draw_cloud(ctx, x, y - size * 0.05, size * 0.9, color)
    draw_rain_drops(ctx, x, y, size, color)


def draw_cloud_snow(ctx, x, y, size, color):
    draw_cloud(ctx, x, y - size * 0.05, size * 0.9, color)
    draw_snow_flakes(ctx, x, y, size, color)


def draw_cloud_bolt(ctx, x, y, size, color):
    draw_cloud(ctx, x, y - size * 0.05, size * 0.9, color)
    draw_bolt(ctx, x, y, size, color)


def draw_cloud_rain_bolt(ctx, x, y, size, color):
    """Облако, дождь и молния (гроза)"""
    draw_cloud(ctx, x, y - size * 0.05, size * 0.9, color)

    draw_bolt(ctx, x, y, size * 0.8, color)

    ctx.set_source_rgb(*color)
    ctx.set_line_width(size * 0.05)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    drops = [(-0.2, 0.3, 0.45), (0.2, 0.3, 0.45)]
    for dx, y1, y2 in drops:
        ctx.new_path()
        ctx.move_to(x + size * dx, y + size * y1)
        ctx.line_to(x + size * (dx - 0.05), y + size * y2)
        ctx.stroke()


def draw_partly_cloudy_rain(ctx, x, y, size, color):
    """Солнце из-за облака с дождем (кратковременные осадки)"""
    draw_partly_cloudy(ctx, x, y, size, color)
    draw_rain_drops(ctx, x - size * 0.05, y + size * 0.05, size * 0.85, color)


def draw_partly_cloudy_snow(ctx, x, y, size, color):
    """Солнце из-за облака со снегом (кратковременный снег)"""
    draw_partly_cloudy(ctx, x, y, size, color)
    draw_snow_flakes(ctx, x - size * 0.05, y + size * 0.05, size * 0.85, color)


def draw_fog(ctx, x, y, size, color):
    ctx.set_source_rgb(*color)
    ctx.set_line_width(size * 0.08)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    lines = [(-0.15, 0.6, -0.1), (0.0, 0.9, 0.0), (0.15, 0.7, 0.05), (0.3, 0.5, -0.05)]
    for dy, w_mult, x_offset in lines:
        ctx.new_path()
        w = size * w_mult
        ctx.move_to(x + size * x_offset - w / 2, y + size * dy)
        ctx.line_to(x + size * x_offset + w / 2, y + size * dy)
        ctx.stroke()


def draw_icon_by_code(ctx, code, x, y, size, color):
    if code == 0:
        draw_sun(ctx, x, y, size, color)
    elif code == 1:
        draw_partly_cloudy(ctx, x, y, size, color)
    elif code in [2, 3]:
        draw_cloud(ctx, x, y, size, color)
    elif code in [45, 48]:
        draw_fog(ctx, x, y, size, color)
    elif code in [51, 53, 55, 61, 63, 65]:
        draw_cloud_rain(ctx, x, y, size, color)
    elif code in [80, 81, 82]:
        draw_partly_cloudy_rain(ctx, x, y, size, color)
    elif code in [56, 57, 66, 67, 71, 73, 75, 77]:
        draw_cloud_snow(ctx, x, y, size, color)
    elif code in [85, 86]:
        draw_partly_cloudy_snow(ctx, x, y, size, color)
    elif code in [95, 96, 99]:
        draw_cloud_rain_bolt(ctx, x, y, size, color)
    else:
        draw_cloud(ctx, x, y, size, color)


def get_location_from_ip():
    try:
        url = "http://ip-api.com/json/"
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.load(response)
            if data["status"] == "success":
                return str(data["lat"]), str(data["lon"])
    except:
        pass
    return None


def get_coords():
    if not AUTO_DETECT:
        return DEFAULT_LAT, DEFAULT_LON
    if os.path.exists(CACHE_FILE):
        try:
            mtime = os.path.getmtime(CACHE_FILE)
            if (time.time() - mtime) < LOCATION_UPDATE_INTERVAL:
                with open(CACHE_FILE, "r") as f:
                    d = json.load(f)
                    return d["lat"], d["lon"]
        except:
            pass
    loc = get_location_from_ip()
    if loc:
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump({"lat": loc[0], "lon": loc[1]}, f)
        except:
            pass
        return loc
    return DEFAULT_LAT, DEFAULT_LON


def get_weather_data():
    lat, lon = get_coords()
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code&wind_speed_unit=ms"
    for _ in range(WEATHER_RETRY_COUNT):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.load(response)
                curr = data.get("current", {})
                temp = curr.get("temperature_2m", 0)
                code = curr.get("weather_code", 0)
                desc = WEATHER_CODES.get(code, "Unknown")
                return temp, code, desc.lower()
        except:
            time.sleep(WEATHER_RETRY_DELAY_SEC)
    return None, None, None


def create_weather_image(temp, code, desc):
    timestamp = int(time.time())
    filename = os.path.join(TMP_DIR, f"conky_weather_{timestamp}.png")

    try:
        for f in os.listdir(TMP_DIR):
            if f.startswith("conky_weather_"):
                os.remove(os.path.join(TMP_DIR, f))
    except:
        pass

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, IMG_WIDTH, IMG_HEIGHT)
    ctx = cairo.Context(surface)

    ICON_SIZE = 50
    FONT_SIZE = 48

    sign = ""
    temp_str = f"{sign}{temp:.0f}°c"

    ctx.select_font_face(FONT_MAIN, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(FONT_SIZE)

    ext_temp = ctx.text_extents(temp_str)
    ext_desc = ctx.text_extents(desc)

    GAP_ICON_TEMP = 20
    GAP_TEMP_PIPE = 25
    GAP_PIPE_DESC = 25
    PIPE_WIDTH = 2

    total_width = (
        ICON_SIZE
        + GAP_ICON_TEMP
        + ext_temp.width
        + ext_temp.x_bearing
        + GAP_TEMP_PIPE
        + PIPE_WIDTH
        + GAP_PIPE_DESC
        + ext_desc.width
        + ext_desc.x_bearing
    )

    start_x = (IMG_WIDTH - total_width) / 2
    base_y = (IMG_HEIGHT / 2) + (ext_temp.height / 2) - 8

    # 1. Icon
    icon_x = start_x + ICON_SIZE / 2
    icon_y = IMG_HEIGHT / 2 - 5
    draw_icon_by_code(ctx, code, icon_x, icon_y, ICON_SIZE, COLOR_PRIMARY)

    current_x = start_x + ICON_SIZE + GAP_ICON_TEMP

    # 2. Temp
    ctx.set_source_rgb(*COLOR_PRIMARY)
    ctx.move_to(current_x, base_y)
    ctx.show_text(temp_str)

    current_x += ext_temp.width + ext_temp.x_bearing + GAP_TEMP_PIPE

    # 3. Separator
    ctx.set_line_width(PIPE_WIDTH)
    r, g, b = COLOR_PRIMARY
    ctx.set_source_rgba(r, g, b, 0.4)

    pipe_h = 40
    pipe_y_center = IMG_HEIGHT / 2 - 8
    ctx.move_to(current_x, pipe_y_center - pipe_h / 2)
    ctx.line_to(current_x, pipe_y_center + pipe_h / 2)
    ctx.stroke()

    current_x += PIPE_WIDTH + GAP_PIPE_DESC

    # 4. Description
    ctx.set_source_rgb(*COLOR_PRIMARY)
    ctx.move_to(current_x, base_y)
    ctx.show_text(desc)

    surface.write_to_png(filename)
    return filename


def main():
    temp, code, desc = get_weather_data()
    if temp is None:
        return
    img_path = create_weather_image(temp, code, desc)
    print(f"${{image {img_path} -p 0,300 -s {IMG_WIDTH}x{IMG_HEIGHT}}}")


if __name__ == "__main__":
    main()
