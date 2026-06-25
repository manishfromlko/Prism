# Observability

The backend supports two tracing paths:

- MLflow for local/free tracing.
- LangSmith for optional hosted tracing.

## MLflow

Docker Compose starts MLflow at:

```text
http://localhost:5001
```

The backend container sends traces to:

```text
http://mlflow:5000
```

Relevant environment values:

```text
MLFLOW_TRACING=true
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_EXPERIMENT_NAME=rag-chatbot-legacy
```

## LangSmith

LangSmith is optional:

```text
LANGSMITH_TRACING=false
LANGCHAIN_TRACING_V2=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=rag-chatbot-legacy
```

Enable it only when you have credentials and want hosted traces.

