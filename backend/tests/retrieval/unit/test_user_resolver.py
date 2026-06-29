from src.retrieval.chatbot.user_resolver import UserNameResolver


class StubUserStore:
    def get_all_user_ids(self):
        return []


def test_single_ambiguous_candidate_asks_confirmation_without_top_matches():
    resolver = UserNameResolver(StubUserStore())

    result = resolver.resolve(
        "what about aarav mehra?",
        candidates=[("aarav.mehra", 82.0)],
    )

    assert result["exact_uid"] is None
    assert result["confidence"] == 0.75
    assert result["answer"] == "I found one possible match: **aarav.mehra**. Are you asking about this person?"
    assert "Top Matches" not in result["answer"]


def test_multiple_ambiguous_candidates_asks_natural_clarification():
    resolver = UserNameResolver(StubUserStore())

    result = resolver.resolve(
        "what about aarav mehra?",
        candidates=[
            ("aarav.mehra", 100.0),
            ("aarav.mehraa", 95.0),
            ("aarav2.mehra", 94.0),
        ],
    )

    assert result["exact_uid"] is None
    assert result["confidence"] == 0.6
    assert result["answer"] == (
        "I found a few similar people: **aarav.mehra**, **aarav.mehraa**, "
        "or **aarav2.mehra**. Which one did you mean?"
    )
    assert "Top Matches" not in result["answer"]


def test_unambiguous_candidate_resolves_exactly():
    resolver = UserNameResolver(StubUserStore())

    result = resolver.resolve(
        "tell me about ravi verma",
        candidates=[("ravi.verma", 100.0)],
    )

    assert result == {"exact_uid": "ravi.verma", "answer": None, "confidence": 1.0}
