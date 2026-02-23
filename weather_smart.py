#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.request

# Включает подробный вывод в терминал для проверки
DEBUG = False

# Повторы запроса погоды при временных сбоях
WEATHER_RETRY_COUNT = 3
WEATHER_RETRY_DELAY_SEC = 1.5

# Автоматическое определение города (True/False)
AUTO_DETECT = True

# Координаты по умолчанию, используются если AUTO_DETECT = False
DEFAULT_LAT = "52.54"
DEFAULT_LON = "85.21"

CACHE_FILE = os.path.expanduser("./weather_location.json")
LOCATION_UPDATE_INTERVAL = 14400


def log(msg):
    if DEBUG:
        sys.stderr.write(f"[WeatherDebug] {msg}\n")


def get_condition_text(code):
    mapping = {
        0: "clear sky",
        1: "mainly clear",
        2: "partly cloudy",
        3: "overcast",
        45: "fog",
        48: "depositing rime fog",
        51: "light drizzle",
        53: "drizzle",
        55: "dense drizzle",
        56: "light freezing drizzle",
        57: "freezing drizzle",
        61: "slight rain",
        63: "rain",
        65: "heavy rain",
        66: "freezing rain",
        67: "heavy freezing rain",
        71: "slight snow",
        73: "snow",
        75: "heavy snow",
        77: "snow grains",
        80: "slight rain showers",
        81: "rain showers",
        82: "violent rain showers",
        85: "slight snow showers",
        86: "heavy snow showers",
        95: "thunderstorm",
        96: "thunderstorm with hail",
        99: "thunderstorm with heavy hail",
    }
    return mapping.get(code, "unknown")


def get_location_from_ip():
    log("Requesting IP location (via Direct Route)...")
    try:
        # Этот запрос должен уйти в обход VPN благодаря настройке Throne
        url = "http://ip-api.com/json/"
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.load(response)
            if data["status"] == "success":
                log(f"API found: {data.get('city')} ({data['lat']}, {data['lon']})")
                return str(data["lat"]), str(data["lon"]), data.get("city", "Unknown")
    except Exception as e:
        log(f"Location API Error: {e}")
    return None


def update_location_cache():
    # Проверяем, не слишком ли стар кэш
    if os.path.exists(CACHE_FILE):
        try:
            mtime = os.path.getmtime(CACHE_FILE)
            if (time.time() - mtime) < LOCATION_UPDATE_INTERVAL:
                return
        except:
            pass

    # Если кэш старый или его нет — обновляем
    loc_data = get_location_from_ip()
    if loc_data:
        lat, lon, city = loc_data
        try:
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump(
                    {"lat": lat, "lon": lon, "city": city, "timestamp": time.time()}, f
                )
            log("Cache updated with new coordinates")
        except:
            pass


def get_coords():
    if not AUTO_DETECT:
        return DEFAULT_LAT, DEFAULT_LON

    update_location_cache()

    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                return data["lat"], data["lon"]
        except:
            pass

    return DEFAULT_LAT, DEFAULT_LON


def get_weather():
    lat, lon = get_coords()

    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code&wind_speed_unit=ms"

    for attempt in range(1, WEATHER_RETRY_COUNT + 1):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.load(response)
                curr = data.get("current", {})
                temp = curr.get("temperature_2m", 0)
                cond = get_condition_text(curr.get("weather_code", 0))

                sign = "+" if temp > 0 else ""
                print(f"{sign}{temp:.0f}°c {cond}")
                return
        except Exception as e:
            log(f"Weather API Error (attempt {attempt}/{WEATHER_RETRY_COUNT}): {e}")
            if attempt < WEATHER_RETRY_COUNT:
                time.sleep(WEATHER_RETRY_DELAY_SEC)
            else:
                print("offline")


if __name__ == "__main__":
    get_weather()
