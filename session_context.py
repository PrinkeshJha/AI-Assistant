import threading
from flask import request, has_request_context
from memory.redis_store import RedisStore

# Thread-safe context storage backed by Redis/local fallback
store = RedisStore()
session_contexts = {}
context_lock = threading.Lock()

def get_session_context(sid=None):
    """
    Returns the session context dictionary for the current request.sid or the provided sid.
    Falls back to a default empty dictionary if request context is not present.
    """
    if sid is None:
        if has_request_context() and hasattr(request, 'sid') and request.sid:
            sid = request.sid
        else:
            # Fallback mock context for non-request contexts (like CLI or pytest)
            return {}
            
    with context_lock:
        if sid not in session_contexts:
            session_contexts[sid] = store.get_context(sid)
        return session_contexts[sid]

def clear_session_context(sid=None):
    """
    Clears the session context dictionary for the current request.sid or the provided sid.
    """
    if sid is None:
        if has_request_context() and hasattr(request, 'sid') and request.sid:
            sid = request.sid
        else:
            return
            
    with context_lock:
        if sid in session_contexts:
            session_contexts[sid].clear()
        else:
            store.clear_context(sid)

def delete_session_context(sid):
    """
    Deletes the session context entry for the given sid to prevent memory leaks.
    """
    with context_lock:
        if sid in session_contexts:
            del session_contexts[sid]
        store.delete_context(sid)
