# Kubeflow Workspace Intelligence LLMOps Deck v4

Interview-ready presentation content generated from the current codebase.

Source of truth used:
- `README.md`
- `src/ingestion/*`
- `src/retrieval/*`
- `src/retrieval/chatbot/*`
- `src/observability/*`
- `docs/observability/layer2-testing.md`
- `rag_observability_overview.md`
- `dataset/.ingestion/ingestion_catalog.json`

Accuracy note:
- The checked-in ingestion catalog currently contains 5 workspaces and 211 artifacts: 132 notebooks, 75 scripts, and 4 text files.
- The prompt mentions approximately 250 notebooks. Present that as an expandable target size, not the current checked-in snapshot.

---

## Slide 1: Title

### Content
- **Kubeflow Workspace Intelligence**
- RAG-based chatbot with LLMOps observability and evaluation
- Production-style assistant for workspace knowledge, notebook discovery, platform docs QA, and user expertise profiling
- FastAPI | Next.js | Milvus | LiteLLM | Langfuse | RAGAS

### Speaker Notes
Frame this as a production-style LLMOps system, not a generic chatbot wrapper. The project connects ingestion, retrieval, generation, tracing, and evaluation into one inspectable workflow for data scientists and ML engineers.

### Diagram
Title slide uses a clean stack tagline rather than a detailed diagram.

---

## Slide 2: Problem

### Content
- Kubeflow workspaces become knowledge silos as notebooks and scripts grow
- Filename search misses ML intent: tools, models, datasets, techniques
- Teams need grounded answers, expertise discovery, and operational visibility

### Speaker Notes
The problem is discovery plus trust. Notebooks hold institutional memory, but that memory is hard to query by filename and hard to evaluate once an LLM is involved. A usable enterprise assistant needs retrieval grounding, traceability, and quality checks.

---

## Slide 3: Solution Overview

### Content
- Intent-routed RAG assistant over platform docs, artifact summaries, and user profiles
- Semantic retrieval backed by OpenAI embeddings and Milvus collections
- LiteLLM and Langfuse provide request-level visibility across classify, rewrite, and generate
- RAGAS and LLM-as-judge evaluate groundedness and relevance after the answer returns

### Speaker Notes
The system separates knowledge surfaces instead of putting everything into one mixed index. Platform docs answer how-to questions, artifact summaries power notebook/script discovery, and user profiles support expertise search.

---

## Slide 4: Dataset and Ingestion Scope

### Content
- Current checked-in catalog: 5 workspaces, 211 artifacts
- Artifact mix: 132 notebooks, 75 scripts, 4 text files
- CSV, binary, archive, and unsupported files are excluded from semantic indexing
- Full and incremental ingestion use content hashes to control reprocessing cost

### Speaker Notes
The current catalog is smaller than the prompt’s approximate dataset size. In an interview, be precise: the repo snapshot has 132 notebooks and the architecture can scale to a larger corpus. The exclusion of raw datasets is intentional because the goal is to understand work patterns and artifact intent, not embed raw tabular data.

---

## Slide 5: Core Capabilities

### Content
- Workspace browsing and profiling
- Notebook/script semantic search
- LLM-generated artifact summaries and user profiles
- Platform documentation QA from Word documents
- Assistant with intent routing, query rewriting, sources, feedback, and trace IDs

### Speaker Notes
The implementation goes beyond the initial prompt. In addition to notebook search and profiling, it supports platform-doc QA, hybrid routing, user resolution, feedback scoring, and admin sync endpoints.

---

## Slide 6: High-Level Architecture

### Content
- Next.js acts as a BFF and proxies to FastAPI
- FastAPI orchestrates search, chat, sync, metrics, and feedback
- Milvus stores separate knowledge collections
- LiteLLM and Langfuse make LLM calls observable

### Speaker Notes
Walk left to right: users access the Next.js UI; server-side routes call FastAPI; FastAPI orchestrates ingestion-backed retrieval, chat routing, LLM generation, tracing, and scoring. The diagram should make clear that the UI, API, knowledge layer, and LLMOps layer are separate concerns.

