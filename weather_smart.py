#!/usr/bin/env python3
import json
import urllib.request
import urllib.error
import sys
import os
import time
import subprocess

# --- НАСТРОЙКИ ---
# Включает подробный вывод в терминал для проверки
DEBUG = False

# Автоматическое определение города (True/False)
AUTO_DETECT = False

# Координаты по умолчанию, используются если AUTO_DETECT = False
DEFAULT_LAT = "55.75"
DEFAULT_LON = "37.61"

CACHE_FILE = os.path.expanduser("./weather_location.json")
VPN_INTERFACES = ["tun", "wg", "ppp", "proton"]


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


def is_gnome_proxy_active():
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.system.proxy", "mode"],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip().replace("'", "") != "none":
            log("GNOME Proxy detected")
            return True
    except:
        pass
    return False


def is_vpn_interface_active():
    try:
        if os.path.exists("/sys/class/net/"):
            for iface in os.listdir("/sys/class/net/"):
                for key in VPN_INTERFACES:
                    if key in iface:
                        with open(f"/sys/class/net/{iface}/operstate", "r") as f:
                            if f.read().strip() != "down":
                                log(f"VPN Interface detected: {iface}")
                                return True
    except:
        pass
    return False


def get_location_from_ip():
    log("Requesting IP location...")
    try:
        url = "http://ip-api.com/json/"
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.load(response)
            if data["status"] == "success":
                log(f"API returned: {data.get('city')}")
                return str(data["lat"]), str(data["lon"]), data.get("city", "Unknown")
    except Exception as e:
        log(f"API Error: {e}")
    return None


def update_location_cache():
    if not AUTO_DETECT:
        return

    if is_gnome_proxy_active() or is_vpn_interface_active():
        log("VPN active. Skipping update.")
        return

    loc_data = get_location_from_ip()
    if loc_data:
        lat, lon, city = loc_data
        try:
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump(
                    {"lat": lat, "lon": lon, "city": city, "timestamp": time.time()}, f
                )
            log("Cache updated")
        except:
            pass


def get_coords():
    if not AUTO_DETECT:
        log(f"Auto-detect OFF. Using default: {DEFAULT_LAT}, {DEFAULT_LON}")
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

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.load(response)
            curr = data.get("current", {})
            temp = curr.get("temperature_2m", 0)
            cond = get_condition_text(curr.get("weather_code", 0))

            sign = "+" if temp > 0 else ""
            print(f"{sign}{temp:.0f}°c {cond}")

    except Exception as e:
        log(f"Weather Error: {e}")
        print("offline")


if __name__ == "__main__":
    get_weather()
