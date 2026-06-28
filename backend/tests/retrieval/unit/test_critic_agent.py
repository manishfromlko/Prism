from src.retrieval.agents.critic import CriticAgent
from src.retrieval.agents.types import AgentContext


def test_critic_lowers_confidence_for_overconfident_empty_retrieval_answer():
    context = AgentContext(query="who works on NLP")
    result = {
        "answer": "I couldn't find any matching users for this query in the knowledge base.",
        "intent": "USER_SEARCH",
        "confidence": 0.9,
        "artifacts": [],
        "users": [],
        "sources": [],
    }

    reviewed = CriticAgent().review(context, result)

    assert reviewed["confidence"] == 0.65
    assert context.steps[-1].action == "lower_confidence"


def test_critic_approves_grounded_retrieval_answer():
    context = AgentContext(query="who is ravi")
    result = {
        "answer": "**ravi.verma**",
        "intent": "USER_SEARCH",
        "confidence": 1.0,
        "artifacts": [],
        "users": [{"name": "ravi.verma"}],
        "sources": [],
    }

    reviewed = CriticAgent().review(context, result)

    assert reviewed["confidence"] == 1.0
    assert context.steps[-1].action == "approve"