### Diagram
Native PowerPoint architecture diagram plus Mermaid source:
- `presentation/v4/high-level-architecture-v4.mmd`

Diagram structure:
- Request path: Users -> Next.js BFF -> FastAPI Retrieval API -> ChatEngine -> Response + trace_id
- Knowledge layer: `kubeflow_artifacts`, `artifact_summaries`, `user_profiles`, `platform_docs`
- LLMOps layer: LiteLLM -> model provider, Langfuse traces/scores, RAGAS/LLM judge

---

## Slide 7: Data Flow: Offline Build and Online Serving

### Content
- Offline path builds catalog, summaries, profiles, document chunks, and vector indexes
- Online path classifies the query, retrieves context, generates an answer, and returns trace_id
- Evaluation path posts quality scores to the same Langfuse trace asynchronously

### Speaker Notes
Use this slide to show that RAG has two lifecycles. Offline jobs create and refresh the knowledge layer. Online serving uses that layer to answer user questions. The observability path follows the online request and then posts delayed quality scores after the answer returns.

### Diagram
Native PowerPoint data-flow diagram plus Mermaid source:
- `presentation/v4/data-flow-v4.mmd`

Diagram structure:
- Offline build: Workspace files -> ingestion catalog -> parse/chunk -> embeddings -> Milvus collections -> summaries/profiles/docs
- Online serving: User query -> classify/rewrite -> retrieve context -> prompt/generate -> answer + sources + trace_id
- Evaluation: response/context -> RAGAS or LLM judge -> Langfuse scores

---

## Slide 8: Ingestion and Indexing Pipeline

### Content
- Scan workspace directories and classify supported files
- Extract notebook/script metadata: tools, table references, database targets
- Convert artifacts into LangChain documents and extract notebook cell text
- Chunk by content type, embed with `text-embedding-3-small`, and upsert to Milvus

### Speaker Notes
The ingestion phase creates the structured catalog. The retrieval indexer then loads that catalog, extracts notebook cell content, applies guardrails, chunks documents by type, generates embeddings, and inserts vectors into Milvus. Incremental indexing avoids re-embedding unchanged artifacts.

---

## Slide 9: Retrieval Surfaces

### Content
- `kubeflow_artifacts`: raw artifact chunks for semantic artifact search
- `artifact_summaries`: concise notebook/script descriptions and tags
- `user_profiles`: generated expertise summaries by workspace owner
- `platform_docs`: chunks extracted from platform Word documents

### Speaker Notes
Separate collections improve retrieval precision and prompt clarity. The tradeoff is that multiple stores must be built and refreshed. That is why the project includes admin endpoints for artifact summaries, profiles, and doc ingestion.

---

## Slide 10: Chatbot Runtime Flow

### Content
- One trace_id groups classify, rewrite, retrieve, generate, and scoring
- Intent decides which store is queried and which prompt is built
- USER_SEARCH uses exact/candidate name resolution before semantic retrieval
- Scores and feedback are attached to the same Langfuse trace

### Speaker Notes
This is the core interview architecture slide. Emphasize that query classification controls retrieval, cost, prompt shape, and failure handling. The trace ID is propagated through LiteLLM metadata so Langfuse groups related model calls under one request.

### Diagram
Native PowerPoint runtime-flow diagram plus Mermaid source:
- `presentation/v4/chatbot-runtime-flow-v4.mmd`

Diagram structure:
- Query + trace_id -> IntentClassifier -> QueryRewriter -> RoutedRetriever -> PromptBuilder -> LiteLLM Generate -> Formatted Response
- USER_SEARCH branch: candidate resolution -> exact profile fetch / disambiguation / semantic fallback
- Observability branch: Layer 1 heuristic scores + Layer 2 RAGAS/LLM judge -> Langfuse trace

---

## Slide 11: Intent Routing

