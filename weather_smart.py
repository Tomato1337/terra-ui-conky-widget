#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.request
import cairo
import subprocess
from datetime import datetime

# --- НАСТРОЙКИ ---
DEBUG = True
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
COLOR_PRIMARY_HEX = "#E0987A"
COLOR_PRIMARY_RGB = (224 / 255, 152 / 255, 122 / 255)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(SCRIPT_DIR, "weather_icons")

# Маппинг кодов
WEATHER_ICONS_MAP = {
    # 0-9: Явления без осадков (облачность, дым, пыль)
    0: ("wi-day-sunny", "wi-night-clear"),
    1: ("wi-day-cloudy-high", "wi-night-alt-cloudy-high"),
    2: (
        "wi-day-sunny-overcast",
        "wi-night-alt-partly-cloudy",
    ),  # Идеально для "переменной облачности"
    3: ("wi-cloudy", "wi-cloudy"),
    4: ("wi-smoke", "wi-smoke"),
    5: ("wi-day-haze", "wi-night-fog"),
    6: ("wi-dust", "wi-dust"),
    7: ("wi-dust", "wi-dust"),
    8: ("wi-sandstorm", "wi-sandstorm"),
    9: ("wi-sandstorm", "wi-sandstorm"),
    # 10-19: Мгла, туман, шквалы и молнии
    10: ("wi-day-fog", "wi-night-fog"),
    11: ("wi-fog", "wi-night-fog"),
    12: ("wi-fog", "wi-night-fog"),
    13: ("wi-day-lightning", "wi-night-alt-lightning"),
    14: ("wi-day-sprinkle", "wi-night-alt-sprinkle"),
    15: ("wi-day-showers", "wi-night-alt-showers"),
    16: ("wi-day-showers", "wi-night-alt-showers"),
    17: ("wi-day-lightning", "wi-night-alt-lightning"),
    18: ("wi-day-cloudy-gusts", "wi-night-alt-cloudy-gusts"),  # Шквалы
    19: ("wi-tornado", "wi-tornado"),
    # 20-29: Осадки или туман за последний час
    20: ("wi-day-sprinkle", "wi-night-alt-sprinkle"),
    21: ("wi-day-rain", "wi-night-alt-rain"),
    22: ("wi-day-snow", "wi-night-alt-snow"),
    23: ("wi-day-rain-mix", "wi-night-alt-rain-mix"),
    24: ("wi-day-sleet", "wi-night-alt-sleet"),
    25: ("wi-day-showers", "wi-night-alt-showers"),
    26: ("wi-day-snow", "wi-night-alt-snow"),
    27: ("wi-day-hail", "wi-night-alt-hail"),
    28: ("wi-fog", "wi-night-fog"),
    29: ("wi-day-thunderstorm", "wi-night-alt-thunderstorm"),
    # 40-49: Туман (различной интенсивности)
    41: ("wi-fog", "wi-night-fog"),
    45: ("wi-fog", "wi-night-fog"),
    48: ("wi-fog", "wi-night-fog"),
    # 50-59: Морось и изморозь
    51: ("wi-raindrops", "wi-raindrops"),  # Отличная иконка для легкой мороси
    53: ("wi-day-sprinkle", "wi-night-alt-sprinkle"),
    55: ("wi-day-rain", "wi-night-alt-rain"),
    56: ("wi-day-sleet", "wi-night-alt-sleet"),
    57: ("wi-day-sleet", "wi-night-alt-sleet"),
    # 60-69: Дождь
    61: ("wi-day-showers", "wi-night-alt-showers"),
    63: ("wi-day-rain", "wi-night-alt-rain"),
    65: ("wi-day-rain-wind", "wi-night-alt-rain-wind"),
    66: ("wi-day-rain-mix", "wi-night-alt-rain-mix"),
    67: ("wi-day-sleet-storm", "wi-night-alt-sleet-storm"),
    # 70-79: Снег
    71: ("wi-day-snow", "wi-night-alt-snow"),
    73: ("wi-snow", "wi-snow"),
    75: ("wi-day-snow-wind", "wi-night-alt-snow-wind"),
    77: ("wi-snowflake-cold", "wi-snowflake-cold"),
    # 80-99: Ливни и грозы
    80: ("wi-day-showers", "wi-night-alt-showers"),
    81: ("wi-day-storm-showers", "wi-night-alt-storm-showers"),
    82: ("wi-day-storm-showers", "wi-night-alt-storm-showers"),
    85: ("wi-day-snow", "wi-night-alt-snow"),
    86: ("wi-day-snow-wind", "wi-night-alt-snow-wind"),
    87: ("wi-day-hail", "wi-night-alt-hail"),
    89: ("wi-day-hail", "wi-night-alt-hail"),
    95: ("wi-day-thunderstorm", "wi-night-alt-thunderstorm"),
    96: ("wi-day-snow-thunderstorm", "wi-night-alt-snow-thunderstorm"),
    99: ("wi-day-snow-thunderstorm", "wi-night-alt-snow-thunderstorm"),
    # === КАСТОМНЫЕ КОДЫ (100+) ДЛЯ ЭКСТРЕМАЛЬНЫХ И СПЕЦИАЛЬНЫХ ЯВЛЕНИЙ ===
    100: ("wi-smog", "wi-smog"),
    101: ("wi-hurricane", "wi-hurricane"),
    102: ("wi-volcano", "wi-volcano"),
    103: ("wi-earthquake", "wi-earthquake"),
    104: ("wi-flood", "wi-flood"),
    105: ("wi-tsunami", "wi-tsunami"),
    106: ("wi-fire", "wi-fire"),
    107: ("wi-meteor", "wi-meteor"),
    108: ("wi-alien", "wi-alien"),  # Пасхалка / Неопознанное атмосферное явление
    109: ("wi-solar-eclipse", "wi-lunar-eclipse"),  # Затмения (дневное/ночное)
    110: ("wi-hot", "wi-hot"),
    111: ("wi-strong-wind", "wi-strong-wind"),
    112: (
        "wi-small-craft-advisory",
        "wi-small-craft-advisory",
    ),  # Предупреждение для малых судов
    113: ("wi-gale-warning", "wi-gale-warning"),  # Штормовое предупреждение (ветер)
    114: ("wi-storm-warning", "wi-storm-warning"),  # Штормовое предупреждение (буря)
    115: ("wi-hurricane-warning", "wi-hurricane-warning"),  # Угроза урагана
}

