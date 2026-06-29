import importlib.util
from pathlib import Path


MLFLOW_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "observability"
    / "mlflow_tracing.py"
)
spec = importlib.util.spec_from_file_location("mlflow_tracing", MLFLOW_PATH)
mlflow_tracing = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mlflow_tracing)


def test_mlflow_disabled_without_tracking_uri(monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACING", "true")
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)

    assert mlflow_tracing.is_mlflow_enabled() is False


def test_mlflow_chat_trace_noops_when_disabled(monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACING", "false")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")

    with mlflow_tracing.mlflow_chat_trace("hello", [], "session-1") as span:
        assert span is None


class FakeSpan:
    def __init__(self):
        self.attributes = {}
        self.outputs = {}

    def set_attributes(self, attributes):
        self.attributes.update(attributes)

    def set_outputs(self, outputs):
        self.outputs.update(outputs)


class FakeMlflow:
    def __init__(self):
        self.tags = {}
        self.metrics = {}
        self.artifacts = {}

    def set_tag(self, key, value):
        self.tags[key] = value

    def log_metric(self, key, value):
        self.metrics[key] = value

    def log_dict(self, payload, artifact_file):
        self.artifacts[artifact_file] = payload


def test_record_mlflow_chat_output_logs_agent_trace(monkeypatch):
    fake_mlflow = FakeMlflow()
    monkeypatch.setattr(mlflow_tracing, "mlflow", fake_mlflow)
    monkeypatch.setattr(mlflow_tracing, "_MLFLOW_AVAILABLE", True)
    monkeypatch.setenv("MLFLOW_TRACING", "true")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    span = FakeSpan()

    mlflow_tracing.record_mlflow_chat_output(
        span,
        {
            "trace_id": "trace-1",
            "intent": "USER_SEARCH",
            "confidence": 0.65,
            "exact_match": False,
            "answer": "No users found",
            "artifacts": [],
            "users": [],
            "sources": [],
            "agent_mode": "orchestrated",
            "agent_steps": [
                {"agent": "orchestrator", "action": "start", "status": "completed", "details": {}},
                {"agent": "people_profile", "action": "semantic_people_search", "status": "completed", "details": {"hit_count": 0}},
                {"agent": "critic", "action": "lower_confidence", "status": "completed", "details": {}},
            ],
        },
    )

    assert fake_mlflow.tags["agent_mode"] == "orchestrated"
    assert "people_profile.semantic_people_search" in fake_mlflow.tags["agent_path"]
    assert fake_mlflow.metrics["agent_step_count"] == 3.0
    assert fake_mlflow.artifacts["agent_trace.json"]["agent_steps"][1]["agent"] == "people_profile"
    assert span.attributes["agent_step_count"] == 3
    assert span.outputs["agent_steps"][2]["action"] == "lower_confidence"
