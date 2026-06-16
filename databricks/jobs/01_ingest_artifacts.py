# Databricks notebook — Task 1: scan Unity Catalog Volume, extract, chunk, write to Delta
#
# Replaces: src/ingestion/pipeline.py + src/retrieval/document_loader.py + indexer.py
# Source:   /Volumes/kubeflow/intelligence/workspace_files/
# Sink:     kubeflow.intelligence.artifact_chunks (Delta table)
#
# Pipeline:
#   IngestionPipeline  → scans volume, classifies files, writes catalog JSON
#   DocumentLoader     → reads catalog, extracts text, applies DocumentGuard
#   TextProcessor      → splits text into chunks
#   → write rows to Delta table (Vector Search embeds on next sync)

# COMMAND ----------
import os
import sys

SCOPE = "kubeflow-scope"
os.environ["DATABRICKS_HOST"]  = dbutils.secrets.get(SCOPE, "databricks-host")
os.environ["DATABRICKS_TOKEN"] = dbutils.secrets.get(SCOPE, "databricks-token")

REPO_PATH    = "/Workspace/Repos/manishfromlko@gmail.com/project-1"  # adjust if needed
VOLUME_PATH  = "/Volumes/kubeflow/intelligence/workspace_files"

sys.path.insert(0, REPO_PATH)

# COMMAND ----------
# Step 1 — run ingestion pipeline to scan the volume and write catalog JSON
# Catalog is saved to /Volumes/.../workspace_files/.ingestion/ingestion_catalog.json

from src.ingestion.pipeline import IngestionPipeline

pipeline = IngestionPipeline(root_path=VOLUME_PATH, mode="full")
pipeline.run()

catalog_path = f"{VOLUME_PATH}/.ingestion/ingestion_catalog.json"
print(f"Catalog written to: {catalog_path}")

# COMMAND ----------
# Step 2 — load documents from catalog, extract text, apply DocumentGuard

from src.retrieval.document_loader import DocumentLoader
from src.retrieval.config import RetrievalConfig

config = RetrievalConfig.from_env()
loader = DocumentLoader(catalog_path=catalog_path, config=config)
documents = loader.load_documents(apply_guardrails=True)

print(f"Documents loaded: {len(documents)}")
for doc in documents[:3]:
    print(f"  {doc.metadata.get('artifact_id')}  [{doc.metadata.get('type')}]  "
          f"{len(doc.page_content)} chars")

# COMMAND ----------
# Step 3 — chunk each document

from src.retrieval.text_processor import TextProcessor

processor = TextProcessor(config=config)
rows = []

for doc in documents:
    artifact_id = doc.metadata.get("artifact_id", "")
    file_type    = doc.metadata.get("type", "text")
    file_path    = doc.metadata.get("path", "")
    workspace_id = doc.metadata.get("workspace_id", "")
    sha256       = doc.metadata.get("content_hash", "")

    chunks = processor.split_text(doc.page_content, content_type=file_type)
    for i, chunk_text in enumerate(chunks):
        rows.append({
            "chunk_id":    f"{artifact_id}::{i}",
            "artifact_id": artifact_id,
            "chunk_text":  chunk_text,
            "chunk_index": i,
            "file_path":   file_path,
            "file_type":   file_type,
            "sha256_hash": sha256,
        })

print(f"Total chunks: {len(rows)}")
print(f"Total artifacts: {len(set(r['artifact_id'] for r in rows))}")

# COMMAND ----------
# Step 4 — inspect before writing (sanity check)

display(spark.createDataFrame(rows[:20]))

# COMMAND ----------
# Step 5 — upsert into Delta table
# Delete stale chunks for re-ingested artifacts, then append fresh rows

if rows:
    df = spark.createDataFrame(rows)
    new_ids = list(set(r["artifact_id"] for r in rows))

    # Delete old chunks for any artifact being re-ingested
    ids_sql = ", ".join(f"'{i}'" for i in new_ids)
    spark.sql(f"""
        DELETE FROM kubeflow.intelligence.artifact_chunks
        WHERE artifact_id IN ({ids_sql})
    """)

    df.write.mode("append").saveAsTable("kubeflow.intelligence.artifact_chunks")
    print(f"Wrote {len(rows)} chunks from {len(new_ids)} artifacts")
else:
    print("No documents extracted — check volume path and catalog")
