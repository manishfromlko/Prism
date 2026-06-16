# Ingestion Pipeline

## Purpose

The ingestion pipeline scans workspace folders under `dataset/`, records metadata about supported artifacts, and writes the source-of-truth catalog used by retrieval and API profile endpoints.

## Entry Point

```bash
python -m src.ingestion.cli --root dataset --mode full
python -m src.ingestion.cli --root dataset --mode incremental
```

## Code Map

| File | Responsibility |
| --- | --- |
| `src/ingestion/cli.py` | Parses `--root`, `--mode`, and `--dry-run`. |
| `src/ingestion/pipeline.py` | Orchestrates workspace scan, classification, extraction, and storage. |
| `src/ingestion/guards.py` | Classifies files and protects against sensitive/unsupported artifacts. |
| `src/ingestion/extractors.py` | Extracts notebook and script metadata such as tools, databases, and table references. |
| `src/ingestion/models.py` | Dataclasses for workspaces, artifacts, runs, and audit records. |
| `src/ingestion/storage.py` | Reads/writes `ingestion_catalog.json` and `ingestion_audit.json`. |
| `src/ingestion/utils.py` | Hashing, path normalization, safe directory listing. |

## Supported Files

| Extension | Type |
| --- | --- |
| `.ipynb` | notebook |
| `.py`, `.scala`, `.sql` | script |
| `.txt`, `.md` | text |

Unsupported files are ignored. Guard-skipped files are written to the catalog with status `skipped` and also recorded in the audit file.

## Full vs Incremental

Full mode resets the in-memory catalog before scanning and writes a fresh view of the dataset.

Incremental mode compares each artifact hash with the stored `content_hash`. Unchanged files are not reprocessed, but their catalog status is updated to `unchanged` when present.

## Outputs

```text
dataset/.ingestion/ingestion_catalog.json
dataset/.ingestion/ingestion_audit.json
```

The catalog is required by:

- `src/retrieval/indexer.py`
- `src/retrieval/artifact_summary_indexer.py`
- `src/retrieval/profiling.py`
- FastAPI `/workspaces` and `/profile/workspace/{workspace_id}` endpoints

## Operational Notes

- The pipeline treats each immediate child directory of `dataset/` as one workspace.
- Workspace ids are normalized from directory names.
- The pipeline currently does not parse raw CSV/binary datasets into the catalog for semantic search.
- If you move or rename workspace directories, run full mode to avoid stale catalog entries.
