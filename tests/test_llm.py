import pytest
from unittest.mock import patch, MagicMock
from services import llm_service

def test_llm_ask_success():
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = "This is a mock answer from Jarvis."
    mock_completion.usage.total_tokens = 42
    mock_client.chat.completions.create.return_value = mock_completion
    
    with patch("services.llm_service.get_client", return_value=mock_client):
        res, tokens, latency = llm_service.ask("Explain quantum computing")
        assert res == "This is a mock answer from Jarvis."
        assert tokens == 42
        assert latency >= 0
        mock_client.chat.completions.create.assert_called_once()

def test_llm_summarize_history():
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = "Summary: User and Jarvis spoke."
    mock_client.chat.completions.create.return_value = mock_completion
    
    history = [{"query": "hello", "response": "hi"}]
    with patch("services.llm_service.get_client", return_value=mock_client):
        summary = llm_service.summarize_history(history)
        assert "Summary" in summary
        mock_client.chat.completions.create.assert_called_once()

def test_assistant_fallback_to_llm():
    from assistant import JarvisAssistant
    assistant = JarvisAssistant()
    
    # Mock classifier to trigger fallback (confidence < 0.65, no suggestions)
    with patch.object(assistant.classifier, "classify", return_value={"WikiSkill": 0.1}), \
         patch("services.llm_service.ask", return_value=("This is the LLM answer.", 50, 0.2)) as mock_ask:
        
        res, state = assistant.process_command("Explain quantum computing")
        assert res == "This is the LLM answer."
        assert state == "IDLE"
        mock_ask.assert_called_once_with("Explain quantum computing", [], None)

def test_assistant_summarizes_history():
    from assistant import JarvisAssistant
    from unittest.mock import patch, MagicMock
    from session_context import get_session_context
    
    assistant = JarvisAssistant()
    ctx = get_session_context("summarize_test_session")
    ctx["history"] = [
        {"query": f"Query {i}", "response": f"Response {i}", "intent": "SomeSkill", "entities": []}
        for i in range(4)
    ]
    
    with patch("session_context.has_request_context", return_value=True), \
         patch("session_context.request", MagicMock(sid="summarize_test_session")), \
         patch("services.llm_service.summarize_history", return_value="Condensed: user query loop.") as mock_sum, \
         patch("skills.weather_skill.fetch_weather", return_value=(20.0, "sunny")):
        
        with patch.object(assistant.classifier, "classify", return_value={"WeatherSkill": 0.9}):
            res, state = assistant.process_command("what is the weather in Munich")
            mock_sum.assert_called_once()
            assert ctx.get("summary") == "Condensed: user query loop."
            assert len(ctx.get("history")) == 1

def test_analytics_metrics_logging():
    from assistant import JarvisAssistant
    from unittest.mock import patch, MagicMock
    from analytics.metrics import get_fallback_rate, get_average_llm_latency, get_rag_query_count, DB_PATH
    import os
    
    # Remove database if exists to ensure clean run
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except PermissionError:
            pass
            
    assistant = JarvisAssistant()
    
    class MockRequest:
        def __init__(self, sid):
            self.sid = sid
            
    with patch("session_context.has_request_context", return_value=True), \
         patch("session_context.request", MockRequest("test_analytics_session")), \
         patch("analytics.metrics.has_request_context", return_value=True), \
         patch("analytics.metrics.request", MockRequest("test_analytics_session")):
         
        # Fallback query
        with patch.object(assistant.classifier, "classify", return_value={"WikiSkill": 0.1}), \
             patch("services.llm_service.ask", return_value=("This is the LLM answer.", 50, 0.2)):
            assistant.process_command("Explain quantum computing")
            
        # RAG query
        mock_store = MagicMock()
        mock_store.index.ntotal = 1
        with patch("skills.rag_skill.SessionVectorStore", return_value=mock_store), \
             patch.object(assistant.classifier, "classify", return_value={"RAGSkill": 0.9}), \
             patch("skills.rag_skill.retrieve_context", return_value=["LR Parsing is bottom-up parsing."]), \
             patch("services.llm_service.ask", return_value=("LR Parsing is bottom-up.", 30, 0.1)):
            assistant.process_command("explain LR parsing from my notes")
        
    fallback_rate = get_fallback_rate()
    avg_latency = get_average_llm_latency()
    rag_count = get_rag_query_count()
    
    assert fallback_rate == 0.5
    assert avg_latency == pytest.approx(0.15)
    assert rag_count == 1
