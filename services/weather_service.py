import requests
from config import OPENWEATHER_API_KEY
from tenacity import retry, stop_after_attempt, wait_exponential
from cachetools import TTLCache
import threading

weather_cache = TTLCache(maxsize=100, ttl=300)
cache_lock = threading.Lock()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True
)
def _fetch_weather_api(location: str):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={OPENWEATHER_API_KEY}&units=metric"
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    data = response.json()
    temp = data['main']['temp']
    desc = data['weather'][0]['description']
    return temp, desc

def fetch_weather(location: str):
    location_key = location.lower().strip()
    with cache_lock:
        if location_key in weather_cache:
            return weather_cache[location_key]

    temp, desc = _fetch_weather_api(location)

    with cache_lock:
        weather_cache[location_key] = (temp, desc)
    return temp, desc
