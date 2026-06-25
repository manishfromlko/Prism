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
