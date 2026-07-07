import os
import sqlite3
import pytest
from unittest.mock import patch, Mock
from assistant import JarvisAssistant
from session_context import get_session_context, delete_session_context, session_contexts
from analytics.metrics import DB_PATH, get_intent_distribution, get_average_confidence

def test_semantic_classification():
    assistant = JarvisAssistant()
    
    # "will it pour today" is semantic for WeatherSkill (forecast/rain)
    with patch("skills.weather_skill.fetch_weather") as mock_weather:
        mock_weather.return_value = (18.0, "heavy rain")
        res, state = assistant.process_command("will it pour in Seattle")
        assert "Seattle" in res
        assert "heavy rain" in res
        mock_weather.assert_called_once_with("Seattle")

def test_confidence_threshold_clarification():
    assistant = JarvisAssistant()
    
    # Query with low/competing similarity scores
    # We patch the classifier to return scores below 0.65 but above 0.3
    with patch.object(assistant.classifier, "classify") as mock_classify:
        mock_classify.return_value = {
            "WeatherSkill": 0.55,
            "WikiSkill": 0.45,
            "NewsSkill": 0.10
        }
        res, state = assistant.process_command("tell me something about the rain news")
        # Should ask a clarifying question naming the top 2-3 intents
        assert "I'm not sure. Did you mean" in res
        assert "WeatherSkill" in res
        assert "WikiSkill" in res
        assert "NewsSkill" not in res # NewsSkill is < 0.3
        assert state == "IDLE"

def test_confidence_fallback():
    assistant = JarvisAssistant()
    
    # Query with extremely low similarity score
    with patch.object(assistant.classifier, "classify") as mock_classify, \
         patch("services.llm_service.ask", return_value=("I'm not sure how to help with that yet.", 50, 0.2)) as mock_ask:
        mock_classify.return_value = {
            "WeatherSkill": 0.15,
            "WikiSkill": 0.10
        }
        res, state = assistant.process_command("xyz abc def")
        assert res == "I'm not sure how to help with that yet."
        assert state == "IDLE"
        mock_ask.assert_called_once()

def test_persistent_memory_across_reconnect():
    # Setup test session
    sid = "test_persist_session"
    delete_session_context(sid)
    
    # Connect/set context
    ctx = get_session_context(sid)
    ctx["last_city"] = "Munich"
    ctx["last_person"] = "Ada Lovelace"
    
    # Simulate a disconnection/reconnect by clearing Python's local session_contexts cache
    # But because it is backed by RedisStore, it will reload the values!
    session_contexts.pop(sid, None)
    
    ctx_reconnect = get_session_context(sid)
    assert ctx_reconnect["last_city"] == "Munich"
    assert ctx_reconnect["last_person"] == "Ada Lovelace"
    
    delete_session_context(sid)

def test_sqlite_metrics_logging():
    assistant = JarvisAssistant()
    
    # Remove database if exists to ensure clean run
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except PermissionError:
            pass
            
    with patch("skills.weather_skill.fetch_weather") as mock_weather:
        mock_weather.return_value = (20.0, "sunny")
        assistant.process_command("what is the weather in Munich")
        
    dist = get_intent_distribution()
    assert "WeatherSkill" in dist
    assert dist["WeatherSkill"] >= 1
    
    avg_conf = get_average_confidence()
    assert avg_conf > 0.0

def test_multi_turn_ellipsis_and_pronouns():
    assistant = JarvisAssistant()
    sid = "multi_turn_session"
    delete_session_context(sid)
    
    class MockRequest:
        def __init__(self, sid):
            self.sid = sid
            
    # Mock Flask request context
    with patch("session_context.request", MockRequest(sid)), \
         patch("session_context.has_request_context", return_value=True), \
         patch("analytics.metrics.has_request_context", return_value=True), \
         patch("analytics.metrics.request", MockRequest(sid)):
        
        # Turn 1: Weather in Munich
        with patch("skills.weather_skill.fetch_weather") as mock_weather:
            mock_weather.return_value = (20.0, "sunny")
            res, state = assistant.process_command("is it hot in Munich?")
            assert "Munich" in res
            assert "20.0" in res
            
        # Check context
        ctx = get_session_context(sid)
        assert ctx.get("last_city") == "Munich"
        
        # Turn 2: "and there?" (Resolving 'there' -> 'in Munich')
        with patch("skills.weather_skill.fetch_weather") as mock_weather:
            mock_weather.return_value = (20.0, "sunny")
            res, state = assistant.process_command("how is it there?")
            # "how is it there?" -> resolved "there" to "in Munich"
            # resolved "it" to "Munich"
            # final resolved query should contain Munich
            mock_weather.assert_called_with("Munich")
            
        # Turn 3: "what about Paris?" (Ellipsis fragment resolving to Weather in Paris)
        with patch("skills.weather_skill.fetch_weather") as mock_weather:
            mock_weather.return_value = (15.0, "windy")
            res, state = assistant.process_command("what about Paris?")
            # Should replace Munich with Paris and run WeatherSkill
            mock_weather.assert_called_with("Paris")
            assert "Paris" in res
            assert "15.0" in res

    delete_session_context(sid)

def test_skill_execution_failure():
    assistant = JarvisAssistant()
    
    # Force TimeSkill to fail
    with patch("skills.time_skill.TimeSkill.handle", side_effect=Exception("Simulated skill crash")):
        res, state = assistant.process_command("what time is it")
        assert res == "Sorry, I encountered an error while processing that request."
        assert state == "IDLE"