# Расширенные описания
WEATHER_CODES_DESC = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    4: "Smoke",
    5: "Haze",
    6: "Widespread dust",
    7: "Dust or sand raised by wind",
    8: "Well developed dust whirls",
    9: "Sandstorm",
    10: "Mist",
    11: "Patches of shallow fog",
    12: "Continuous shallow fog",
    13: "Lightning visible, no thunder",
    14: "Precipitation within sight",
    15: "Precipitation distant",
    16: "Precipitation near station",
    17: "Thunderstorm, no precipitation",
    18: "Squalls",
    19: "Tornado / Funnel cloud",
    20: "Drizzle (past hour)",
    21: "Rain (past hour)",
    22: "Snow (past hour)",
    23: "Rain and snow (past hour)",
    24: "Freezing drizzle (past hour)",
    25: "Showers of rain (past hour)",
    26: "Showers of snow (past hour)",
    27: "Showers of hail (past hour)",
    28: "Fog (past hour)",
    29: "Thunderstorm (past hour)",
    41: "Patchy fog",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Drizzle: Light",
    53: "Drizzle: Moderate",
    55: "Drizzle: Dense intensity",
    56: "Freezing Drizzle: Light",
    57: "Freezing Drizzle: Dense intensity",
    61: "Rain: Slight",
    63: "Rain: Moderate",
    65: "Rain: Heavy intensity",
    66: "Freezing Rain: Light",
    67: "Freezing Rain: Heavy intensity",
    71: "Snow fall: Slight",
    73: "Snow fall: Moderate",
    75: "Snow fall: Heavy intensity",
    77: "Snow grains",
    80: "Rain showers: Slight",
    81: "Rain showers: Moderate",
    82: "Violent showers",
    85: "Snow showers: Slight",
    86: "Snow showers: Heavy",
    87: "Snow pellets showers",
    89: "Hail showers",
    95: "Thunderstorm: Slight or moderate",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
    # Спец. коды
    100: "Heavy Smog",
    101: "Hurricane",
    102: "Volcanic Ash",
    103: "Earthquake",
    104: "Flood",
    105: "Tsunami",
    106: "Wildfire",
    107: "Meteor strike",
    108: "Unknown Atmospheric Phenomenon / Alien",
    109: "Eclipse",
    110: "Extreme Heat",
    111: "Strong Gale",
    112: "Small Craft Advisory",
    113: "Gale Warning",
    114: "Storm Warning",
    115: "Hurricane Warning",
}


