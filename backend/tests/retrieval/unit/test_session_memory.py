import importlib.util
from pathlib import Path


MEMORY_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "retrieval"
    / "chatbot"
    / "session_memory.py"
)
spec = importlib.util.spec_from_file_location("session_memory", MEMORY_PATH)
session_memory = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(session_memory)


def test_remembers_turns_by_session_id():
    store = session_memory.ConversationMemoryStore(max_sessions=20, max_messages=4)

    store.remember_turn("session-1", "who is priya?", "Top Matches:\n1. priya2.patel")

    assert store.get("session-1") == [
        {"role": "user", "content": "who is priya?"},
        {"role": "assistant", "content": "Top Matches:\n1. priya2.patel"},
    ]
    assert store.get("other-session") == []


def test_lists_and_deletes_saved_conversations():
    store = session_memory.ConversationMemoryStore(max_sessions=2, max_messages=4)

    store.remember_turn("session-1", "first question", "first answer")
    store.remember_turn("session-2", "second question", "second answer")
    store.remember_turn("session-3", "third question", "third answer")

    conversations = store.list_conversations()

    assert [row["session_id"] for row in conversations] == ["session-3", "session-2"]
    assert conversations[0]["title"] == "third question"
    assert store.get("session-1") == []
    assert store.delete_conversation("session-2") is True
    assert store.get_conversation("session-2") is None


def test_merges_stored_and_incoming_history_without_duplicates():
    stored = [
        {"role": "user", "content": "who is priya?"},
        {"role": "assistant", "content": "Top Matches:\n1. priya2.patel"},
    ]
    incoming = [
        {"role": "assistant", "content": "Top Matches:\n1. priya2.patel"},
        {"role": "user", "content": "priya2.patel"},
    ]

    assert session_memory.ConversationMemoryStore.merge(stored, incoming) == [
        {"role": "user", "content": "who is priya?"},
        {"role": "assistant", "content": "Top Matches:\n1. priya2.patel"},
        {"role": "user", "content": "priya2.patel"},
    ]
