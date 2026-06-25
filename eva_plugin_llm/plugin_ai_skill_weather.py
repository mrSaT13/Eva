"""
LLM инструмент для получения погоды.
"""

from logging import getLogger
from typing import Optional, Annotated

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from eva import VAApiExt
from eva.plugin_loader.magic_plugin import operation

name = 'ai_skill_weather'
version = '0.1.0'

_logger = getLogger(name)


async def init(*_args, **_kwargs):
    pass


@operation('lc_tools')
@tool(parse_docstring=True)
def get_weather(
        city: str,
        run_config: RunnableConfig,
) -> str:
    """
    Get current weather for a city.
    Use this tool when user asks about weather, temperature, or climate.

    Args:
        city: name of the city (in Russian or English)
        run_config:
    """
    va: VAApiExt = run_config['configurable']['eva_va_api']

    try:
        import httpx
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            res = client.get(f"https://wttr.in/{city}?format=j1&lang=ru",
                           headers={"User-Agent": "Eva/1.0"})
            if res.status_code == 200:
                data = res.json()
                current = data.get("current_condition", [{}])[0]
                temp = current.get("temp_C", "?")
                desc_list = current.get("weatherDesc", [{}])
                desc = desc_list[0].get("value", "?") if desc_list else "?"
                humidity = current.get("humidity", "?")
                wind = current.get("windspeedKmph", "?")
                feels = current.get("FeelsLikeC", "?")
                return f"Погода в {city}: {desc}, {temp}°C, ощущается как {feels}°C. Влажность {humidity}%, ветер {wind} км/ч."
    except Exception as e:
        _logger.warning("Weather API error: %s", e)

    try:
        import urllib.request
        import json
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        with urllib.request.urlopen(geo_url, timeout=5) as resp:
            geo_data = json.loads(resp.read())
            if geo_data.get("results"):
                lat = geo_data["results"][0]["latitude"]
                lon = geo_data["results"][0]["longitude"]
                url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                with urllib.request.urlopen(url, timeout=5) as resp2:
                    data = json.loads(resp2.read())
                    cw = data.get("current_weather", {})
                    temp = cw.get("temperature", "?")
                    wind = cw.get("windspeed", "?")
                    code = cw.get("weathercode", 0)
                    wmo = {0: "ясно", 1: "малооблачно", 2: "облачно", 3: "пасмурно",
                           45: "туман", 51: "морось", 61: "дождь", 71: "снег", 95: "гроза"}
                    desc = wmo.get(code, f"код {code}")
                    return f"Погода в {city}: {desc}, {temp}°C, ветер {wind} км/ч."
    except Exception as e:
        _logger.warning("Open-Meteo error: %s", e)

    return f"Не удалось получить погоду для {city}"
