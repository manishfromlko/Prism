# Databricks notebook — Task 2: generate LLM summaries for new artifacts
#
# Replaces: src/retrieval/artifact_summary_generator.py (local sequential loop)
# Source:   kubeflow.intelligence.artifact_chunks (Delta)
# Sink:     kubeflow.intelligence.artifact_summaries (Delta)

import os
import sys

SCOPE = "kubeflow-scope"
os.environ["DATABRICKS_HOST"]  = dbutils.secrets.get(SCOPE, "databricks-host")
os.environ["DATABRICKS_TOKEN"] = dbutils.secrets.get(SCOPE, "databricks-token")

sys.path.insert(0, "/Workspace/Repos/<your-repo>/project-1")

from src.retrieval.artifact_summary_generator import ArtifactSummaryGenerator

# Only process artifacts that don't already have a summary
new_artifacts = spark.sql("""
    SELECT DISTINCT
        c.artifact_id,
        FIRST(c.chunk_text)  AS sample_text,
        FIRST(c.file_type)   AS file_type
    FROM kubeflow.intelligence.artifact_chunks c
    LEFT JOIN kubeflow.intelligence.artifact_summaries s
      ON c.artifact_id = s.artifact_id
    WHERE s.artifact_id IS NULL
      AND c.file_type IN ('notebook', 'script', 'text')
    GROUP BY c.artifact_id
""").collect()

print(f"Generating summaries for {len(new_artifacts)} artifacts")

gen = ArtifactSummaryGenerator()
rows = []
for row in new_artifacts:
    try:
        summary = gen.generate(row.sample_text, row.file_type)
        rows.append({
            "artifact_id":      row.artifact_id,
            "artifact_summary": summary,
            "artifact_type":    row.file_type,
            "file_path":        row.artifact_id,
            "metadata":         {},
        })
    except Exception as e:
        print(f"SKIP summary {row.artifact_id}: {e}")

if rows:
    df = spark.createDataFrame(rows)
    df.write.mode("append").saveAsTable("kubeflow.intelligence.artifact_summaries")
    print(f"Wrote {len(rows)} summaries")
else:
    print("No new summaries needed")
