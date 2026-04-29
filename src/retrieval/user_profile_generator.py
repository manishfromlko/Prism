"""Generate user profiles from the ingestion catalog."""

import json
import logging
import re
from collections import Counter
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Tools we recognise and surface as tags; anything else is filtered out.
KNOWN_TOOLS = {
    "pyspark", "spark", "pandas", "numpy", "sklearn", "matplotlib",
    "seaborn", "tensorflow", "keras", "pytorch", "torch", "langchain",
    "openai", "kafka", "airflow", "mlflow", "xgboost", "lightgbm",
    "catboost", "scipy", "statsmodels", "plotly", "bokeh", "dask",
    "ray", "huggingface", "transformers", "fastapi", "flask",
    "sqlalchemy", "redis", "elasticsearch", "nltk", "spacy",
}

TOOL_ALIASES = {
    "scikit-learn": "sklearn",
    "sk-learn": "sklearn",
    "torch": "pytorch",
    "tf": "tensorflow",
}

# Folder/path keywords → human-readable topic label
TOPIC_PATTERNS = [
    (r"recommender|recommendation", "Recommender Systems"),
    (r"time[_\s\-]?series|timeseries", "Time Series"),
    (r"deep[_\s]?learning|neural", "Deep Learning"),
    (r"natural[_\s]?language|nlp|text[_\s]?classi", "NLP"),
    (r"machine[_\s]?learning", "Machine Learning"),
    (r"stream|kafka|real[_\s]?time", "Stream Processing"),
    (r"data[_\s]?engineer|pipeline|etl", "Data Engineering"),
    (r"visual|seaborn|matplotlib|plot|chart", "Data Visualisation"),
    (r"predict|forecast|future[_\s]?value", "Forecasting"),
    (r"classif", "Classification"),
    (r"regression", "Regression"),
    (r"cluster", "Clustering"),
    (r"finance|stock|market|investor|fund", "Financial Analysis"),
    (r"getting|knowing|eda|exploratory", "Exploratory Analysis"),
    (r"sql|database|query", "SQL & Databases"),
]


def _normalize_tool(raw: str) -> Optional[str]:
    t = raw.lower().strip()
    t = TOOL_ALIASES.get(t, t)
    return t if t in KNOWN_TOOLS else None


def _infer_topics(paths: List[str]) -> List[str]:
    joined = " ".join(paths).lower()
    seen: set = set()
    topics: List[str] = []
    for pattern, label in TOPIC_PATTERNS:
        if label not in seen and re.search(pattern, joined):
            topics.append(label)
            seen.add(label)
    return topics[:4]


def _build_profile_text(
    user_id: str,
    topics: List[str],
    top_tools: List[str],
    nb_count: int,
    script_count: int,
    text_count: int,
) -> str:
    topic_str = ", ".join(topics) if topics else "data analysis"

    artifact_parts = []
    if nb_count:
        artifact_parts.append(f"{nb_count} notebook{'s' if nb_count != 1 else ''}")
    if script_count:
        artifact_parts.append(f"{script_count} script{'s' if script_count != 1 else ''}")
    if text_count:
        artifact_parts.append(f"{text_count} text file{'s' if text_count != 1 else ''}")
    artifact_str = ", ".join(artifact_parts) if artifact_parts else "various files"

    tool_str = ", ".join(top_tools[:5]) if top_tools else "general Python"

    text = (
        f"{user_id} works on {topic_str}. "
        f"Workspace includes {artifact_str}. "
        f"Primary tools: {tool_str}."
    )
    return text[:500]


def generate_profiles(catalog_path: str) -> List[Dict]:
    """
    Read catalog and return a profile dict for each workspace.

    Each dict has keys: id, user_id, user_profile, tags.
    The caller is responsible for adding the 'vector' key before indexing.
    """
    with open(catalog_path) as f:
        catalog = json.load(f)

    artifacts = catalog.get("artifacts", {})

    ws_data: Dict[str, Dict] = {}
    for art in artifacts.values():
        ws = art.get("workspace_id", "")
        if not ws:
            continue
        if ws not in ws_data:
            ws_data[ws] = {
                "tools": Counter(),
                "paths": [],
                "counts": {"notebook": 0, "script": 0, "text": 0},
            }
        ft = art.get("file_type", "")
        if ft in ws_data[ws]["counts"]:
            ws_data[ws]["counts"][ft] += 1
        ws_data[ws]["paths"].append(art.get("relative_path", ""))
        for raw_tool in art.get("classification", {}).get("metadata", {}).get("tools", []):
            norm = _normalize_tool(raw_tool)
            if norm:
                ws_data[ws]["tools"][norm] += 1

    profiles: List[Dict] = []
    for user_id, data in ws_data.items():
        top_tools = [t for t, _ in data["tools"].most_common(10)]
        topics = _infer_topics(data["paths"])
        c = data["counts"]

        profile_text = _build_profile_text(
            user_id, topics, top_tools,
            c.get("notebook", 0), c.get("script", 0), c.get("text", 0),
        )
        tags = ",".join(top_tools)

        profiles.append({
            "id": f"profile:{user_id}",
            "user_id": user_id,
            "user_profile": profile_text,
            "tags": tags,
        })
        logger.info(
            f"  {user_id}: {len(profile_text)} chars, tools=[{tags[:60]}...]"
        )

    return profiles
