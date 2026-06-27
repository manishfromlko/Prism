import importlib.util
from pathlib import Path


MEMORY_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "retrieval"
    / "chatbot"
    / "memory.py"
)
spec = importlib.util.spec_from_file_location("chatbot_memory", MEMORY_PATH)
memory = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(memory)


def test_resolves_exact_user_id_with_digits_without_history():
    user_ids = ["priya.patel", "priya2.patel", "priyam.patel"]

    assert memory.resolve_user_from_context("priya2.patel", [], user_ids) == "priya2.patel"


def test_resolves_user_selection_from_previous_disambiguation():
    user_ids = ["priya.patel", "priya2.patel", "priyam.patel"]
    history = [
        {
            "role": "assistant",
            "content": (
                "Top Matches:\n"
                "1. priya2.patel\n"
                "2. priya.patel\n"
                "3. priyam.patel\n\n"
                "Follow-up Question:\n"
                "Are you looking for a specific Priya?"
            ),
        }
    ]

    assert memory.resolve_user_from_context("priya2.patel", history, user_ids) == "priya2.patel"


def test_resolves_contextual_followup_from_recent_profile():
    user_ids = ["priya.patel", "priya2.patel", "priyam.patel"]
    history = [
        {
            "role": "assistant",
            "content": "**priya2.patel**\n\nPriya works on model monitoring and Spark ETL.",
        }
    ]

    assert memory.resolve_user_from_context("what projects is she working on?", history, user_ids) == "priya2.patel"


def test_broad_people_search_does_not_reuse_recent_profile_user():
    user_ids = ["ravi.verma", "zoya.khan"]
    history = [
        {"role": "user", "content": "Who is ravi verma"},
        {"role": "assistant", "content": "**ravi.verma**\n\nRavi works on ETL."},
    ]

    assert (
        memory.resolve_user_from_context(
            "tell me about people who work on natural language processing?",
            history,
            user_ids,
        )
        is None
    )


def test_detects_greeting_and_conversation_memory_query():
    assert memory.is_greeting("Hi")
    assert memory.is_self_intro_query("tell me about yourself")
    assert memory.is_system_stats_query("How many workspaces exist in the system?")
    assert memory.is_conversation_memory_query("What questions I asked till now?")
    assert not memory.is_conversation_memory_query("tell me about ravi.verma")


def test_answers_conversation_memory_query_from_history():
    history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hi! How can I help?"},
        {"role": "user", "content": "tell me about ravi.verma?"},
        {"role": "assistant", "content": "Ravi Verma works on PySpark ETL."},
    ]

    answer = memory.answer_conversation_memory_query(
        "What questions I asked till now?",
        history,
    )

    assert "1. Hi" in answer
    assert "2. tell me about ravi.verma?" in answer
    assert "3. What questions I asked till now?" in answer
    assert "ravi.verma" in answer
