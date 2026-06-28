from src.retrieval.agents.people import PeopleProfileAgent
from src.retrieval.agents.types import AgentContext


class StubUserStore:
    def get_all_user_ids(self):
        return []


class StubUserResolver:
    pass


class StubUserRetriever:
    def __init__(self, hits):
        self.hits = hits
        self.calls = []

    def retrieve(self, query, top_k=5):
        self.calls.append((query, top_k))
        return self.hits


def test_people_agent_semantic_search_returns_empty_answer_without_legacy_fallback():
    retriever = StubUserRetriever([])
    agent = PeopleProfileAgent(
        user_store=StubUserStore(),
        user_resolver=StubUserResolver(),
        user_retriever=retriever,
    )
    context = AgentContext(
        query="tell me about people who work on natural language processing",
        intent="USER_SEARCH",
        confidence=0.9,
        search_query="natural language processing expertise",
    )

    result = agent.semantic_search(context)

    assert result["intent"] == "USER_SEARCH"
    assert result["answer"] == "I couldn't find any matching users for this query in the knowledge base."
    assert retriever.calls == [("natural language processing expertise", 5)]
    assert any(step.action == "semantic_people_search" for step in context.steps)


def test_people_agent_semantic_search_formats_user_hits():
    agent = PeopleProfileAgent(
        user_store=StubUserStore(),
        user_resolver=StubUserResolver(),
        user_retriever=StubUserRetriever(
            [{"user_id": "meera.iyer", "tags": "NLP, Python", "user_profile": "Works on NLP"}]
        ),
    )
    context = AgentContext(
        query="who works on natural language processing",
        intent="USER_SEARCH",
        confidence=0.8,
    )

    result = agent.semantic_search(context)

    assert result["answer"] == "Relevant people I found: meera.iyer."
    assert result["users"][0]["name"] == "meera.iyer"
