import wikipedia
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from cachetools import TTLCache
import threading

wiki_cache = TTLCache(maxsize=100, ttl=300)
cache_lock = threading.Lock()

# Set a custom user agent to avoid Wikimedia blocking requests
wikipedia.set_user_agent("JarvisAssistant/1.0 (contact@example.com)")

# Monkeypatch requests.get in the wikipedia library to enforce timeout=5 on internal calls
original_get = wikipedia.wikipedia.requests.get
def patched_get(*args, **kwargs):
    kwargs.setdefault('timeout', 5)
    return original_get(*args, **kwargs)
wikipedia.wikipedia.requests.get = patched_get

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True
)
def _fetch_wiki_api(query: str):
    return wikipedia.summary(query, sentences=2)

def fetch_wiki_summary(query: str):
    query_key = query.lower().strip()
    with cache_lock:
        if query_key in wiki_cache:
            return wiki_cache[query_key]

    summary = _fetch_wiki_api(query)

    with cache_lock:
        wiki_cache[query_key] = summary
    return summary
