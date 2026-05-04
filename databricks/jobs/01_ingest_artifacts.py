# Databricks notebook — Task 1: scan Unity Catalog Volume, extract, guard, write to Delta
#
# Replaces: src/ingestion/pipeline.py (local filesystem walk + Milvus insert)
# Source:   /Volumes/kubeflow/intelligence/workspace_files/
# Sink:     kubeflow.intelligence.artifact_chunks (Delta table)

import os
import sys

# Inject secrets from Databricks secret scope into env
SCOPE = "kubeflow-scope"
os.environ["DATABRICKS_HOST"]  = dbutils.secrets.get(SCOPE, "databricks-host")
os.environ["DATABRICKS_TOKEN"] = dbutils.secrets.get(SCOPE, "databricks-token")

sys.path.insert(0, "/Workspace/Repos/<your-repo>/project-1")  # adjust to your repo path

from src.ingestion.extractors import extract_artifact
from src.ingestion.guards import DocumentGuard
from src.ingestion.utils import compute_file_hash

VOLUME_PATH = "/Volumes/kubeflow/intelligence/workspace_files"

rows = []
for root, _dirs, files in os.walk(VOLUME_PATH):
    for fname in files:
        path = os.path.join(root, fname)
        try:
            artifact = extract_artifact(path)
            if artifact is None:
                continue
            if not DocumentGuard.is_safe(artifact):
                continue
            sha256 = compute_file_hash(path)
            for chunk in artifact.chunks:
                rows.append({
                    "chunk_id":    f"{artifact.artifact_id}::{chunk.index}",
                    "artifact_id": artifact.artifact_id,
                    "chunk_text":  chunk.text,
                    "chunk_index": chunk.index,
                    "file_path":   path,
                    "file_type":   artifact.file_type,
                    "sha256_hash": sha256,
                    "metadata":    artifact.metadata,
                })
        except Exception as e:
            print(f"SKIP {path}: {e}")

if rows:
    df = spark.createDataFrame(rows)
    # Upsert: delete existing chunks for updated files then append
    existing = spark.table("kubeflow.intelligence.artifact_chunks")
    new_ids = [r["artifact_id"] for r in rows]
    spark.sql(f"""
        DELETE FROM kubeflow.intelligence.artifact_chunks
        WHERE artifact_id IN ({','.join(repr(i) for i in set(new_ids))})
    """)
    df.write.mode("append").saveAsTable("kubeflow.intelligence.artifact_chunks")
    print(f"Wrote {len(rows)} chunks from {len(set(new_ids))} artifacts")
else:
    print("No new artifacts found")
