# Databricks notebook — Task 3: generate / refresh user profiles from summaries
#
# Replaces: src/retrieval/user_profile_from_summaries_generator.py (local loop)
# Source:   kubeflow.intelligence.artifact_summaries (Delta)
# Sink:     kubeflow.intelligence.user_profiles (Delta)

import os
import sys

SCOPE = "kubeflow-scope"
os.environ["DATABRICKS_HOST"]  = dbutils.secrets.get(SCOPE, "databricks-host")
os.environ["DATABRICKS_TOKEN"] = dbutils.secrets.get(SCOPE, "databricks-token")

sys.path.insert(0, "/Workspace/Repos/<your-repo>/project-1")

from src.retrieval.user_profile_from_summaries_generator import UserProfileFromSummariesGenerator

# Group summaries by user_id (first segment of artifact_id path)
summaries_by_user = spark.sql("""
    SELECT
        split(artifact_id, '/')[0]       AS user_id,
        collect_list(artifact_summary)   AS summaries
    FROM kubeflow.intelligence.artifact_summaries
    GROUP BY split(artifact_id, '/')[0]
""").collect()

print(f"Generating profiles for {len(summaries_by_user)} users")

gen = UserProfileFromSummariesGenerator()
rows = []
for row in summaries_by_user:
    try:
        profile = gen.generate(row.user_id, row.summaries)
        rows.append({
            "user_id":      row.user_id,
            "user_profile": profile,
            "display_name": row.user_id.replace(".", " ").title(),
            "metadata":     {},
        })
    except Exception as e:
        print(f"SKIP profile {row.user_id}: {e}")

if rows:
    df = spark.createDataFrame(rows)
    # Full refresh — profiles are derived entirely from summaries
    df.write.mode("overwrite").saveAsTable("kubeflow.intelligence.user_profiles")
    print(f"Wrote {len(rows)} user profiles")
else:
    print("No profiles generated")
