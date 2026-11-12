"""Private, account-scoped long-term memory for Sambot X.

Only explicitly saved memories are stored. Every operation requires a valid
Sambot billing/email session token; records are isolated by verified email.
"""
import os
import sqlite3
import time
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from billing import _email_from_token

router = APIRouter(prefix="/api/memory", tags=["memory"])
DB_PATH = os.getenv("BILLING_DB_PATH", "/var/data/sambot_billing.sqlite3")
MAX_ITEMS = 100

def _connect():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS user_memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        UNIQUE(email, content)
    )""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_user_memories_email ON user_memories(email, id DESC)")
    return con

def _owner(authorization):
    if not authorization:
        raise HTTPException(401, "Sign in to use private long-term memory.")
    return _email_from_token(authorization)

class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)

@router.get("")
def list_memories(authorization: str | None = Header(default=None)):
    email = _owner(authorization)
    con = _connect()
    try:
        rows = con.execute(
            "SELECT id, content, created_at FROM user_memories WHERE email=? ORDER BY id DESC LIMIT ?",
            (email, MAX_ITEMS),
        ).fetchall()
        return {"memories": [dict(row) for row in rows], "limit": MAX_ITEMS}
    finally:
        con.close()

@router.post("")
def save_memory(body: MemoryCreate, authorization: str | None = Header(default=None)):
    email = _owner(authorization)
    content = " ".join(body.content.split())
    if not content:
        raise HTTPException(400, "Memory cannot be empty.")
    con = _connect()
    try:
        count = con.execute("SELECT COUNT(*) AS n FROM user_memories WHERE email=?", (email,)).fetchone()["n"]
        existing = con.execute(
            "SELECT id FROM user_memories WHERE email=? AND content=?", (email, content)
        ).fetchone()
        if existing:
            return {"ok": True, "id": existing["id"], "duplicate": True}
        if count >= MAX_ITEMS:
            raise HTTPException(409, "Memory is full. Delete an old item before saving another.")
        cur = con.execute(
            "INSERT INTO user_memories(email, content, created_at) VALUES(?,?,?)",
            (email, content, int(time.time())),
        )
        con.commit()
        return {"ok": True, "id": cur.lastrowid, "duplicate": False}
    finally:
        con.close()

@router.delete("/{memory_id}")
def delete_memory(memory_id: int, authorization: str | None = Header(default=None)):
    email = _owner(authorization)
    con = _connect()
    try:
        cur = con.execute("DELETE FROM user_memories WHERE id=? AND email=?", (memory_id, email))
        con.commit()
        if not cur.rowcount:
            raise HTTPException(404, "Memory not found.")
        return {"ok": True}
    finally:
        con.close()

@router.delete("")
def clear_memories(authorization: str | None = Header(default=None)):
    email = _owner(authorization)
    con = _connect()
    try:
        con.execute("DELETE FROM user_memories WHERE email=?", (email,))
        con.commit()
        return {"ok": True}
    finally:
        con.close()

def get_memory_context(authorization: str | None, limit: int = 30) -> str:
    """Return only this signed-in account's explicitly saved facts."""
    if not authorization:
        return ""
    email = _email_from_token(authorization)
    con = _connect()
    try:
        rows = con.execute(
            "SELECT content FROM user_memories WHERE email=? ORDER BY id DESC LIMIT ?",
            (email, max(1, min(limit, 50))),
        ).fetchall()
        return "\n".join("- " + row["content"] for row in reversed(rows))
    finally:
        con.close()
