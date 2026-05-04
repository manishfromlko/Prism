# Databricks notebook — Task 4: trigger Vector Search index sync
#
# Run after every ingestion cycle so the indexes reflect the latest Delta tables.
# TRIGGERED pipeline type — sync is on-demand; switch to CONTINUOUS for real-time.

import os

SCOPE = "kubeflow-scope"
os.environ["DATABRICKS_HOST"]  = dbutils.secrets.get(SCOPE, "databricks-host")
os.environ["DATABRICKS_TOKEN"] = dbutils.secrets.get(SCOPE, "databricks-token")

from databricks.vector_search.client import VectorSearchClient

ENDPOINT = "kubeflow-intelligence-endpoint"
INDEXES = [
    "kubeflow.intelligence.artifact_chunks_index",
    "kubeflow.intelligence.artifact_summaries_index",
    "kubeflow.intelligence.user_profiles_index",
]

vsc = VectorSearchClient(
    workspace_url=os.environ["DATABRICKS_HOST"],
    personal_access_token=os.environ["DATABRICKS_TOKEN"],
)

for index_name in INDEXES:
    try:
        idx = vsc.get_index(ENDPOINT, index_name)
        idx.sync()
        print(f"Sync triggered: {index_name}")
    except Exception as e:
        print(f"ERROR syncing {index_name}: {e}")
        raise

print("All indexes synced")
