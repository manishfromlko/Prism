from src.retrieval.agents.docs import DocsAgent
from src.retrieval.agents.types import AgentContext


class StubDocRetriever:
    def __init__(self, hits):
        self.hits = hits
        self.calls = []

    def retrieve(self, query, top_k=5):
        self.calls.append((query, top_k))
        return self.hits


def test_docs_agent_returns_empty_answer_for_no_hits():
    retriever = StubDocRetriever([])
    agent = DocsAgent(doc_retriever=retriever)
    context = AgentContext(
        query="how do I submit a spark job",
        intent="DOC_QA",
        confidence=0.83,
        search_query="submit spark job",
    )

    result = agent.run(context)

    assert result["intent"] == "DOC_QA"
    assert result["answer"] == "I couldn't find relevant platform documentation for this question."
    assert retriever.calls == [("submit spark job", 5)]


def test_docs_agent_formats_sources_without_llm():
    agent = DocsAgent(
        doc_retriever=StubDocRetriever(
            [{"doc_id": "d1", "source_file": "Kubeflow_Spark_Job_Guide.docx"}]
        ),
    )
    context = AgentContext(
        query="how do I submit a spark job",
        intent="DOC_QA",
        confidence=0.8,
    )

    result = agent.run(context)

    assert result["answer"] == "Relevant platform documentation I found: Kubeflow_Spark_Job_Guide.docx."
    assert result["sources"][0]["file"] == "Kubeflow_Spark_Job_Guide.docx"
