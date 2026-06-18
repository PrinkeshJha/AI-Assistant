import requests
from config import NEWS_API_KEY
from tenacity import retry, stop_after_attempt, wait_exponential
from cachetools import TTLCache
import threading

news_cache = TTLCache(maxsize=10, ttl=300)
cache_lock = threading.Lock()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True
)
def _fetch_news_api():
    url = f"https://gnews.io/api/v4/top-headlines?language=en&country=in&category=general&apikey={NEWS_API_KEY}"
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    data = response.json()
    articles = data.get('articles', [])
    return articles

def fetch_news():
    cache_key = 'headlines'
    with cache_lock:
        if cache_key in news_cache:
            return news_cache[cache_key]

    articles = _fetch_news_api()

    with cache_lock:
        news_cache[cache_key] = articles
    return articles