### Content
- DOC_QA routes to `platform_docs`
- ARTIFACT_SEARCH routes to `artifact_summaries`
- USER_SEARCH routes to direct profile lookup or `user_profiles`
- HYBRID retrieves from docs, artifacts, and profiles
- OUT_OF_SCOPE returns a bounded response instead of general model knowledge

### Speaker Notes
The classifier returns intent and confidence. Failure falls back to DOC_QA with low confidence, which is conservative compared with generating ungrounded workspace facts. OUT_OF_SCOPE is a hallucination-control mechanism.

---

## Slide 12: LLM Orchestration with LiteLLM

### Content
- All chat calls use an OpenAI-compatible client pointed at LiteLLM
- Generation defaults to `gpt-4o-mini` for cost-sensitive interaction
- Evaluation and judge paths use `gpt-4o` for stronger scoring reliability
- Trace metadata groups multi-step calls under one Langfuse request

### Speaker Notes
LiteLLM centralizes model routing, provider configuration, token/cost tracking, and Langfuse callbacks. This keeps application code provider-agnostic while preserving observability.

---

## Slide 13: Layer 1 Observability

### Content
- LiteLLM forwards prompts, responses, latency, cost, tokens, and errors to Langfuse
- Application posts `response_length`, `has_content`, `intent_confidence`, and `source_count`
- The trace_id is returned so frontend feedback can attach to the same trace

### Speaker Notes
Layer 1 tells us what happened operationally: latency, cost, token use, prompt/response, errors, and lightweight response health signals. These are not semantic quality metrics, but they are useful for debugging and cost control.

---

## Slide 14: Layer 2 RAG Evaluation

### Content
- Runs after the response in a background thread
- RAGAS metrics: faithfulness, answer_relevancy, context_precision
- Exact USER_SEARCH uses LLM judge score: profile_relevance
- Scores are posted back to the same Langfuse trace

### Speaker Notes
Layer 2 tells us whether the answer was good and grounded. It is asynchronous so RAGAS does not add user-facing latency. Exact people lookups use a different evaluator because direct profile retrieval is not the same shape as normal RAG generation.

---

## Slide 15: Evaluation Interpretation

### Content
- Low faithfulness means answer claims are unsupported by retrieved context
- Low answer_relevancy means the answer missed the user question
- Low context_precision means retrieval returned weak or poorly ranked context
- Low profile_relevance means people-search output did not match the ask

### Speaker Notes
These metrics are diagnostic. Low context precision points to retriever/chunking/index issues. Low faithfulness points to prompt grounding or generation behavior. Low intent confidence points to classifier review.

---

## Slide 16: API and Web Surface

### Content
- `/query`, `/chat`, `/workspaces`, `/user-profiles`, `/profile/workspace/{id}`
- Admin endpoints rebuild indexes, summaries, profiles, and platform-doc chunks
- Feedback and score endpoints attach quality signals to Langfuse traces
- Next.js server routes proxy browser requests to FastAPI via `PYTHON_API_URL`

### Speaker Notes
This is more than a backend script. It has serving endpoints, admin lifecycle endpoints, observability endpoints, and a web UI that uses server-side API routes as a boundary between the browser and Python backend.

---

## Slide 17: Design Decisions and Tradeoffs

### Content
- Separate vector collections improve precision but require freshness management
- Summary-first profiles reduce token noise but depend on summary quality
- Async evaluation preserves latency but scores arrive later
- LLM classifier is flexible but introduces uncertainty and model dependency
- LiteLLM adds a service but centralizes routing and observability

### Speaker Notes
Each decision has a cost. The architecture is stronger when you can explain why the tradeoff is acceptable for this use case and how the system mitigates the downside.

---

## Slide 18: Failure Cases and Mitigations

### Content
- Missing or stale indexes -> health checks and admin sync endpoints
- Low retrieval recall -> query rewriting, chunk overlap, and intent-specific stores
- Hallucinated answers -> OUT_OF_SCOPE guard, grounded prompts, faithfulness scoring
- Ambiguous people queries -> candidate resolution before semantic fallback
- Evaluation cost/latency -> background RAGAS execution

