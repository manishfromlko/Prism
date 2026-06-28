from src.retrieval.agents.artifacts import ArtifactAgent
from src.retrieval.agents.types import AgentContext


class StubArtifactRetriever:
    def __init__(self, hits):
        self.hits = hits
        self.calls = []

    def retrieve(self, query, top_k=5):
        self.calls.append((query, top_k))
        return self.hits


def test_artifact_agent_returns_empty_answer_for_no_hits():
    retriever = StubArtifactRetriever([])
    agent = ArtifactAgent(artifact_retriever=retriever)
    context = AgentContext(
        query="find spark notebooks",
        intent="ARTIFACT_SEARCH",
        confidence=0.82,
        search_query="spark notebooks",
    )

    result = agent.run(context)

    assert result["intent"] == "ARTIFACT_SEARCH"
    assert result["answer"] == "I couldn't find matching notebooks, scripts, or artifacts for this query."
    assert retriever.calls == [("spark notebooks", 5)]
    assert any(step.action == "search_artifacts" for step in context.steps)


def test_artifact_agent_formats_hits_without_llm():
    agent = ArtifactAgent(
        artifact_retriever=StubArtifactRetriever(
            [{"artifact_id": "etl/orders.py", "user_id": "ravi.verma"}]
        ),
    )
    context = AgentContext(
        query="find order ETL",
        intent="ARTIFACT_SEARCH",
        confidence=0.8,
    )

    result = agent.run(context)

    assert result["answer"] == "Relevant artifacts I found: etl/orders.py."
    assert result["artifacts"][0]["title"] == "etl/orders.py"
    assert result["artifacts"][0]["owner"] == "ravi.verma"
