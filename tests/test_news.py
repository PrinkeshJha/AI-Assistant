import pytest
import requests
from unittest.mock import Mock
from services.news_service import fetch_news, news_cache

def test_news_cache(monkeypatch):
    news_cache.clear()

    call_count = 0
    def mock_get(url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "articles": [{"title": "News Title 1"}]
        }
        return mock_resp

    monkeypatch.setattr(requests, "get", mock_get)

    # First fetch - increments call_count
    articles = fetch_news()
    assert len(articles) == 1
    assert articles[0]["title"] == "News Title 1"
    assert call_count == 1

    # Second fetch - hits cache
    articles = fetch_news()
    assert call_count == 1
