#!/usr/bin/env python3
"""Download compact public data/ML examples into realistic user workspaces."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "workspaces"
DEFAULT_WORKSPACES = {
    "aarav.mehra",
    "aarav.mehraa",
    "ananya2.iyer",
    "anaya.iyer",
    "diya.shah",
}

SOURCES = [
    {
        "workspace": "aarav.mehra",
        "focus": "Spark ETL and word-count exploration",
        "license": "Apache-2.0",
        "source_project": "Apache Spark",
        "url": "https://raw.githubusercontent.com/apache/spark/master/examples/src/main/python/wordcount.py",
        "path": "spark/wordcount.py",
    },
    {
        "workspace": "ananya.iyer",
        "focus": "Spark SQL data discovery",
        "license": "Apache-2.0",
        "source_project": "Apache Spark",
        "url": "https://raw.githubusercontent.com/apache/spark/master/examples/src/main/python/sql/basic.py",
        "path": "spark_sql/basic.py",
    },
    {
        "workspace": "arjun.menon",
        "focus": "Spark datasource profiling",
        "license": "Apache-2.0",
        "source_project": "Apache Spark",
        "url": "https://raw.githubusercontent.com/apache/spark/master/examples/src/main/python/sql/datasource.py",
        "path": "spark_sql/datasource.py",
    },
    {
        "workspace": "diya.shah",
        "focus": "Customer clustering with Spark ML",
        "license": "Apache-2.0",
        "source_project": "Apache Spark",
        "url": "https://raw.githubusercontent.com/apache/spark/master/examples/src/main/python/ml/kmeans_example.py",
        "path": "spark_ml/kmeans_example.py",
    },
    {
        "workspace": "ishaan.kapoor",
        "focus": "Classification model comparison in Spark",
        "license": "Apache-2.0",
        "source_project": "Apache Spark",
        "url": "https://raw.githubusercontent.com/apache/spark/master/examples/src/main/python/ml/random_forest_classifier_example.py",
        "path": "spark_ml/random_forest_classifier_example.py",
    },
    {
        "workspace": "kavya.nair",
        "focus": "Logistic regression experiment tracking",
        "license": "Apache-2.0",
        "source_project": "Apache Spark",
        "url": "https://raw.githubusercontent.com/apache/spark/master/examples/src/main/python/ml/logistic_regression_with_elastic_net.py",
        "path": "spark_ml/logistic_regression_with_elastic_net.py",
    },
    {
        "workspace": "meera.krishnan",
        "focus": "Feature pipeline prototyping",
        "license": "Apache-2.0",
        "source_project": "Apache Spark",
        "url": "https://raw.githubusercontent.com/apache/spark/master/examples/src/main/python/ml/pipeline_example.py",
        "path": "spark_ml/pipeline_example.py",
    },
    {
        "workspace": "neha.gupta",
        "focus": "Recommendation modeling with ALS",
        "license": "Apache-2.0",
        "source_project": "Apache Spark",
        "url": "https://raw.githubusercontent.com/apache/spark/master/examples/src/main/python/ml/als_example.py",
        "path": "spark_ml/als_example.py",
    },
    {
        "workspace": "priya.patel",
        "focus": "Distributed k-means with Spark MLlib",
        "license": "Apache-2.0",
        "source_project": "Apache Spark",
        "url": "https://raw.githubusercontent.com/apache/spark/master/examples/src/main/python/mllib/k_means_example.py",
        "path": "mllib/k_means_example.py",
    },
    {
        "workspace": "rahul.nair",
        "focus": "Collaborative filtering in Spark MLlib",
        "license": "Apache-2.0",
        "source_project": "Apache Spark",
        "url": "https://raw.githubusercontent.com/apache/spark/master/examples/src/main/python/mllib/recommendation_example.py",
        "path": "mllib/recommendation_example.py",
    },
    {
        "workspace": "rohit.sharma",
        "focus": "Streaming text analytics",
        "license": "Apache-2.0",
        "source_project": "Apache Spark",
        "url": "https://raw.githubusercontent.com/apache/spark/master/examples/src/main/python/streaming/network_wordcount.py",
        "path": "streaming/network_wordcount.py",
    },
    {
        "workspace": "saanvi.reddy",
        "focus": "MLflow regression experiment",
        "license": "Apache-2.0",
        "source_project": "MLflow",
        "url": "https://raw.githubusercontent.com/mlflow/mlflow/master/examples/sklearn_elasticnet_wine/train.py",
        "path": "mlflow/sklearn_elasticnet_wine_train.py",
    },
    {
        "workspace": "siddharth.rao",
        "focus": "Hyperparameter search workflow",
        "license": "Apache-2.0",
        "source_project": "MLflow",
        "url": "https://raw.githubusercontent.com/mlflow/mlflow/master/examples/hyperparam/train.py",
        "path": "mlflow/hyperparam_train.py",
    },
    {
        "workspace": "tanvi.desai",
        "focus": "PyTorch autologging experiment",
        "license": "Apache-2.0",
        "source_project": "MLflow",
        "url": "https://raw.githubusercontent.com/mlflow/mlflow/master/examples/pytorch/MNIST/mnist_autolog_example.py",
        "path": "mlflow/mnist_autolog_example.py",
    },
    {
        "workspace": "vikram.singh",
        "focus": "Classifier benchmarking",
        "license": "BSD-3-Clause",
        "source_project": "scikit-learn",
        "url": "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/examples/classification/plot_classifier_comparison.py",
        "path": "sklearn/classifier_comparison.py",
    },
    {
        "workspace": "zoya.khan",
        "focus": "Clustering digits for discovery",
        "license": "BSD-3-Clause",
        "source_project": "scikit-learn",
        "url": "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/examples/cluster/plot_kmeans_digits.py",
        "path": "sklearn/kmeans_digits.py",
    },
    {
        "workspace": "nisha.banerjee",
        "focus": "Grid search model selection",
        "license": "BSD-3-Clause",
        "source_project": "scikit-learn",
        "url": "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/examples/model_selection/plot_grid_search_digits.py",
        "path": "sklearn/grid_search_digits.py",
    },
    {
        "workspace": "karan.malhotra",
        "focus": "Feature importance analysis",
        "license": "BSD-3-Clause",
        "source_project": "scikit-learn",
        "url": "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/examples/ensemble/plot_forest_importances.py",
        "path": "sklearn/forest_importances.py",
    },
    {
        "workspace": "pooja.joshi",
        "focus": "Feature selection pipelines",
        "license": "BSD-3-Clause",
        "source_project": "scikit-learn",
        "url": "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/examples/feature_selection/plot_feature_selection_pipeline.py",
        "path": "sklearn/feature_selection_pipeline.py",
    },
    {
        "workspace": "aditya.kulkarni",
        "focus": "Preprocessing and scaling analysis",
        "license": "BSD-3-Clause",
        "source_project": "scikit-learn",
        "url": "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/examples/preprocessing/plot_scaling_importance.py",
        "path": "sklearn/scaling_importance.py",
    },
    {
        "workspace": "priya2.patel",
        "focus": "Distributed linear regression with Spark MLlib",
        "license": "Apache-2.0",
        "source_project": "Apache Spark",
        "url": "https://raw.githubusercontent.com/apache/spark/master/examples/src/main/python/mllib/linear_regression_with_sgd_example.py",
        "path": "mllib/linear_regression_with_sgd_example.py",
    },
    {
        "workspace": "priyam.patel",
        "focus": "Decision-tree classification in Spark MLlib",
        "license": "Apache-2.0",
        "source_project": "Apache Spark",
        "url": "https://raw.githubusercontent.com/apache/spark/master/examples/src/main/python/mllib/decision_tree_classification_example.py",
        "path": "mllib/decision_tree_classification_example.py",
    },
    {
        "workspace": "priyanka.patel",
        "focus": "Frequent-pattern mining for data discovery",
        "license": "Apache-2.0",
        "source_project": "Apache Spark",
        "url": "https://raw.githubusercontent.com/apache/spark/master/examples/src/main/python/mllib/fpgrowth_example.py",
        "path": "mllib/fpgrowth_example.py",
    },
    {
        "workspace": "ananya2.iyer",
        "focus": "Principal component analysis with distributed matrices",
        "license": "Apache-2.0",
        "source_project": "Apache Spark",
        "url": "https://raw.githubusercontent.com/apache/spark/master/examples/src/main/python/mllib/pca_rowmatrix_example.py",
        "path": "mllib/pca_rowmatrix_example.py",
    },
    {
        "workspace": "anaya.iyer",
        "focus": "Text feature extraction using TF-IDF",
        "license": "Apache-2.0",
        "source_project": "Apache Spark",
        "url": "https://raw.githubusercontent.com/apache/spark/master/examples/src/main/python/mllib/tf_idf_example.py",
        "path": "mllib/tf_idf_example.py",
    },
    {
        "workspace": "arjun2.menon",
        "focus": "Lasso model selection for regression",
        "license": "BSD-3-Clause",
        "source_project": "scikit-learn",
        "url": "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/examples/linear_model/plot_lasso_model_selection.py",
        "path": "sklearn/lasso_model_selection.py",
    },
    {
        "workspace": "aarav.mehraa",
        "focus": "Principal component visualization for discovery",
        "license": "BSD-3-Clause",
        "source_project": "scikit-learn",
        "url": "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/examples/decomposition/plot_pca_iris.py",
        "path": "sklearn/pca_iris.py",
    },
    {
        "workspace": "kavya.nairr",
        "focus": "Density-based clustering and anomaly discovery",
        "license": "BSD-3-Clause",
        "source_project": "scikit-learn",
        "url": "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/examples/cluster/plot_dbscan.py",
        "path": "sklearn/dbscan.py",
    },
    {
        "workspace": "rahul.nayar",
        "focus": "Gradient boosting regression and feature importance",
        "license": "BSD-3-Clause",
        "source_project": "scikit-learn",
        "url": "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/examples/ensemble/plot_gradient_boosting_regression.py",
        "path": "sklearn/gradient_boosting_regression.py",
    },
    {
        "workspace": "rohit.sharmma",
        "focus": "MLflow logistic regression experiment logging",
        "license": "Apache-2.0",
        "source_project": "MLflow",
        "url": "https://raw.githubusercontent.com/mlflow/mlflow/master/examples/sklearn_logistic_regression/train.py",
        "path": "mlflow/sklearn_logistic_regression_train.py",
    },
]


def curl_download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["curl", "-L", "-f", "--retry", "3", "-o", str(destination), url],
        check=True,
    )


def write_readme(workspace: Path, item: dict[str, str]) -> None:
    readme = workspace / "README.md"
    readme.write_text(
        "\n".join(
            [
                f"# {item['workspace']}",
                "",
                f"Focus: {item['focus']}.",
                "",
                "This workspace is seeded from a compact public example so the legacy chatbot has realistic code artifacts for retrieval and user-profile discovery.",
                "",
                "## Source",
                "",
                f"- Project: {item['source_project']}",
                f"- License: {item['license']}",
                f"- URL: {item['url']}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download public example workspaces into data/workspaces."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download every known public workspace locally. By default only the five Git-tracked seed workspaces are downloaded.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_sources = SOURCES if args.all else [
        source for source in SOURCES if source["workspace"] in DEFAULT_WORKSPACES
    ]

    manifest = []
    for item in selected_sources:
        workspace = DATASET / item["workspace"]
        destination = workspace / item["path"]
        curl_download(item["url"], destination)
        write_readme(workspace, item)
        manifest.append(
            {
                "workspace": item["workspace"],
                "focus": item["focus"],
                "local_path": str(destination.relative_to(ROOT)),
                "source_project": item["source_project"],
                "source_url": item["url"],
                "license": item["license"],
            }
        )

    (DATASET / "public_sources_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    (DATASET / "ATTRIBUTIONS.md").write_text(
        "# Public Source Attributions\n\n"
        "The added workspaces below use compact examples from permissively licensed public repositories.\n\n"
        + "\n".join(
            f"- `{entry['workspace']}`: {entry['source_project']} ({entry['license']}), {entry['source_url']}"
            for entry in manifest
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
