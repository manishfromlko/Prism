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

profiling_module = pytypes.ModuleType("src.retrieval.profiling")
profiling_module.WorkspaceProfiler = object
sys.modules["src.retrieval.profiling"] = profiling_module

load_module(
    "src.retrieval.agents.types",
    AGENTS_ROOT / "types.py",
    package="src.retrieval.agents",
)
tools = load_module(
    "src.retrieval.agents.tools",
    AGENTS_ROOT / "tools.py",
    package="src.retrieval.agents",
)


class StubRetriever:
    def __init__(self, items):
        self.items = items
        self.calls = []

    def retrieve(self, query, top_k=5):
        self.calls.append((query, top_k))
        return self.items[:top_k]


class StubProfiler:
    def profile_workspace(self, workspace_id):
        return {"workspace_id": workspace_id, "artifact_count": 2}


def test_search_artifacts_returns_typed_tool_result():
    toolbelt = tools.RetrievalToolbelt(
        doc_retriever=StubRetriever([]),
        artifact_retriever=StubRetriever([{"id": "a"}, {"id": "b"}]),
        user_retriever=StubRetriever([]),
    )

    result = toolbelt.search_artifacts("spark", top_k=4)

    assert result.tool_name == "search_artifacts"
    assert len(result.items) == 2
    assert result.confidence == 0.5
    assert result.metadata == {"query": "spark", "top_k": 4}


def test_get_workspace_profile_uses_profiler():
    toolbelt = tools.RetrievalToolbelt(
        doc_retriever=StubRetriever([]),
        artifact_retriever=StubRetriever([]),
        user_retriever=StubRetriever([]),
        profiler=StubProfiler(),
    )

    result = toolbelt.get_workspace_profile("priya2.patel")

    assert result.tool_name == "get_workspace_profile"
    assert result.confidence == 1.0
    assert result.items[0]["workspace_id"] == "priya2.patel"
