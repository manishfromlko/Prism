from src.retrieval.agents.hybrid import HybridAgent
from src.retrieval.agents.types import AgentContext


class StubRetriever:
    def __init__(self, hits):
        self.hits = hits
        self.calls = []

    def retrieve(self, query, top_k=3):
        self.calls.append((query, top_k))
        return self.hits


def test_hybrid_agent_searches_all_sources():
    doc_retriever = StubRetriever([{"doc_id": "d1", "source_file": "Guide.docx"}])
    artifact_retriever = StubRetriever([{"artifact_id": "etl.py", "user_id": "ravi.verma"}])
    user_retriever = StubRetriever([{"user_id": "ravi.verma", "tags": "Spark"}])
    agent = HybridAgent(doc_retriever, artifact_retriever, user_retriever)
    context = AgentContext(
        query="find spark docs and people",
        intent="HYBRID",
        confidence=0.8,
        search_query="spark docs people",
    )

    result = agent.run(context)

    assert result["intent"] == "HYBRID"
    assert result["sources"][0]["file"] == "Guide.docx"
    assert result["artifacts"][0]["title"] == "etl.py"
    assert result["users"][0]["name"] == "ravi.verma"
    assert doc_retriever.calls == [("spark docs people", 3)]
    assert artifact_retriever.calls == [("spark docs people", 3)]
    assert user_retriever.calls == [("spark docs people", 3)]
    assert any(step.action == "search_all_sources" for step in context.steps)


def test_hybrid_agent_handles_no_hits():
    agent = HybridAgent(StubRetriever([]), StubRetriever([]), StubRetriever([]))
    context = AgentContext(query="nothing here", intent="HYBRID", confidence=0.8)

    result = agent.run(context)

    assert result["answer"] == "I couldn't find relevant docs, artifacts, or people for this query."
    assert result["confidence"] == 0.65
