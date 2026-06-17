# Research: Data Cleaning and Ingestion Pipeline

## Decision: Backend language and runtime
- Decision: Use Python 3.11+ for the ingestion pipeline.
- Rationale: Python is the dominant language for data engineering and AI orchestration, has mature notebook/file parsing libraries, and integrates smoothly with Langchain, Litellm, and future backend services.
- Alternatives considered:
  - Scala/Java via Spark for distributed source scanning: rejected for MVP because the sample data is local-mounted and the priority is rapid metadata extraction and guardrail logic.
  - Go for performance and binary distribution: rejected because Python enables richer notebook metadata extraction and easier Langchain integration.

## Decision: Ingestion architecture and storage
- Decision: Build a source-first pipeline with local filesystem discovery, metadata cataloging, content classification, and explicit provenance storage in a lightweight staging store.
- Rationale: The project requires visibility into user workspaces before any LLM generation, so ingestion must extract authoritative workspace and file-level evidence first.
- Alternatives considered:
  - Direct ingestion into Qdrant: rejected because vectorization should be a downstream stage after cleaning and metadata extraction.
  - Pure file scan without provenance: rejected because auditability and guardrails demand source lineage for every record.

## Decision: Incremental update strategy
- Decision: Support a full initial ingestion run and a daily incremental mode using file hashing/timestamps and ingestion state tracking.
- Rationale: Daily update scheduling minimizes reprocessing while keeping user profiles current, consistent with the requirement for management visibility.
- Alternatives considered:
  - Full daily re-ingestion: rejected due to scale and duplicate processing risks.
  - Event-driven file watch: deferred for later release because the current environment is NAS-mounted and scheduling is simpler for MVP.

## Decision: Guardrails and sensitive artifact handling
- Decision: Implement a guardrail layer that classifies files by type, identifies sensitive patterns, and either sanitizes or skips ingesting unsupported artifacts while writing audit records.
- Rationale: Sensitive workspace content cannot be blindly ingested; the system must also remain explainable to security reviewers.
- Alternatives considered:
  - Ingest everything and filter later: rejected because it violates the constitution's requirement for responsible ingestion and audit readiness.

## Decision: Qdrant collections for future retrieval
- Decision: Plan for separate Qdrant collections: one for user-level summaries and one for notebook/document-level embeddings.
- Rationale: The constitution and feature plan call for dual-collection representation; the ingestion stage will populate notebook/document metadata that later feeds the notebook-level collection and aggregated user signals that feed the user-level collection.
- Alternatives considered:
  - Single monolithic embedding collection: rejected because it would make user-profile retrieval less precise and harder to maintain.

## Decision: Observability and monitoring readiness
- Decision: Embed structured ingestion logging, health status outputs, and validation summaries in the pipeline, making it compatible with Langfuse or another observability layer.
- Rationale: Monitoring ingestion health is a required project principle and ensures the pipeline is trustworthy before downstream retrieval and generation begin.
- Alternatives considered:
  - Minimal logging only: rejected because it would not satisfy constitution-level observability requirements.
