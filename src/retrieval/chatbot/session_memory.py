"""In-process conversation memory keyed by frontend session ID."""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from typing import Dict, List, Optional


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
