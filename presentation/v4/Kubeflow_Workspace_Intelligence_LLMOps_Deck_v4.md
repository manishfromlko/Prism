# Kubeflow Workspace Intelligence LLMOps Deck v4

Interview-ready slide content generated from the current codebase.

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
- The prompt mentions approximately 250 notebooks. I would present that as an intended/expandable dataset size, not as the current indexed snapshot.

---

## Slide 1: Title

### Content
- **Kubeflow Workspace Intelligence with RAG and LLMOps**
- Production-style assistant for workspace knowledge, notebook discovery, and user expertise profiling
- Built for data scientists and ML engineers
- Core stack: FastAPI, Next.js, Milvus, OpenAI-compatible LiteLLM gateway, Langfuse, RAGAS

### Speaker Notes
This project is a RAG-based intelligence layer over Kubeflow-style workspaces. The goal is not a generic chatbot. The system understands notebooks, scripts, platform documents, and generated user profiles so a data scientist can ask questions like: "How do I submit a Spark job?", "Find notebooks using PySpark classification", or "Who has worked on NLP?"

The implementation is production-style because it includes ingestion, indexing, retrieval, generation, web/API separation, observability, evaluation, and admin workflows. The LLMOps part is especially important: every LLM call routes through LiteLLM and is traced in Langfuse, while response quality is evaluated with RAGAS and LLM-as-judge.

### Suggested Diagram
Title slide visual: simple horizontal strip showing **Workspace Artifacts -> RAG Indexes -> Intent-Routed Assistant -> Langfuse/RAGAS Feedback Loop**.

---

## Slide 2: Problem

### Content
- Kubeflow workspaces become knowledge silos as notebooks and scripts grow
- Search by filename is weak for ML intent: models, tools, datasets, techniques
- New team members cannot quickly identify prior work or domain owners
- Chatbot answers need grounding, observability, and evaluation, not just "best effort" LLM calls

### Speaker Notes
In ML teams, a large part of institutional memory lives inside notebooks. That memory is hard to query because notebook titles rarely capture the actual work. A notebook named `Classification.ipynb` may contain Spark setup, feature engineering, model selection, and evaluation logic.

The second problem is expertise discovery. If I want to know who worked on recommender systems or Spark streaming, that information is distributed across artifacts. The project solves this by distilling artifact-level summaries and rolling them up into user profiles.

The final problem is operational. A demo chatbot is easy; a system you can reason about in production needs traceability, cost visibility, prompt logs, and quality evaluation.

### Suggested Diagram
Problem diagram: three disconnected boxes labeled **Notebooks**, **Scripts**, **Docs**, each pointing to pain points: **hard to search**, **hard to attribute expertise**, **hard to trust answers**.

---

## Slide 3: Solution Overview

### Content
- RAG assistant over three knowledge surfaces:
  - Platform documentation
  - Workspace artifact summaries
  - User expertise profiles
- Intent classifier routes queries to DOC_QA, ARTIFACT_SEARCH, USER_SEARCH, HYBRID, or OUT_OF_SCOPE
- Semantic retrieval uses OpenAI embeddings and Milvus vector collections
- LLMOps loop captures traces, scores, and RAG quality metrics

### Speaker Notes
The system separates knowledge into different retrieval surfaces rather than throwing everything into one vector index. Platform docs answer "how do I use the platform" questions. Artifact summaries answer "find code/notebooks like this" questions. User profiles answer "who works on this" questions.

The classifier is itself an LLM call. It decides the route and records a confidence score. This matters because different query types need different retrieval behavior. A person lookup like "Tell me about Alex Chen" should not be treated the same as "How do I submit a Spark job?"

The HYBRID route is important for realistic enterprise queries. A user may ask, "Who has examples for Spark jobs?" That crosses documentation, artifacts, and people.

### Suggested Diagram
Use `presentation/v4/high-level-architecture-v4.mmd`.

---

## Slide 4: Dataset and Ingestion Scope

### Content
- Current catalog: 5 workspaces, 211 artifacts
- Artifact types indexed:
  - 132 Jupyter notebooks
  - 75 scripts
  - 4 text files
- CSV, binary, archive, and unsupported files are excluded from semantic indexing
- Full and incremental ingestion modes are implemented

