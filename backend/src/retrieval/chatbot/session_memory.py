"""Conversation memory keyed by frontend session ID."""

from __future__ import annotations

import os
from collections import OrderedDict
from contextlib import contextmanager
from datetime import datetime
from threading import Lock
from typing import Any, Dict, Iterator, List, Optional

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - optional for unit tests without Postgres
    psycopg = None
    dict_row = None


class ConversationMemoryStore:
    """Small bounded store for recent chat turns.

    This is intentionally process-local: it gives the agent continuity in the
    running demo stack without introducing a database dependency. The frontend
    owns the stable session ID, and the backend keeps recent turns per session.
    """

    def __init__(self, max_sessions: int = 200, max_messages: int = 20):
        self.max_sessions = max_sessions
        self.max_messages = max_messages
        self._sessions: OrderedDict[str, List[Dict[str, str]]] = OrderedDict()
        self._lock = Lock()

    def get(self, session_id: Optional[str]) -> List[Dict[str, str]]:
        if not session_id:
            return []
        with self._lock:
            messages = list(self._sessions.get(session_id, []))
            if session_id in self._sessions:
                self._sessions.move_to_end(session_id)
            return messages

    def remember_turn(self, session_id: Optional[str], query: str, answer: str) -> None:
        if not session_id:
            return
        with self._lock:
            messages = self._sessions.setdefault(session_id, [])
            messages.extend(
                [
                    {"role": "user", "content": query},
                    {"role": "assistant", "content": answer},
                ]
            )
            del messages[:-self.max_messages]
            self._sessions.move_to_end(session_id)
            while len(self._sessions) > self.max_sessions:
                self._sessions.popitem(last=False)

    def list_conversations(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        limit = limit or self.max_sessions
        with self._lock:
            rows: List[Dict[str, Any]] = []
            for session_id, messages in reversed(self._sessions.items()):
                first_user_message = next(
                    (message["content"] for message in messages if message.get("role") == "user"),
                    "New conversation",
                )
                rows.append(
                    {
                        "session_id": session_id,
                        "title": first_user_message.replace("\n", " ")[:80],
                        "created_at": None,
                        "updated_at": None,
                        "message_count": len(messages),
                    }
                )
                if len(rows) >= limit:
                    break
            return rows

    def get_conversation(self, session_id: str) -> Optional[Dict[str, Any]]:
        messages = self.get(session_id)
        if not messages:
            return None
        title = next(
            (message["content"] for message in messages if message.get("role") == "user"),
            "New conversation",
        )
        return {
            "session_id": session_id,
            "title": title.replace("\n", " ")[:80],
            "created_at": None,
            "updated_at": None,
            "messages": messages,
        }

    def delete_conversation(self, session_id: str) -> bool:
        with self._lock:
            existed = session_id in self._sessions
            self._sessions.pop(session_id, None)
            return existed

    @staticmethod
    def merge(
        stored: List[Dict[str, str]],
        incoming: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """Merge stored and client-provided history while avoiding duplicates."""
        merged: List[Dict[str, str]] = []
        seen = set()
        for message in [*stored, *incoming]:
            role = message.get("role")
            content = message.get("content")
            if role not in {"user", "assistant"} or not content:
                continue
            key = (role, content)
            if key in seen:
                continue
            seen.add(key)
            merged.append({"role": role, "content": content})
        return merged


def _iso(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class PostgresConversationMemoryStore:
    """Durable conversation memory stored in Postgres.

    The store keeps the latest ``max_conversations`` conversations by
    ``updated_at``. Messages remain scoped to their conversation session ID.
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        max_conversations: int = 20,
        max_messages_per_conversation: int = 100,
    ):
        self.database_url = database_url or os.getenv("METADATA_DATABASE_URL")
        if not self.database_url:
            raise ValueError("METADATA_DATABASE_URL is not configured")
        if psycopg is None:
            raise RuntimeError("psycopg is required for durable conversation memory")
        self.max_conversations = max_conversations
        self.max_messages_per_conversation = max_messages_per_conversation

    @classmethod
    def from_env(cls) -> Optional["PostgresConversationMemoryStore"]:
        database_url = os.getenv("METADATA_DATABASE_URL")
        return cls(database_url) if database_url else None

    @contextmanager
    def connect(self) -> Iterator[Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            yield conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    message_id BIGSERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES conversations(session_id)
                        ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversation_messages_session_id ON conversation_messages(session_id, message_id)"
            )
            conn.commit()

    def get(self, session_id: Optional[str]) -> List[Dict[str, str]]:
        if not session_id:
            return []
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content
                FROM conversation_messages
                WHERE session_id = %s
                ORDER BY message_id ASC
                """,
                (session_id,),
            ).fetchall()
            return [{"role": row["role"], "content": row["content"]} for row in rows]

    def remember_turn(self, session_id: Optional[str], query: str, answer: str) -> None:
        if not session_id:
            return

        title = query.strip().replace("\n", " ")[:80] or "New conversation"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO conversations (session_id, title)
                VALUES (%s, %s)
                ON CONFLICT (session_id) DO UPDATE SET updated_at = now()
                """,
                (session_id, title),
            )
            conn.execute(
                """
                INSERT INTO conversation_messages (session_id, role, content)
                VALUES (%s, 'user', %s), (%s, 'assistant', %s)
                """,
                (session_id, query, session_id, answer),
            )
            self._prune_messages(conn, session_id)
            self._prune_conversations(conn)
            conn.commit()

    def list_conversations(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        limit = limit or self.max_conversations
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT c.session_id, c.title, c.created_at, c.updated_at,
                       COUNT(m.message_id)::int AS message_count
                FROM conversations c
                LEFT JOIN conversation_messages m ON m.session_id = c.session_id
                GROUP BY c.session_id, c.title, c.created_at, c.updated_at
                ORDER BY c.updated_at DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
            return [
                {
                    "session_id": row["session_id"],
                    "title": row["title"],
                    "created_at": _iso(row["created_at"]),
                    "updated_at": _iso(row["updated_at"]),
                    "message_count": row["message_count"],
                }
                for row in rows
            ]

    def get_conversation(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT session_id, title, created_at, updated_at
                FROM conversations
                WHERE session_id = %s
                """,
                (session_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "session_id": row["session_id"],
                "title": row["title"],
                "created_at": _iso(row["created_at"]),
                "updated_at": _iso(row["updated_at"]),
                "messages": self.get(session_id),
            }

    def delete_conversation(self, session_id: str) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM conversations WHERE session_id = %s",
                (session_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def _prune_messages(self, conn: Any, session_id: str) -> None:
        conn.execute(
            """
            DELETE FROM conversation_messages
            WHERE session_id = %s
              AND message_id NOT IN (
                  SELECT message_id
                  FROM conversation_messages
                  WHERE session_id = %s
                  ORDER BY message_id DESC
                  LIMIT %s
              )
            """,
            (session_id, session_id, self.max_messages_per_conversation),
        )

    def _prune_conversations(self, conn: Any) -> None:
        conn.execute(
            """
            DELETE FROM conversations
            WHERE session_id NOT IN (
                SELECT session_id
                FROM conversations
                ORDER BY updated_at DESC
                LIMIT %s
            )
            """,
            (self.max_conversations,),
        )
