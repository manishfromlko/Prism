from src.retrieval.agents.synthesis import SynthesisAgent
from src.retrieval.agents.types import AgentContext


def test_synthesis_agent_returns_empty_answer_without_evidence():
    context = AgentContext(query="anything")
    agent = SynthesisAgent()

    answer = agent.synthesize(
        context,
        evidence=[],
        prompt_builder=lambda evidence, query: [],
        fallback_builder=lambda evidence: "fallback",
        empty_answer="nothing found",
    )

    assert answer == "nothing found"
    assert context.steps[-1].agent == "synthesis"
    assert context.steps[-1].action == "empty_answer"


def test_synthesis_agent_uses_fallback_without_llm_client():
    context = AgentContext(query="find people")
    agent = SynthesisAgent()

    answer = agent.synthesize(
        context,
        evidence=[{"user_id": "ravi.verma"}],
        prompt_builder=lambda evidence, query: [],
        fallback_builder=lambda evidence: evidence[0]["user_id"],
        empty_answer="nothing found",
    )

    assert answer == "ravi.verma"
    assert context.steps[-1].action == "fallback_answer"
