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
MLFLOW_EXPERIMENT_NAME=rag-chatbot-legacy-agent-traces
MLFLOW_ARTIFACT_LOCATION=mlflow-artifacts:/
```

### Verifying Agent Traces

After sending a chat request, open:

```text
http://localhost:5001
```

Select experiment `rag-chatbot-legacy-agent-traces`, then open the latest
`chat_pipeline` run. For orchestrated chat turns, the run includes:

- tag `agent_mode`, usually `orchestrated`
- tag `agent_path`, for example `orchestrator.start -> memory.pass -> ...`
- tag `conversation_id`, matching the chat `session_id`
- metric `agent_step_count`
- a trace span graph with one child span per agent step
- artifact `agent_trace.json` with the full ordered `agent_steps` payload
- artifact `chat_response_summary.json` with the answer preview and retrieval counts

The `agent_trace.json` artifact is the canonical MLflow record for which agents
ran, which actions they took, and the details captured for each step.

To see all turns for one conversation, filter runs or traces by:

```text
tags.conversation_id = '<session_id>'
```

Each chat turn is still stored as its own MLflow run/trace so latency, intent,
retrieval counts, and agent path stay turn-specific. The shared
`conversation_id`/`session_id` tags are the grouping key.

Older local runs may exist under experiment `rag-chatbot-legacy`. That
experiment used a container-local artifact path before proxied artifacts were
enabled, so use `rag-chatbot-legacy-agent-traces` for full agent trace
artifacts.

## LangSmith

LangSmith is optional:

```text
LANGSMITH_TRACING=false
LANGCHAIN_TRACING_V2=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=rag-chatbot-legacy
```

Enable it only when you have credentials and want hosted traces.
