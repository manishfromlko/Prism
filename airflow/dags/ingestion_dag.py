from __future__ import annotations

from datetime import timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="kubeflow_workspace_ingestion",
    default_args=default_args,
    description="Run the Kubeflow workspace ingestion pipeline on a schedule.",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
    tags=["ingestion", "kubeflow"],
) as dag:
    run_ingestion = BashOperator(
        task_id="run_ingestion_pipeline",
        bash_command=(
            "cd /opt/airflow/repo && "
            "PYTHONPATH=/opt/airflow/repo python -m src.ingestion.cli "
            "--root /opt/airflow/repo/dataset --mode incremental"
        ),
    )

    run_ingestion
