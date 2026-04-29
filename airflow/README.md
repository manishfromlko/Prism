# Airflow Packaging

This folder contains the Airflow DAG and instructions for scheduling the Kubeflow workspace ingestion pipeline.

## Start Airflow

```bash
docker compose -f docker-compose.airflow.yml up --build
```

Once the container starts, open the Airflow UI at:

http://localhost:8080

Use the default credentials:

- Username: `admin`
- Password: `admin`

## Ingestion DAG

The DAG file is located at `airflow/dags/ingestion_dag.py`.

It runs the ingestion CLI against the repository dataset volume:

```bash
PYTHONPATH=/opt/airflow/repo python -m src.ingestion.cli --root /opt/airflow/repo/dataset --mode incremental
```

## Notes

- The DAG uses the `SequentialExecutor` for local testing and packaging.
- The repository is mounted into the Airflow container at `/opt/airflow/repo`.
- The dataset is expected to be available inside the container at `/opt/airflow/repo/dataset`.
