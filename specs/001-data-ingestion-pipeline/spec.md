# Feature Specification: Data Cleaning and Ingestion Pipeline

**Feature Branch**: `[001-data-ingestion-pipeline]`
**Created**: 2026-04-28
**Status**: Draft
**Input**: User description: "Implement the feature specification based on the updated constitution. I want to build data cleaning and ingestion pipeline first."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Workspace Source Ingestion (Priority: P1)

A data platform operator needs the system to discover and ingest workspace files from the NAS-like repository so management can see who is working on what.

**Why this priority**: This is the foundation for all profiling, because no user profile or notebook summary can be generated without an accurate source ingest.

**Independent Test**: Run the ingestion pipeline against the sample `dataset/` workspace structure and verify that workspace metadata, file counts, notebook references, and extracted tool/database mentions are stored in the staging layer.

**Acceptance Scenarios**:

1. **Given** a valid workspace root with user directories and files, **When** the ingestion job runs, **Then** each workspace owner is recorded with a file count and workspace path.
2. **Given** notebook files under a workspace, **When** the ingestion job processes them, **Then** notebook metadata and any detected database/table/tool mentions are captured alongside source references.

---

### User Story 2 - Incremental Update and File Change Tracking (Priority: P2)

A data engineer wants the pipeline to support daily incremental updates so the profiler remains current without reprocessing unchanged files.

**Why this priority**: Incremental ingestion reduces load and ensures the dashboard reflects recent activity rather than stale snapshots.

**Independent Test**: Add or modify files in a workspace, run the incremental update, and verify that only changed files are reprocessed while unchanged files remain unchanged.

**Acceptance Scenarios**:

1. **Given** a previous ingestion state and a workspace with new or modified files, **When** the incremental job runs, **Then** only the changed files are added or updated in the ingestion catalog.
2. **Given** a workspace with no changes, **When** the incremental job runs, **Then** it completes without creating duplicate records or reprocessing unchanged files.

---

### User Story 3 - Guardrail-aware Sanitization and Auditability (Priority: P3)

A security reviewer needs the pipeline to detect unsupported or sensitive files and log decision details so the system remains compliant and explainable.

**Why this priority**: This protects the project from ingesting secrets or unsupported binary artifacts while preserving a clear audit trail.

**Independent Test**: Introduce a sensitive file type or unsupported artifact in a workspace, run ingestion, and verify that the file is excluded or sanitized and the action is recorded.

**Acceptance Scenarios**:

1. **Given** a sensitive file such as a credential or virtual environment artifact, **When** the ingestion job encounters it, **Then** it does not ingest the raw file content and logs the reason.
2. **Given** an unsupported binary artifact, **When** the ingestion job encounters it, **Then** it records metadata about the artifact without creating a content-level document record.

---

### Edge Cases

- What happens when a workspace directory is missing or inaccessible during ingestion?
- How does the system handle corrupted or partially written notebook files?
- How does the pipeline behave when file metadata suggests a duplicate notebook or a duplicate workspace record?
- How are large binary files and artifacts handled without causing ingestion failures?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST discover all user workspace directories and file artifacts under the NAS-like source tree.
- **FR-002**: The system MUST normalize each workspace owner and compute a file count for sorting workspace activity.
- **FR-003**: The system MUST extract structured metadata from notebooks and relevant files, including tool mentions, database targets, and table references.
- **FR-004**: The system MUST clean and classify ingested artifacts, skipping or sanitizing unsupported sensitive files while preserving an audit record of that decision.
- **FR-005**: The system MUST support a full initial ingestion run followed by daily incremental ingestion that processes only new or changed files.
- **FR-006**: The system MUST maintain provenance information for every ingested artifact, including source path, workspace owner, ingestion timestamp, and change reason.
- **FR-007**: The system MUST surface ingestion validation outcomes before downstream retrieval or generation, including missing workspaces, parse failures, and skipped artifacts.

### Key Entities

- **Workspace**: Represents a user-owned NAS workspace directory, identified by workspace name, owner, root path, and active file count.
- **FileArtifact**: Represents an ingested file within a workspace, including path, type, size, content classification, and ingestion status.
- **NotebookDocument**: Represents a notebook or script file that is eligible for extraction, with metadata for detected tools, database queries, and source context.
- **IngestionRun**: Represents a single execution of the pipeline, capturing scope, run type (initial or incremental), timestamp, and validation outcomes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Initial ingestion catalogs 100% of supported workspace files for a representative sample workspace.
- **SC-002**: Incremental ingestion processes new or changed files within 24 hours of arrival for daily scheduled runs.
- **SC-003**: At least 95% of notebook files produce structured metadata records for tool usage, database mentions, or table references.
- **SC-004**: Sensitive or unsupported artifacts are excluded or sanitized in 100% of ingestion runs, with audit logs available for each decision.
- **SC-005**: The pipeline reports ingestion health and source coverage before downstream generation is enabled.

## Assumptions

- Workspaces are accessible through a mounted NAS-like directory such as the local `dataset/` structure.
- Authentication and access control for workspace sources are provided outside this feature; this feature focuses on ingestion and cleaning.
- Webapp profiling, retrieval, and generation are separate features that consume the cleaned ingestion output.
- Binary-only artifacts may be cataloged at the metadata level without full content extraction.
- Qdrant collection design and retrieval API contracts will be defined in subsequent feature work.
