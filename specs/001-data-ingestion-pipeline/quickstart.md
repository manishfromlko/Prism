# Quickstart: Data Cleaning and Ingestion Pipeline

## Prerequisites

- Python 3.11+
- `pip` or equivalent package manager
- Access to the source workspace tree mounted locally under `dataset/`
- A shell session opened in the repository root: `/Users/manish/mount/projects/project-1`

## Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install langchain litellm qdrant-client pydantic pytest
```

> Note: The initial ingestion pipeline is backend-first. Additional dependencies for Langfuse, Qdrant, and frontend UI are added later when retrieval and generation features are implemented.

## Code quality

To maintain code quality, run the following:

```bash
# Format code
python -m pip install black
black src/ tests/

# Lint code
python -m pip install flake8
flake8 src/ tests/

# Run tests
python -m pytest tests/
```

## Run initial ingestion

```bash
python -m src.ingestion.cli --root dataset/ --mode full
```

## Run incremental update

```bash
python -m src.ingestion.cli --root dataset/ --mode incremental
```

Incremental mode only processes files that have been added or modified since the last ingestion run. It preserves existing metadata for unchanged files and updates records for modified ones. This is more efficient for regular updates to large workspaces.

## Validate output

- Confirm that a workspace catalog was created for each directory under `dataset/`.
- Verify that metadata records contain `file_count`, `last_ingested_at`, and a `status`.
- Check that notebook extraction recorded `extracted_tools`, `database_targets`, and `table_references`.
- Review the audit log for any `skipped` or `sanitized` decisions.

## Next step

After the ingestion pipeline is working, the next feature is the retriever stage. That stage will consume the cleaned metadata output and populate the notebook-level and user-level Qdrant collections.