def log(msg):
    if DEBUG:
        sys.stderr.write(f"[WeatherDebug] {msg}\n")


# --- ЛОГИКА ---
def get_location_from_ip():
    try:
        url = "http://ip-api.com/json/"
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.load(response)
            if data["status"] == "success":
                log(
                    f"Detected location: {data['city']}, {data['country']} (lat: {data['lat']}, lon: {data['lon']})"
                )
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
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,is_day&timezone=auto"
    for _ in range(WEATHER_RETRY_COUNT):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.load(response)
                curr = data.get("current", {})
                temp = curr.get("temperature_2m", 0)
                code = curr.get("weather_code", 0)
                is_day = curr.get("is_day", 1)
                desc = WEATHER_CODES_DESC.get(code, "Unknown")
                return temp, code, desc, is_day
        except:
            time.sleep(WEATHER_RETRY_DELAY_SEC)
    return None, None, None, 1


def prepare_icon(code, is_day):
    pair = WEATHER_ICONS_MAP.get(code, ("wi-na", "wi-na"))
    icon_name = pair[0] if is_day == 1 else pair[1]
    svg_path = os.path.join(ICONS_DIR, f"{icon_name}.svg")

    if not os.path.exists(svg_path):
        return None

    try:
        with open(svg_path, "r") as f:
            svg_content = f.read()

        colored_svg = svg_content.replace("<svg ", f'<svg fill="{COLOR_PRIMARY_HEX}" ')

        temp_svg = os.path.join(TMP_DIR, "temp_weather_icon.svg")
        with open(temp_svg, "w") as f:
            f.write(colored_svg)

        temp_png = os.path.join(TMP_DIR, "temp_weather_icon.png")

        # High Quality Render
        subprocess.run(
            [
                "convert",
                "-background",
                "none",
                "-density",
                "300",  # Высокое разрешение
                temp_svg,
                "-resize",
                "256x256",  # Большой размер
                temp_png,
            ],
            check=True,
        )

        return temp_png
    except Exception as e:
        if DEBUG:
            print(f"Icon error: {e}")
        return None


def create_weather_image(temp, code, desc, is_day):
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

    icon_png_path = prepare_icon(code, is_day)

    ICON_DISPLAY_SIZE = 64
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
        ICON_DISPLAY_SIZE
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
    icon_x = start_x
    icon_y = (IMG_HEIGHT - ICON_DISPLAY_SIZE) / 2 - 5

    if icon_png_path and os.path.exists(icon_png_path):
        try:
            img_surf = cairo.ImageSurface.create_from_png(icon_png_path)
            ctx.save()
            ctx.translate(icon_x, icon_y)

            # Масштабирование
            raw_w = img_surf.get_width()
            scale = ICON_DISPLAY_SIZE / float(raw_w)

            ctx.scale(scale, scale)
            ctx.set_source_surface(img_surf, 0, 0)
            ctx.paint()
            ctx.restore()
        except:
            pass

    current_x = start_x + ICON_DISPLAY_SIZE + GAP_ICON_TEMP - 10

    # 2. Temp
    ctx.set_source_rgb(*COLOR_PRIMARY_RGB)
    ctx.move_to(current_x, base_y)
    ctx.show_text(temp_str)

    current_x += ext_temp.width + ext_temp.x_bearing + GAP_TEMP_PIPE

    # 3. Separator
    ctx.set_line_width(PIPE_WIDTH)
    r, g, b = COLOR_PRIMARY_RGB
    ctx.set_source_rgba(r, g, b, 0.4)

    pipe_h = 40
    pipe_y_center = IMG_HEIGHT / 2 - 8
    ctx.move_to(current_x, pipe_y_center - pipe_h / 2)
    ctx.line_to(current_x, pipe_y_center + pipe_h / 2)
    ctx.stroke()

    current_x += PIPE_WIDTH + GAP_PIPE_DESC

    # 4. Description
    ctx.set_source_rgb(*COLOR_PRIMARY_RGB)
    ctx.move_to(current_x, base_y)
    ctx.show_text(desc)

    surface.write_to_png(filename)
    return filename


def main():
    temp, code, desc, is_day = get_weather_data()
    if temp is None:
        return
    img_path = create_weather_image(temp, code, desc, is_day)
    print(f"${{image {img_path} -p 0,300d -s {IMG_WIDTH}x{IMG_HEIGHT}}}")


if __name__ == "__main__":
    main()