### Speaker Notes
The ingestion pipeline scans workspace directories and creates a catalog under `dataset/.ingestion/ingestion_catalog.json`. It supports full ingestion and incremental ingestion. Incremental mode uses content hashes to detect unchanged files, which avoids needless reprocessing and reduces embedding cost.

The code intentionally excludes raw datasets such as CSV files from semantic indexing. That is a design decision: the goal is to understand what people are working on, not to embed raw rows of data. Supported artifacts are notebooks, scripts, and text/markdown-style files.

The prompt says approximately 250 notebooks. In the checked-in catalog, the actual indexed snapshot has 132 notebooks. For an interview, I would state the concrete catalog numbers and say the architecture scales to a larger notebook corpus.

### Suggested Diagram
Ingestion funnel:
**Workspace folders -> file classifier/guardrails -> metadata extraction -> ingestion catalog -> indexing jobs**.

---

## Slide 5: Core Capabilities

### Content
- Workspace browsing and profiling
- Notebook/script semantic search
- LLM-generated artifact summaries
- User profiles generated from artifact summaries
- Platform documentation QA from `.docx` guides
- Enterprise assistant with intent routing, query rewriting, citations/sources, and feedback scores

### Speaker Notes
The prompt listed user profiling, notebook summarization, and semantic search. The implemented project goes further.

Artifact summaries are generated from notebook/script content and indexed into a dedicated Milvus collection. User profiles are generated from those summaries rather than directly from raw code, which gives the LLM a cleaner, lower-noise input.

The chatbot also supports platform documentation QA. It ingests Word documents from `platform_documents/`, splits them into chunks, embeds them, and retrieves them for DOC_QA. This makes the assistant useful for onboarding and operational questions, not just artifact discovery.

### Suggested Diagram
Capability map with three columns:
**Artifacts**, **People**, **Platform Docs**. Each column shows storage/index and example query.

---

## Slide 6: High-Level Architecture

### Content
- Frontend: Next.js application with server-side API routes
- Backend: FastAPI retrieval and orchestration service
- Vector store: Milvus collections for artifacts, summaries, profiles, and docs
- LLM gateway: LiteLLM proxy with OpenAI-compatible client
- Observability: Langfuse traces and scores

### Speaker Notes
The web frontend does not call Python directly from the browser. It uses Next.js API routes as a backend-for-frontend layer and proxies to the FastAPI service using `PYTHON_API_URL`. This gives cleaner separation between browser concerns and backend retrieval/generation concerns.

FastAPI owns the retrieval API, admin sync endpoints, chatbot orchestration, metrics endpoint, and observability feedback endpoints. Milvus stores the vectorized knowledge surfaces. LiteLLM gives the code one OpenAI-compatible client path and centralizes model routing and observability callbacks.

### Suggested Diagram
Use the high-level architecture diagram in `presentation/v4/high-level-architecture-v4.mmd`.

---

## Slide 7: Ingestion and Indexing Pipeline

### Content
- Scan workspace directories and classify supported files
- Extract notebook/script metadata: tools, table references, database targets
- Convert artifacts into LangChain documents
- Chunk text by content type
- Generate embeddings with `text-embedding-3-small`
- Upsert vectors into Milvus

### Speaker Notes
The ingestion phase creates the structured catalog. The retrieval indexer then loads that catalog through `DocumentLoader`, extracts notebook cell content from `.ipynb` JSON, applies document guardrails, and converts each artifact into a LangChain document with metadata.

Chunking is content-aware. Python/scripts use a code splitter, markdown uses a markdown splitter, and notebooks use recursive splitting because notebooks mix markdown and code. The default retrieval configuration uses 1000-character chunks with 200-character overlap.

The vector indexer supports incremental mode. It queries already indexed artifact IDs in Milvus and only embeds new artifacts. This is a practical cost and latency control.

### Suggested Diagram
Flow:
**Dataset -> IngestionPipeline -> Catalog JSON -> DocumentLoader -> TextProcessor -> EmbeddingService -> Milvus kubeflow_artifacts**.

---

## Slide 8: Retrieval Surfaces and Collections

### Content
- `kubeflow_artifacts`: raw artifact chunks for semantic search
- `artifact_summaries`: LLM-generated summaries and tags
- `user_profiles`: user-level expertise summaries
- `platform_docs`: chunks from platform Word documents
- Separate indexes keep retrieval intent and metadata clean

