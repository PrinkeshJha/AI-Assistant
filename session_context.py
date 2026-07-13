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
        if has_request_context():
            from flask import session
            # 1. Try JWT identity (REST API routes)
            try:
                from flask_jwt_extended import get_jwt_identity, has_jwt_context
                if has_jwt_context():
                    identity = get_jwt_identity()
                    if identity:
                        sid = f"user_{identity}"
            except Exception:
                pass
            
            # 2. Try socket session user_id
            if sid is None:
                try:
                    if session and 'user_id' in session:
                        sid = f"user_{session['user_id']}"
                except Exception:
                    pass
            
            # 3. Fallback to raw socket request.sid
            if sid is None:
                if hasattr(request, 'sid') and request.sid:
                    sid = request.sid
                    
        if sid is None:
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
        if has_request_context():
            from flask import session
            # Try JWT identity
            try:
                from flask_jwt_extended import get_jwt_identity, has_jwt_context
                if has_jwt_context():
                    identity = get_jwt_identity()
                    if identity:
                        sid = f"user_{identity}"
            except Exception:
                pass
                
            # Try Socket session
            if sid is None:
                try:
                    if session and 'user_id' in session:
                        sid = f"user_{session['user_id']}"
                except Exception:
                    pass
                    
            # Fallback to request.sid
            if sid is None:
                if hasattr(request, 'sid') and request.sid:
                    sid = request.sid
        if sid is None:
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