### Speaker Notes
A strong interview answer names realistic RAG failures and ties each one to a detection or mitigation mechanism. This system is built to make failures observable rather than silent.

---

## Slide 19: Production Readiness: Current State

### Content
- Implemented: full/incremental ingestion, indexing, assistant runtime, tracing, scoring, RAGAS, feedback, admin sync
- Observable request lifecycle: classify, rewrite, retrieve, generate, score
- Operational controls exist, but identity, ACLs, alerting, and release gates still need hardening

### Speaker Notes
Be honest: this is production-style now. It becomes production-ready after security, reliability, deployment, and quality gates are added.

---

## Slide 20: Production Readiness: Security and Governance

### Content
- Add authentication and propagate user identity from UI to FastAPI
- Apply workspace/user ACL filters before retrieval and before answer generation
- Move secrets to a managed secret store and rotate LiteLLM/Langfuse keys
- Add audit logs for admin syncs, data access, feedback, and prompt changes
- Introduce PII/sensitive-content checks for artifacts and trace payloads

### Speaker Notes
This is the first production-readiness path: prevent data leakage. In enterprise RAG, ACL-aware retrieval is not optional because generated answers can expose retrieved context.

---

## Slide 21: Production Readiness: Reliability and Quality Gates

### Content
- Move background RAGAS work to a queue-backed worker for retry and backpressure
- Create scheduled eval datasets for DOC_QA, ARTIFACT_SEARCH, USER_SEARCH, and HYBRID
- Gate prompt/model/index changes on regression metrics before promotion
- Add SLO dashboards for latency, error rate, index freshness, cost/query, and faithfulness
- Use canary releases for classifier prompts and generation prompts

### Speaker Notes
This is how production readiness can be met operationally: make quality measurable, make evaluation reliable, and make changes releasable with regression checks.

---

## Slide 22: Production Readiness: Deployment and Operations

### Content
- Containerize FastAPI, Next.js, LiteLLM, Langfuse, and Milvus with environment-specific configs
- Run ingestion/indexing as scheduled jobs with idempotent full and incremental modes
- Add CI for unit, integration, retrieval, and API contract tests
- Define runbooks for stale indexes, failed LLM calls, high cost, and low evaluation scores

### Speaker Notes
This slide completes the production-readiness path. It explains how the system moves from local/demo operation to repeatable environments and on-call ownership.

---

## Slide 23: Demo Walkthrough

### Content
- Show workspaces and a generated workspace/user profile
- Run semantic artifact search for an ML concept
- Ask DOC_QA, ARTIFACT_SEARCH, and USER_SEARCH questions in the assistant
- Open Langfuse trace and show classify, rewrite, generate, and score events

### Speaker Notes
Demo the loop: user question, routed answer, trace, quality score, diagnosis. Keep the demo focused on engineering behavior rather than UI decoration.

### Demo Script
1. Show the workspace list and explain it comes from the ingestion catalog.
2. Open a profile and point out generated expertise and artifact context.
3. Search for a concept such as "PySpark classification examples".
4. Ask a platform question: "How do I submit a Spark job on the platform?"
5. Ask an artifact question: "Find notebooks about recommender systems."
6. Ask a people question: "Who works on Spark ML?"
7. Open Langfuse and show the same trace_id with classify, rewrite, generate, and scores.

---

## Slide 24: Close

### Content
- Turns workspace artifacts into a queryable intelligence layer
- Separates ingestion, retrieval, orchestration, observability, and evaluation
- Built to explain failures, not just return answers
- Clear production path: security, quality gates, deployment automation, and operational runbooks

### Speaker Notes
The strongest takeaway is engineering discipline: observable, evaluable, grounded RAG with a practical hardening path. Close by emphasizing the decisions and tradeoffs rather than marketing language.
