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


def test_orchestrator_delegates_to_legacy_engine():
    orchestrator = orchestrator_module.OrchestratorAgent(
        chat_engine=StubChatEngine(),
        max_steps=3,
        planner_enabled=False,
    )

    result = orchestrator.run("who is priya?", [{"role": "user", "content": "hi"}])

    assert result["answer"] == "answer for who is priya?"
    assert result["agent_mode"] == "orchestrated"
    assert [step["action"] for step in result["agent_steps"]] == [
        "start",
        "delegate_to_legacy_chat_engine",
    ]