### Speaker Notes
This is one of the stronger design decisions in the project. Instead of mixing every kind of content into one vector space, the system maintains separate stores for different use cases.

Artifact search retrieves from summaries, not raw chunks, inside the chatbot. That gives more concise context for "find notebooks about X". User search retrieves from generated profiles. Documentation QA retrieves from platform docs. The older `/query` endpoint still supports vector search over catalog artifacts and can use hybrid retrieval.

The tradeoff is operational complexity: multiple collections must be built and kept fresh. The benefit is better routing, cleaner prompts, and less irrelevant context.

### Suggested Diagram
Four Milvus cylinders with labels and example payload:
**artifact chunks**, **artifact summaries**, **user profiles**, **platform docs**.

---

## Slide 9: Chatbot Runtime Flow

### Content
- Generate a request-level `trace_id`
- Classify intent with LLM
- Rewrite query for retrieval recall
- Retrieve from one or more stores
- Build intent-specific prompt
- Generate answer through LiteLLM
- Format answer with sources, artifacts, users, and trace ID

### Speaker Notes
The runtime flow is implemented in `ChatEngine`. It starts by generating a UUID trace ID. That trace ID is forwarded to every LLM call using LiteLLM metadata so classification, rewriting, and generation are grouped under one Langfuse trace.

The query rewriter is a retrieval optimization step. The original user question is kept for final prompting, but the rewritten query is used for vector search to improve recall.

After retrieval, the engine builds a prompt matched to the intent: docs QA, artifact search, user search, or hybrid. The response formatter then extracts structured result fields for the frontend.

### Suggested Diagram
Use `presentation/v4/chatbot-runtime-flow-v4.mmd`.

---

## Slide 10: Intent Routing Design

### Content
- Supported intents:
  - DOC_QA
  - ARTIFACT_SEARCH
  - USER_SEARCH
  - HYBRID
  - OUT_OF_SCOPE
- USER_SEARCH has a special path for exact/ambiguous name matches
- OUT_OF_SCOPE prevents unsupported real-time or external answers

### Speaker Notes
The classifier returns intent, confidence, and reasoning. If classification fails, the code falls back to DOC_QA with low confidence. That is a conservative fallback because documentation QA is safer than pretending to know unknown workspace facts.

USER_SEARCH is handled carefully. Before semantic search, the system uses string matching and RapidFuzz-style candidate retrieval over known user IDs. If there is one exact high-confidence match, it fetches the profile directly from Milvus and returns it without generation. If there are multiple candidates, it uses an LLM resolver for disambiguation. If there are no name candidates, it falls back to semantic user-profile retrieval.

OUT_OF_SCOPE returns a bounded response instead of letting the LLM answer from general knowledge. This is a hallucination-control feature.

### Suggested Diagram
Decision tree:
**Query -> Classifier -> intent branches**, with USER_SEARCH branch showing **name match -> exact return / disambiguate / vector fallback**.

---

## Slide 11: LLM Orchestration with LiteLLM

### Content
- All chat completions use an OpenAI-compatible client pointed at LiteLLM
- LiteLLM centralizes model routing and provider configuration
- Generation model defaults to `gpt-4o-mini`
- Evaluation/judge paths use stronger `gpt-4o`
- Trace metadata groups multi-step calls under one request

### Speaker Notes
The code uses `make_llm_client()` as the factory for OpenAI-compatible calls. The base URL is `LITELLM_BASE_URL`, defaulting to `http://localhost:4000`, with `LITELLM_API_KEY` used for the proxy.

This is a good LLMOps design because application code does not need to know provider-specific details. If the model or provider changes, the proxy config can absorb much of that change.

The project also makes a deliberate model tradeoff. The main assistant generation uses `gpt-4o-mini`, which is cost-efficient for production interaction. RAGAS and LLM-as-judge use `gpt-4o`, because evaluation quality benefits from a stronger model.

### Suggested Diagram
Box:
**Application OpenAI client -> LiteLLM proxy -> model provider** with side path **LiteLLM callbacks -> Langfuse**.

---

## Slide 12: Layer 1 LLM Observability

### Content
- LiteLLM forwards prompt/response traces to Langfuse
- Captures token usage, cost, latency, and errors per LLM call
- Groups classify, rewrite, and generate calls under one trace ID
- Adds inline heuristic scores:
  - response_length
  - has_content
  - intent_confidence
  - source_count

