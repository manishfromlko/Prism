# Implementation Plan: Data Cleaning and Ingestion Pipeline

**Branch**: `main` | **Date**: 2026-04-28 | **Spec**: `specs/001-data-ingestion-pipeline/spec.md`
**Input**: Feature specification from `specs/001-data-ingestion-pipeline/spec.md`

This plan defines the first backend phase for the Kubeflow Workspace Profiling project: a source-first ingestion pipeline that discovers workspace files, cleans and classifies artifacts, extracts notebook metadata, and supports audit-safe incremental updates.

## Summary

Build a Python-based ingestion pipeline for the `dataset/` NAS-style workspace tree. The pipeline will:
- discover user workspaces and catalog workspace metadata,
- classify supported files and skip or sanitize sensitive/unsupported artifacts,
- extract notebook/script metadata for tooling, database, and table mentions,
- persist provenance and audit records for every processed artifact,
- support a full initial run and a daily incremental update mode.

This phase establishes trusted source evidence for later retrieval and user profiling.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Langchain (orchestration primitives), Pydantic, SQLite/SQLAlchemy, notebook parsing libraries, PyYAML/JSON, request/HTTP utilities for future API endpoints  
**Storage**: source filesystem `dataset/`; metadata staging in SQLite or Parquet/JSON; audit logs in structured JSON/SQLite  
**Testing**: pytest unit and integration tests  
**Target Platform**: macOS/Linux server or container runtime  
**Project Type**: backend ingestion service / data pipeline  
**Performance Goals**: complete representative workspace ingestion within minutes; enable daily incremental refresh for new/changed artifacts  
**Constraints**: enforce guardrails for sensitive/unsupported files, preserve provenance, avoid hallucinated profiling inputs, and keep the pipeline modular for later Qdrant integration  
**Scale/Scope**: starts with the local sample workspace tree; designed to support many users and thousands of notebooks and artifacts  

## Constitution Check

The plan satisfies the project constitution:
- Data-First Visibility: ingestion preserves source evidence and workspace provenance before any generated profile output.
- Workspace-Level Accountability: workspaces are canonical first-class entities with owner, file-count, and activity state.
- Dual-Collection Representation: this phase produces document metadata for notebook-level embeddings and aggregated workspace signals for future user-level summaries.
- Guardrails and Responsible Generation: sensitive and unsupported artifacts are classified, audited, and excluded or sanitized.
- Observability and Evaluation: the pipeline emits structured health and validation metrics suitable for Langfuse monitoring.

## Project Structure

### Documentation (this feature)

```text
specs/001-data-ingestion-pipeline/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ingestion-api.md
└── spec.md
```

### Source Code (repository root)

```text
src/
└── ingestion/
    ├── cli.py
    ├── pipeline.py
    ├── extractors.py
    ├── models.py
    ├── storage.py
    ├── guards.py
    └── utils.py

tests/
└── ingestion/
    ├── unit/
    └── integration/
```

**Structure Decision**: Use a single backend project with a dedicated ingestion package under `src/ingestion` and tests under `tests/ingestion`.

## Complexity Tracking

No constitution violations detected. The plan keeps the initial delivery to a single backend ingestion module while preserving the separation needed for later retrieval and generation phases.
