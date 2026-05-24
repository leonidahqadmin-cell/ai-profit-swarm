import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """Create tables if they don't exist"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Table 1: Cycle history
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cycle_logs (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT NOW(),
            summary TEXT,
            details JSONB,
            metrics JSONB
        )
    """)
    
    # Table 2: Simple persistent swarm memory (key-value)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS swarm_state (
            key TEXT PRIMARY KEY,
            value JSONB,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database tables initialized")

def log_cycle(summary: str, details: dict = None, metrics: dict = None):
    """Log one full cycle"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO cycle_logs (summary, details, metrics)
        VALUES (%s, %s, %s)
    """, (summary, json.dumps(details or {}), json.dumps(metrics or {})))
    conn.commit()
    cur.close()
    conn.close()

def set_state(key: str, value):
    """Save something to persistent memory"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO swarm_state (key, value, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (key) DO UPDATE 
        SET value = EXCLUDED.value, updated_at = NOW()
    """, (key, json.dumps(value)))
    conn.commit()
    cur.close()
    conn.close()

def get_state(key: str, default=None):
    """Load something from persistent memory"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT value FROM swarm_state WHERE key = %s", (key,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return row["value"]
    return default

def get_recent_cycles(limit: int = 10):
    """
    Return the most recent N cycle_logs rows as a list of dicts.
    Used by the self-improvement loop to analyze recent performance.
    Returns [] if there's nothing to read.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT id, timestamp, summary, details, metrics
        FROM cycle_logs
        ORDER BY timestamp DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    # Convert timestamps to ISO strings so the result is JSON-safe
    result = []
    for r in rows:
        result.append({
            "id":        r["id"],
            "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
            "summary":   r["summary"],
            "details":   r["details"] or {},
            "metrics":   r["metrics"] or {},
        })
    return result
