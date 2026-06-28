import importlib.util
import os
import sys
import types as pytypes
from contextlib import contextmanager
from pathlib import Path


os.environ["MLFLOW_TRACING"] = "false"

AGENTS_ROOT = Path(__file__).resolve().parents[3] / "src" / "retrieval" / "agents"
SRC_ROOT = Path(__file__).resolve().parents[3] / "src"


def load_module(name: str, path: Path, package: str | None = None):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if package:
        module.__package__ = package
    sys.modules[name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


src_module = sys.modules.setdefault("src", pytypes.ModuleType("src"))
src_module.__path__ = [str(SRC_ROOT)]
retrieval_module = sys.modules.setdefault("src.retrieval", pytypes.ModuleType("src.retrieval"))
retrieval_module.__path__ = [str(SRC_ROOT / "retrieval")]
agents_module = sys.modules.setdefault("src.retrieval.agents", pytypes.ModuleType("src.retrieval.agents"))
agents_module.__path__ = [str(SRC_ROOT / "retrieval" / "agents")]
chatbot_module = sys.modules.setdefault("src.retrieval.chatbot", pytypes.ModuleType("src.retrieval.chatbot"))
chatbot_module.__path__ = [str(SRC_ROOT / "retrieval" / "chatbot")]

observability_module = pytypes.ModuleType("src.observability")


@contextmanager
def noop_trace(*args, **kwargs):
    yield None


observability_module.is_langsmith_enabled = lambda: False
observability_module.make_llm_client = lambda *args, **kwargs: None
observability_module.mlflow_chat_trace = noop_trace
observability_module.record_mlflow_chat_output = lambda *args, **kwargs: None
observability_module.trace_extra_body = lambda *args, **kwargs: {}
observability_module.evaluate_in_background = lambda *args, **kwargs: None
sys.modules["src.observability"] = observability_module

engine_module = pytypes.ModuleType("src.retrieval.chatbot.engine")
engine_module.ChatEngine = object
sys.modules["src.retrieval.chatbot.engine"] = engine_module


class FakePeopleProfileAgent:
    def __init__(self, user_store, user_resolver, **kwargs):
        self.user_store = user_store
        self.user_resolver = user_resolver

    def run(self, context):
        context.add_step("people_profile", "return_profile", user_id="priya2.patel")
        return {
            "answer": "**priya2.patel**\n\nProfile",
            "intent": "USER_SEARCH",
            "confidence": 1.0,
            "exact_match": True,
        }

    def semantic_search(self, context):
        context.add_step("people_profile", "semantic_people_search", hit_count=0)
        return None


people_module = pytypes.ModuleType("src.retrieval.agents.people")
people_module.PeopleProfileAgent = FakePeopleProfileAgent
sys.modules["src.retrieval.agents.people"] = people_module

types = load_module(
    "src.retrieval.agents.types",
    AGENTS_ROOT / "types.py",
    package="src.retrieval.agents",
)
orchestrator_module = load_module(
    "src.retrieval.agents.orchestrator",
    AGENTS_ROOT / "orchestrator.py",
    package="src.retrieval.agents",
)


class StubChatEngine:
    user_store = object()
    user_resolver = object()
    metadata_repository = None
    user_retriever = object()
    artifact_retriever = object()
    doc_retriever = object()
    client = None
    llm_model = "gpt-4o-mini"

    class rewriter:
        @staticmethod
        def rewrite(query, trace_id=None):
            return query

    class classifier:
        @staticmethod
        def classify(query, trace_id=None):
            if query == "tell me about yourself":
                return {"intent": "SELF_INTRO", "confidence": 0.99}
            if query == "How many workspaces exist in the system?":
                return {"intent": "SYSTEM_STATS", "confidence": 0.99}
            return {"intent": "USER_SEARCH", "confidence": 0.92}

    def chat(self, query, history, session_id=None):
        return {
            "answer": f"answer for {query}",
            "intent": "USER_SEARCH",
            "confidence": 1.0,
            "exact_match": True,
            "trace_id": "trace-1",
        }


class StubMetadataRepository:
    enabled = True

    def list_workspaces(self):
        return [{"workspace_id": "a"}, {"workspace_id": "b"}]

    def list_artifacts(self):
        return [
            {"file_type": "notebook"},
            {"file_type": "script"},
            {"file_type": "script"},
        ]


def test_agent_context_records_steps():
    context = types.AgentContext(query="hello")

    context.add_step("orchestrator", "start", mode="test")

    assert context.steps[0].agent == "orchestrator"
    assert context.steps[0].details["mode"] == "test"


def test_agent_result_formats_canonical_response():
    result = types.AgentResult(
        answer="Found Priya",
        intent="USER_SEARCH",
        confidence=0.91,
        exact_match=True,
        raw_users=[{"user_id": "priya.patel", "tags": "Python, NLP"}],
    )

    response = result.to_response()

    assert response["answer"] == "Found Priya"
    assert response["intent"] == "USER_SEARCH"
    assert response["confidence"] == 0.91
    assert response["exact_match"] is True
    assert response["users"][0]["name"] == "priya.patel"


def test_orchestrator_routes_user_search_to_people_agent():
    orchestrator = orchestrator_module.OrchestratorAgent(
        chat_engine=StubChatEngine(),
        max_steps=3,
        planner_enabled=False,
    )

    result = orchestrator.run("who is priya?", [{"role": "user", "content": "hi"}])

    assert result["answer"].startswith("**priya2.patel**")
    assert result["agent_mode"] == "orchestrated"
    assert [step["action"] for step in result["agent_steps"]] == [
        "start",
        "classify_intent",
        "pass",
        "pass",
        "return_profile",
        "approve",
    ]


def test_orchestrator_routes_memory_turn_to_memory_agent():
    orchestrator = orchestrator_module.OrchestratorAgent(
        chat_engine=StubChatEngine(),
        max_steps=3,
        planner_enabled=False,
    )

    result = orchestrator.run("tell me about yourself", [])

    assert result["intent"] == "SELF_INTRO"
    assert result["agent_mode"] == "orchestrated"
    assert [step["action"] for step in result["agent_steps"]] == [
        "start",
        "classify_intent",
        "answer_self_intro",
        "skip",
    ]


def test_orchestrator_routes_system_stats_to_metadata_agent():
    chat_engine = StubChatEngine()
    chat_engine.metadata_repository = StubMetadataRepository()
    orchestrator = orchestrator_module.OrchestratorAgent(
        chat_engine=chat_engine,
        max_steps=3,
        planner_enabled=False,
    )

    result = orchestrator.run("How many workspaces exist in the system?", [])

    assert result["intent"] == "SYSTEM_STATS"
    assert result["answer"] == "There are 2 workspaces currently indexed in the system."
    assert [step["action"] for step in result["agent_steps"]] == [
        "start",
        "classify_intent",
        "pass",
        "load_system_metadata",
        "skip",
    ]
