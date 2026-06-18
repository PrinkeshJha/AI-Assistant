import pytest
from unittest.mock import patch
from assistant import JarvisAssistant

def test_intent_dispatching():
    assistant = JarvisAssistant()

    # Test weather dispatching
    with patch("skills.weather_skill.fetch_weather") as mock_weather:
        mock_weather.return_value = (22.0, "cloudy")
        res, state = assistant.process_command("what is the weather of Paris")
        assert "weather in Paris" in res or "temperature" in res or "22.0" in res
        mock_weather.assert_called_once_with("Paris")

    # Test news headlines dispatching
    with patch("skills.news_skill.fetch_news") as mock_news:
        mock_news.return_value = [{"title": "Major event occurs"}]
        res, state = assistant.process_command("tell me the news headlines")
        assert "Major event occurs" in res
        mock_news.assert_called_once()

    # Test Wikipedia dispatching
    with patch("skills.wiki_skill.fetch_wiki_summary") as mock_wiki:
        mock_wiki.return_value = "Albert Einstein was a physicist."
        res, state = assistant.process_command("search for Albert Einstein")
        assert "Albert Einstein was a physicist" in res
        mock_wiki.assert_called_once_with("albert einstein")
