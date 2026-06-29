# Multi-Agent Architecture

This branch converts the assistant from an intent-routed RAG flow into an
orchestrated multi-agent runtime. The API response includes `agent_mode` and
`agent_steps`, so each answer can be inspected from the UI, logs, and tracing
backends.

## Runtime Diagram

```mermaid
flowchart TD
    user[User] --> ui[Next.js Chat UI]
    ui --> chat_api[FastAPI POST /chat]
    chat_api --> memory_store[(Conversation Memory<br/>Postgres or in-process)]
    chat_api --> orchestrator[OrchestratorAgent]

    orchestrator --> context[AgentContext<br/>query, history, trace_id, intent, evidence]
    orchestrator --> classifier[IntentClassifier]
    classifier --> route{Intent}

    route -->|GREETING / SELF_INTRO / CONVERSATION_MEMORY| memory[MemoryAgent]
    route -->|SYSTEM_STATS| metadata[MetadataAgent]
    route -->|USER_SEARCH| people[PeopleProfileAgent]
    route -->|DOC_QA| docs[DocsAgent]
    route -->|ARTIFACT_SEARCH| artifacts[ArtifactAgent]
    route -->|HYBRID| hybrid[HybridAgent]

    memory --> critic[CriticAgent]
    metadata --> critic
    people --> synthesis[SynthesisAgent]
    docs --> synthesis
    artifacts --> synthesis
    hybrid --> synthesis
    synthesis --> critic
    critic --> response[ChatResponse<br/>answer, intent, confidence, agent_steps]
    response --> ui

    metadata --> postgres[(Postgres<br/>workspace and artifact metadata)]
    people --> qdrant_users[(Qdrant<br/>user_profiles)]
    docs --> qdrant_docs[(Qdrant<br/>platform_docs)]
    artifacts --> qdrant_artifacts[(Qdrant<br/>artifact_summaries)]
    hybrid --> qdrant_users
    hybrid --> qdrant_docs
    hybrid --> qdrant_artifacts
    synthesis --> openai[OpenAI]
    orchestrator --> mlflow[MLflow traces]
    orchestrator --> langsmith[LangSmith optional]
```

## Agent Responsibilities

| Agent | Responsibility | Primary dependencies |
| --- | --- | --- |
| `OrchestratorAgent` | Creates turn context, classifies intent, routes to specialists, attaches `agent_steps`. | `ChatEngine` services, MLflow tracing |
| `MemoryAgent` | Handles greetings, assistant self-introduction, and current-conversation recap questions. | Conversation history |
| `MetadataAgent` | Answers system inventory questions such as workspace, artifact, notebook, and script counts. | Postgres metadata repository |
| `PeopleProfileAgent` | Resolves exact/similar user names, disambiguates profiles, and searches expertise semantically. | Qdrant `user_profiles`, user resolver |
| `DocsAgent` | Retrieves platform documentation and answers platform how-to questions. | Qdrant `platform_docs` |
| `ArtifactAgent` | Retrieves notebooks, scripts, and artifact summaries. | Qdrant `artifact_summaries` |
| `HybridAgent` | Searches docs, artifacts, and people together for mixed questions. | Qdrant docs/artifacts/users |
| `SynthesisAgent` | Produces grounded final prose from retrieved evidence. | OpenAI, prompt builders |
| `CriticAgent` | Reviews structured responses and lowers confidence for overconfident empty retrieval answers. | Structured response envelope |

## Turn Sequence

```mermaid
sequenceDiagram
    participant UI as Chat UI
    participant API as FastAPI /chat
    participant OR as OrchestratorAgent
    participant CL as IntentClassifier
    participant AG as Specialist Agent
    participant SY as SynthesisAgent
    participant CR as CriticAgent
    participant DB as Postgres/Qdrant

    UI->>API: query + session_id + optional history
    API->>API: merge stored and incoming history
    API->>OR: run(query, history, session_id)
    OR->>OR: create AgentContext
    OR->>CL: classify(query)
    CL-->>OR: intent + confidence
    OR->>AG: run(context)
    AG->>DB: retrieve or load metadata
    DB-->>AG: evidence
    AG->>SY: synthesize(context, evidence)
    SY-->>AG: answer
    AG-->>OR: AgentResult
    OR->>CR: review(context, result)
    CR-->>OR: reviewed response
    OR-->>API: response + agent_steps
    API->>API: persist conversation turn
    API-->>UI: ChatResponse
```

## Routing Rules

| Intent | Primary route |
| --- | --- |
| `GREETING` | `MemoryAgent` |
| `SELF_INTRO` | `MemoryAgent` |
| `CONVERSATION_MEMORY` | `MemoryAgent` |
| `SYSTEM_STATS` | `MetadataAgent` |
| `USER_SEARCH` | `PeopleProfileAgent`, then semantic people search when no name candidate exists |
| `DOC_QA` | `DocsAgent` |
| `ARTIFACT_SEARCH` | `ArtifactAgent` |
| `HYBRID` | `HybridAgent` |
| `OUT_OF_SCOPE` | Legacy fallback remains available through `ChatEngine` |

## Observability

Every orchestrated answer includes:

- `agent_mode`: currently `orchestrated`
- `agent_steps`: ordered list of agent actions, status, and details
- `trace_id`: request trace identifier

The frontend displays a compact `orchestrated • N steps` label under assistant
messages. Backend traces are also recorded through MLflow, with LangSmith
remaining optional.
