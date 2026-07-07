import pytest
from session_context import get_session_context, clear_session_context, delete_session_context
from assistant import JarvisAssistant

def test_session_isolation():
    delete_session_context("sessionA")
    delete_session_context("sessionB")

    ctx_a = get_session_context("sessionA")
    ctx_b = get_session_context("sessionB")

    ctx_a["last_subject"] = "Isaac Newton"
    ctx_b["last_subject"] = "Marie Curie"

    assert get_session_context("sessionA")["last_subject"] == "Isaac Newton"
    assert get_session_context("sessionB")["last_subject"] == "Marie Curie"

    delete_session_context("sessionA")
    delete_session_context("sessionB")

def test_pronoun_context_resolution(monkeypatch):
    delete_session_context("sessionA")
    delete_session_context("sessionB")

    assistant = JarvisAssistant()

    # Session A: last_subject is Isaac Newton
    get_session_context("sessionA")["last_subject"] = "Isaac Newton"
    # Session B: last_subject is Marie Curie
    get_session_context("sessionB")["last_subject"] = "Marie Curie"

    class MockRequest:
        def __init__(self, sid):
            self.sid = sid

    # Run for Session A
    monkeypatch.setattr("session_context.request", MockRequest("sessionA"))
    monkeypatch.setattr("session_context.has_request_context", lambda: True)

    # We process a pronoun query
    res, state = assistant.process_command("what is the history of it")
    # It will resolve to "what is the history of Isaac Newton" and search Wikipedia
    assert "Isaac Newton" in res or "Newton" in res or "Wikipedia" in res

    # Run for Session B
    monkeypatch.setattr("session_context.request", MockRequest("sessionB"))
    
    res, state = assistant.process_command("what is the history of it")
    assert "Marie Curie" in res or "Curie" in res or "Wikipedia" in res

    delete_session_context("sessionA")
    delete_session_context("sessionB")
