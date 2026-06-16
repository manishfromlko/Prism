# Data Flows

## Ingestion Flow

```mermaid
flowchart LR
    root["dataset/"] --> list["List workspace directories"]
    list --> scan["Recursive file scan"]
    scan --> classify["classify_file guardrails"]
    classify --> supported{"Supported extension?"}
    supported -- no --> skip["Skip unsupported"]
    supported -- yes --> changed{"Full run or changed hash?"}
    changed -- unchanged incremental --> mark["Mark unchanged"]
    changed -- new/updated --> extract["Notebook/script/text extraction"]
    extract --> audit{"Guard skipped?"}
    audit -- yes --> auditFile["ingestion_audit.json"]
    audit -- no --> catalog["ingestion_catalog.json"]
```

Supported extensions are `.ipynb`, `.py`, `.scala`, `.sql`, `.txt`, and `.md`.

## Artifact Indexing Flow

```mermaid
flowchart LR
    catalog["ingestion_catalog.json"] --> loader["DocumentLoader"]
    loader --> chunks["LangChain documents"]
    chunks --> mode{"Mode"}
    mode -- full --> drop["Drop/recreate collection"]
    mode -- incremental --> existing["Read existing artifact_ids"]
    existing --> filter["Only new artifact_ids"]
    drop --> embed["EmbeddingService"]
    filter --> embed
    embed --> milvus[(kubeflow_artifacts)]
```

Full mode rebuilds the artifact collection. Incremental mode skips already indexed `artifact_id` values.

## Summary and Profile Flow

```mermaid
flowchart TB
    catalog["ingestion_catalog.json"] --> summaryGen["Artifact summary generator"]
    summaryGen --> llm["LLM gpt-4o-mini"]
    llm --> summaryStore[(artifact_summaries)]
    summaryStore --> profileGen["Profile from summaries indexer"]
    profileGen --> profileLLM["LLM gpt-4o-mini"]
    profileLLM --> profileStore[(user_profiles)]
```

Artifact summaries are the preferred source for user profile generation because they compress raw files into higher-signal user activity descriptions.

## Platform Docs Flow

```mermaid
flowchart LR
    docx["platform_documents/*.docx"] --> parse["python-docx text extraction"]
    parse --> split["800-char chunks, 150-char overlap"]
    split --> embed["EmbeddingService"]
    embed --> docs[(platform_docs)]
```

The chatbot uses `platform_docs` for `DOC_QA` intent.

## Search Request Flow

```mermaid
sequenceDiagram
    actor User
    participant UI as Web UI
    participant Next as webapp/app/api/search/route.ts
    participant API as POST /query
    participant Embed as EmbeddingService
    participant Store as kubeflow_artifacts

    User->>UI: Enter search query
    UI->>Next: POST /api/search
    Next->>API: POST /query
    API->>Embed: Generate query embedding
    Embed-->>API: Query vector
    API->>Store: Similarity search
    Store-->>API: Top K artifact chunks
    API-->>Next: QueryResponse
    Next-->>UI: SearchResult-shaped data
```

## Chatbot Flow

```mermaid
flowchart TB
    query["User query"] --> classify["IntentClassifier"]
    classify --> out{"OUT_OF_SCOPE?"}
    out -- yes --> hardcoded["Return scoped guidance"]
    out -- no --> rewrite["QueryRewriter"]
    rewrite --> intent{"Intent"}
    intent -- DOC_QA --> docs["DocRetriever: platform_docs"]
    intent -- ARTIFACT_SEARCH --> artifacts["ArtifactRetriever: artifact_summaries"]
    intent -- USER_SEARCH --> names["RapidFuzz name resolver"]
    names --> exact{"Exact user?"}
    exact -- yes --> rawProfile["Return stored profile"]
    exact -- no --> users["UserRetriever: user_profiles"]
    intent -- HYBRID --> hybrid["Retrieve docs + artifacts + users"]
    docs --> prompt["Build prompt"]
    artifacts --> prompt
    users --> prompt
    hybrid --> prompt
    prompt --> generate["LLM generation through LiteLLM-compatible client"]
    generate --> format["Format response with artifacts/users/sources"]
    format --> score["Heuristic scores + background evaluation"]
```

## Admin Refresh Flow

```mermaid
sequenceDiagram
    actor Operator
    participant API as FastAPI admin endpoint
    participant Worker as Thread executor
    participant Milvus
    participant Cache as In-memory services

    Operator->>API: POST /admin/sync
    API->>Worker: run_indexing(mode)
    Worker->>Milvus: Insert new vectors
    Worker-->>API: inserted/skipped counts
    API->>Cache: Refresh catalog loader
    API-->>Operator: SyncResponse
```

Admin endpoints run batch work in a thread so the FastAPI event loop is not blocked.

## Observability Flow

```mermaid
flowchart LR
    chat["Chat request"] --> trace["trace_id generated"]
    trace --> classify["classify LLM call"]
    trace --> rewrite["rewrite LLM call"]
    trace --> generate["generate LLM call"]
    generate --> l1["Layer 1 heuristic scores"]
    generate --> l2["Layer 2 background eval"]
    l1 --> langfuse["Langfuse trace scores"]
    l2 --> langfuse
    feedback["Frontend feedback"] --> obsApi["/observability/feedback"]
    obsApi --> langfuse
```
