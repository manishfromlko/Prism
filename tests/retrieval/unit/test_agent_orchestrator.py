import importlib.util
import sys
import types as pytypes
from pathlib import Path


AGENTS_ROOT = Path(__file__).resolve().parents[3] / "src" / "retrieval" / "agents"


def load_module(name: str, path: Path, package: str | None = None):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if package:
        module.__package__ = package
    sys.modules[name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


sys.modules.setdefault("src", pytypes.ModuleType("src"))
sys.modules.setdefault("src.retrieval", pytypes.ModuleType("src.retrieval"))
sys.modules.setdefault("src.retrieval.agents", pytypes.ModuleType("src.retrieval.agents"))
sys.modules.setdefault("src.retrieval.chatbot", pytypes.ModuleType("src.retrieval.chatbot"))

engine_module = pytypes.ModuleType("src.retrieval.chatbot.engine")
engine_module.ChatEngine = object
sys.modules["src.retrieval.chatbot.engine"] = engine_module


class FakePeopleProfileAgent:
    def __init__(self, user_store, user_resolver):
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

    class classifier:
        @staticmethod
        def classify(query, trace_id=None):
            return {"intent": "USER_SEARCH", "confidence": 0.92}

    def chat(self, query, history, session_id=None):
        return {
            "answer": f"answer for {query}",
            "intent": "USER_SEARCH",
            "confidence": 1.0,
            "exact_match": True,
            "trace_id": "trace-1",
        }


def test_agent_context_records_steps():
    context = types.AgentContext(query="hello")

    context.add_step("orchestrator", "start", mode="test")

    assert context.steps[0].agent == "orchestrator"
    assert context.steps[0].details["mode"] == "test"


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
        "return_profile",
    ]