### Speaker Notes
Layer 1 answers: what happened during the LLM request? How many tokens did it use? How long did it take? What prompt and response were sent? Did the model call fail?

The project has two complementary mechanisms. LiteLLM captures the raw LLM traces automatically. The app then posts response quality heuristics into Langfuse using the Langfuse SDK. These are not semantic correctness metrics; they are lightweight operational signals. For example, `source_count` helps catch cases where the model generated an answer with no retrieved grounding.

The trace ID is returned to the frontend, which makes it possible to attach user feedback later.

### Suggested Diagram
Trace ladder:
**classify span -> rewrite span -> generate span -> heuristic scores**, all under one Langfuse trace.

---

## Slide 13: Layer 2 RAG Evaluation

### Content
- Runs after response in a background thread
- RAGAS metrics implemented:
  - faithfulness
  - answer_relevancy
  - context_precision
- USER_SEARCH exact match uses LLM-as-judge: `profile_relevance`
- Scores are posted back to the same Langfuse trace

### Speaker Notes
Layer 2 answers a different question than Layer 1: was the answer good and grounded?

The implementation dispatches evaluation in a daemon thread after the API response returns. That is an important latency tradeoff. RAGAS can require multiple LLM calls, so running it inline would make the chat endpoint slow and unpredictable.

For normal RAG paths, the code extracts contexts from doc hits, artifact summaries, or user profiles and runs faithfulness, answer relevancy, and context precision. For USER_SEARCH exact matches, there may be no generation or retrieved contexts in the RAGAS sense, so the system uses an LLM judge to score whether the returned profile answers the query.

### Suggested Diagram
Use `presentation/v4/observability-evaluation-flow-v4.mmd`.

---

## Slide 14: Evaluation Interpretation

### Content
- Low faithfulness: answer includes claims unsupported by retrieved context
- Low answer relevancy: answer does not address the user question
- Low context precision: retriever returned weak or poorly ranked context
- Low profile_relevance: returned user profile does not match the people-search intent
- Combined scores guide whether to tune prompts, retrieval, or routing

### Speaker Notes
The useful part of RAG evaluation is diagnosis. A single "quality score" is less useful than knowing what failed.

If faithfulness is low but answer relevancy is high, the assistant may be answering the question but inventing unsupported details. That points to prompt grounding and refusal behavior. If context precision is low, the generator may be fine but the retriever is feeding bad evidence. That points to chunking, embeddings, metadata filters, or separate collections.

The project also supports manual/user feedback through `/observability/feedback`, which posts a binary `user_feedback` score to Langfuse.

### Suggested Diagram
2x2 matrix:
**retrieval good/bad** vs **generation good/bad**, with example actions in each quadrant.

---

## Slide 15: API and Web Application Surface

### Content
- FastAPI endpoints:
  - `/query` for semantic/hybrid artifact search
  - `/chat` for assistant orchestration
  - `/workspaces`, `/profile/workspace/{id}`, `/user-profiles`
  - admin sync endpoints for indexes, summaries, profiles, and docs
  - `/observability/score` and `/observability/feedback`
- Next.js UI proxies `/api/*` to the Python backend

### Speaker Notes
This is more than a backend script. The FastAPI service exposes operational endpoints for sync, retrieval, chat, health, metrics, and observability. That makes it easier to demo and operate.

The Next.js app has pages/components for search, workspaces, profiles, analytics, settings, and chatbot interaction. Server-side API routes prevent the browser from coupling directly to the Python service.

The admin endpoints matter in an interview because they show lifecycle thinking. You can rebuild vector indexes, regenerate artifact summaries, regenerate profiles from summaries, and ingest platform docs.

### Suggested Diagram
API map:
**Next.js UI -> /api routes -> FastAPI**, with endpoint groups: **search**, **chat**, **profiles**, **admin**, **observability**.

---

## Slide 16: Design Decisions and Tradeoffs

### Content
- Separate vector collections over one mixed index
- Summary-first profiles over raw-code profile generation
- Async RAG evaluation over inline evaluation
- LLM classifier over fixed keyword routing
- Exact user lookup before semantic people search
- LiteLLM gateway over direct provider calls

