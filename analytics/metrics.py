import os
import sqlite3
import time
from flask import request, has_request_context

DB_PATH = "logs/metrics.db"

def init_db():
    """Initializes the SQLite metrics database and creates the command_metrics table."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS command_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp REAL,
            query TEXT,
            detected_intent TEXT,
            confidence REAL,
            resolved_skill TEXT,
            success_status TEXT,
            llm_latency REAL,
            llm_tokens_used INTEGER,
            is_rag_query INTEGER
        )
    """)
    conn.commit()
    
    # Run migrations for existing DBs that do not have the Phase 3 columns
    try:
        cursor.execute("ALTER TABLE command_metrics ADD COLUMN llm_latency REAL")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE command_metrics ADD COLUMN llm_tokens_used INTEGER")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE command_metrics ADD COLUMN is_rag_query INTEGER")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def log_metric(query: str, detected_intent: str, confidence: float, resolved_skill: str, success_status: str,
               llm_latency: float = None, llm_tokens_used: int = None, is_rag_query: int = 0):
    """Logs a single command metric execution to the SQLite database."""
    session_id = "unknown"
    if has_request_context() and hasattr(request, 'sid') and request.sid:
        session_id = request.sid
        
    init_db()  # Ensure DB, table and columns exist
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO command_metrics (session_id, timestamp, query, detected_intent, confidence, resolved_skill, success_status, llm_latency, llm_tokens_used, is_rag_query)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (session_id, time.time(), query, detected_intent, confidence, resolved_skill, success_status, llm_latency, llm_tokens_used, is_rag_query))
    conn.commit()
    conn.close()

def get_intent_distribution():
    """Returns a dictionary mapping detected intents to their invocation count."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT detected_intent, COUNT(*) FROM command_metrics GROUP BY detected_intent")
    rows = cursor.fetchall()
    conn.close()
    return dict(rows)

def get_average_confidence():
    """Returns the average confidence score across all commands."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT AVG(confidence) FROM command_metrics")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] is not None else 0.0

def get_fallback_rate() -> float:
    """Returns the fraction of queries that fallback to LLM."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM command_metrics")
    total = cursor.fetchone()[0]
    if total == 0:
        conn.close()
        return 0.0
    cursor.execute("SELECT COUNT(*) FROM command_metrics WHERE success_status = 'FALLBACK'")
    fallback = cursor.fetchone()[0]
    conn.close()
    return fallback / total

def get_average_llm_latency() -> float:
    """Returns the average LLM latency in seconds."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT AVG(llm_latency) FROM command_metrics WHERE llm_latency IS NOT NULL")
    avg = cursor.fetchone()[0]
    conn.close()
    return avg if avg is not None else 0.0

def get_rag_query_count() -> int:
    """Returns the total number of RAG queries."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM command_metrics WHERE is_rag_query = 1")
    count = cursor.fetchone()[0]
    conn.close()
    return count
