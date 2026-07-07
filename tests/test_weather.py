import pytest
import requests
from unittest.mock import Mock
from services.weather_service import fetch_weather, weather_cache

def test_weather_cache(monkeypatch):
    weather_cache.clear()

    call_count = 0
    def mock_get(url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "main": {"temp": 25.5},
            "weather": [{"description": "clear sky"}]
        }
        return mock_resp

    monkeypatch.setattr(requests, "get", mock_get)

    # First fetch - should increment call_count
    temp, desc = fetch_weather("Berlin")
    assert temp == 25.5
    assert desc == "clear sky"
    assert call_count == 1

    # Second fetch - should hit cache, no call_count increment
    temp, desc = fetch_weather("Berlin")
    assert temp == 25.5
    assert call_count == 1

    # Fetching different city - should call API
    temp, desc = fetch_weather("Paris")
    assert call_count == 2

def test_weather_retry(monkeypatch):
    weather_cache.clear()

    call_count = 0
    def mock_get(url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise requests.RequestException("Unreachable API")
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "main": {"temp": 15.0},
            "weather": [{"description": "foggy"}]
        }
        return mock_resp

    monkeypatch.setattr(requests, "get", mock_get)

    # Hamburg - succeeds on 3rd try
    temp, desc = fetch_weather("Hamburg")
    assert temp == 15.0
    assert call_count == 3

def test_weather_llm_collaboration(monkeypatch):
    from assistant import JarvisAssistant
    from unittest.mock import patch
    assistant = JarvisAssistant()
    
    monkeypatch.setattr("config.LLM_FORMAT_SKILLS", True)
    
    with patch("skills.weather_skill.fetch_weather", return_value=(20.0, "sunny")), \
         patch("services.llm_service.ask", return_value=("It is 20 degrees and sunny in Munich, Sir.", 35, 0.1)) as mock_ask:
        
        with patch.object(assistant.classifier, "classify", return_value={"WeatherSkill": 0.9}):
            res, state = assistant.process_command("what is the weather in Munich")
            assert "It is 20 degrees and sunny in Munich, Sir." in res
            assert state == "IDLE"
            mock_ask.assert_called_once()