### Speaker Notes
Separate vector collections improve precision and prompt clarity, but they add sync complexity. Summary-first profiles reduce noise and token volume, but quality depends on the artifact summary step. Async evaluation preserves user latency, but scores appear seconds later rather than immediately.

The LLM classifier is flexible and handles natural language better than keyword rules, but it introduces a model dependency and classification uncertainty. That is why the system records classifier confidence and includes OUT_OF_SCOPE handling.

Exact user lookup before semantic search is a practical optimization. If the user asks for a named person, direct retrieval is more reliable and cheaper than vector search plus generation.

LiteLLM introduces another service, but it centralizes observability and model routing. That is a reasonable tradeoff for LLMOps.

### Suggested Diagram
Tradeoff table with columns:
**Decision**, **Why**, **Cost/Risk**, **Mitigation**.

---

## Slide 17: Failure Cases and Mitigations

### Content
- Missing or stale indexes -> admin sync endpoints and health checks
- Low retrieval recall -> query rewriting, chunk overlap, intent-specific stores
- Hallucinated answers -> OUT_OF_SCOPE guard, retrieved-context prompts, faithfulness scoring
- Ambiguous people queries -> candidate resolution before vector fallback
- LLM/provider failure -> bounded error response and trace visibility
- Evaluation cost/latency -> background RAGAS execution

### Speaker Notes
The failure modes are realistic. A RAG system can fail before the LLM ever sees a prompt: documents may not be indexed, collections may not be loaded, embeddings may fail, or the wrong retrieval surface may be used.

The project mitigates some of that with startup initialization, health endpoints, admin sync flows, query rewriting, separate stores, and observable traces.

The system is not fully production-complete. Areas I would still harden include stronger auth/ACL filtering, automated regression eval sets, CI gates for prompts, queue-based background evaluation instead of daemon threads, and stronger monitoring around Milvus and the FastAPI process.

### Suggested Diagram
Failure pipeline with red warning points:
**ingest -> index -> classify -> retrieve -> generate -> evaluate**, each annotated with mitigation.

---

## Slide 18: Production Readiness

### Content
- Implemented:
  - full/incremental ingestion
  - vector indexing
  - multi-intent assistant
  - LiteLLM + Langfuse tracing
  - RAGAS/LLM-judge scoring
  - frontend/backend separation
  - admin sync and feedback endpoints
- Next hardening:
  - auth and workspace ACL enforcement
  - scheduled eval datasets and quality gates
  - queue-backed evaluation workers
  - SLO dashboards and alerting
  - prompt/version release process

### Speaker Notes
This slide should be honest. The project is production-style, not necessarily production-final.

The implemented pieces demonstrate the core architecture and operational thinking. The next steps are what I would expect before an enterprise rollout: identity, authorization, automated evaluation, alerting, deployment automation, and prompt/model versioning.

The important interview framing is that LLMOps is not only tracing. It is the loop from ingestion quality to retrieval quality to generation quality to user feedback and production diagnostics.

### Suggested Diagram
Readiness checklist split into **Implemented Now** and **Production Hardening**.

---

## Slide 19: Demo Walkthrough

### Content
- Start with workspace inventory and profiles
- Show semantic artifact search
- Ask platform documentation question
- Ask people/expertise question
- Show Langfuse trace for the same `trace_id`
- Show RAGAS/LLM-judge scores attached to the trace

### Speaker Notes
Demo sequence:

1. Open the Next.js webapp and show the workspace list. Point out that this is backed by the ingestion catalog.
2. Open a workspace profile. Highlight extracted tools, topics, file types, and recent artifacts.
3. Use search for a technical query such as "PySpark classification examples" or "recommender systems".
4. Open the AI Assistant and ask: "How do I submit a Spark job on the platform?" This should route to DOC_QA and retrieve platform document chunks.
5. Ask: "Find notebooks about recommender systems." This should route to ARTIFACT_SEARCH.
6. Ask: "Who works on Spark ML?" This should route to USER_SEARCH or HYBRID depending on wording.
7. Copy the returned `trace_id` from the API response or logs and open Langfuse.
8. Show grouped spans for classify, rewrite, and generate. Then show scores: response_length, has_content, intent_confidence, source_count, plus RAGAS metrics after the background job completes.

### Suggested Diagram
Demo storyboard:
**UI -> query -> answer -> trace -> scores**.

---

## Slide 20: Interview Close

