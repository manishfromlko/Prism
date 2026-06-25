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