### Content
- This project converts workspace artifacts into a queryable intelligence layer
- The architecture separates ingestion, retrieval, orchestration, and evaluation
- LLM calls are observable by default through LiteLLM and Langfuse
- RAG quality is measured with faithfulness, answer relevancy, context precision, and profile relevance
- The system is built to explain failures, not just return answers

### Speaker Notes
The closing message is that this is an engineering system, not a chatbot wrapper. The strongest parts are the separation of retrieval surfaces, the intent-routed orchestration, and the observability/evaluation loop.

In an interview, I would emphasize the design decisions and tradeoffs: why summaries exist, why user profiles are generated from summaries, why evaluation is async, why LiteLLM sits in the middle, and how traces map to debugging actions.

End by saying the next production step would be hardening identity/ACLs and creating an automated regression suite over representative queries.

### Suggested Diagram
Final flywheel:
**Ingest -> Retrieve -> Generate -> Trace -> Evaluate -> Improve**.

---

# Demo Walkthrough Script

Use this as a spoken sequence during a live interview demo.

1. "I will start from the workspace view. The backend has scanned five Kubeflow-style workspaces and created an ingestion catalog of notebooks, scripts, and text artifacts."
2. "The profiler gives a quick summary of a user's workspace: what tools appear, what topics recur, and what artifacts were recently touched."
3. "Now I will search for an ML concept rather than a filename. This goes through vector retrieval, so the system can find semantically related notebooks even when titles do not match the query exactly."
4. "Next I will use the assistant. This question is about platform usage, so the LLM classifier routes it to DOC_QA and retrieves chunks from the platform documentation collection."
5. "This next question asks for notebooks, so it routes to ARTIFACT_SEARCH. The retriever uses generated artifact summaries rather than raw notebook chunks to keep context concise."
6. "For people search, the system first tries name/candidate resolution. If it is an exact match, it returns the stored profile directly. If it is expertise-based, it performs semantic retrieval over user profiles."
7. "Every LLM call in this interaction goes through LiteLLM. The app passes the same trace ID across classify, rewrite, and generate, so Langfuse shows the full request lifecycle."
8. "After the response returns, Layer 2 evaluation runs in the background. RAGAS posts faithfulness, answer relevancy, and context precision to the same trace. Exact user-profile lookups use an LLM judge called profile_relevance."
9. "This lets me debug quality. If context precision is low, I tune retrieval or chunking. If faithfulness is low, I tune prompts and grounding. If intent confidence is low, I review classifier behavior."

# Diagram Descriptions

## Architecture Diagram

Draw the system as five layers:

1. **Experience layer**: Data scientists and ML engineers using the Next.js webapp.
2. **API layer**: Next.js server-side API routes proxying to FastAPI.
3. **Orchestration layer**: ChatEngine with intent classification, query rewriting, retrieval routing, prompt building, generation, and formatting.
4. **Knowledge layer**: Milvus collections for artifact chunks, artifact summaries, user profiles, and platform docs.
5. **LLMOps layer**: LiteLLM proxy, Langfuse traces/scores, RAGAS evaluation, LLM-as-judge, feedback endpoint.

## Runtime Flow Diagram

Draw:

`User Query -> trace_id -> IntentClassifier -> QueryRewriter -> Routed Retriever -> Prompt Builder -> LiteLLM Generate -> Formatted Response -> Langfuse Trace`

Then add a background branch:

`Formatted Response -> Background Eval -> RAGAS / LLM Judge -> Langfuse Scores`

## Evaluation Pipeline Diagram

Draw two paths:

1. **Normal RAG path**: answer + query + retrieved contexts -> RAGAS -> faithfulness, answer_relevancy, context_precision -> Langfuse score API.
2. **Exact USER_SEARCH path**: query + returned profile -> LLM judge -> profile_relevance -> Langfuse score API.

## Failure Analysis Diagram

Draw the pipeline:

`Ingestion -> Indexing -> Intent Routing -> Retrieval -> Generation -> Evaluation`

Mark likely failures:

- skipped/missing files
- stale Milvus collections
- wrong intent
- weak retrieval context
- hallucinated answer
- delayed/missing evaluation score

Then attach mitigation labels:

- incremental/full sync
- health checks
- confidence score
- query rewrite and collection separation
- faithfulness evaluation
- background logs and Langfuse flush
