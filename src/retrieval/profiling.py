"""Profiling and insights generation for workspaces."""

import logging
from collections import Counter
from typing import Dict, List, Any, Optional

from .config import RetrievalConfig
from .document_loader import DocumentLoader

logger = logging.getLogger(__name__)


class WorkspaceProfiler:
    """Generates profiling insights for workspaces."""

    def __init__(self, config: RetrievalConfig, catalog_path: str):
        self.config = config
        self.loader = DocumentLoader(catalog_path, config)

    def profile_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Generate comprehensive profile for a workspace."""
        try:
            catalog = self.loader.load_catalog()
            artifacts = self._get_workspace_artifacts(workspace_id, catalog)
            if not artifacts:
                return self._empty_profile(workspace_id)

            return {
                "workspace_id": workspace_id,
                "artifact_count": len(artifacts),
                "top_tools": self._analyze_tools(artifacts),
                "top_topics": self._analyze_topics(artifacts),
                "collaboration_patterns": self._analyze_collaboration(artifacts),
                "last_updated": self._get_last_updated(artifacts),
                "file_types": self._analyze_file_types(artifacts),
                "code_metrics": self._analyze_code_metrics(artifacts),
                "recent_artifacts": self._get_recent_artifacts(workspace_id, artifacts),
            }
        except Exception as e:
            logger.error(f"Failed to profile workspace {workspace_id}: {e}")
            return self._empty_profile(workspace_id)

    def _get_workspace_artifacts(self, workspace_id: str, catalog: Dict) -> List[Dict]:
        """Get all artifacts for a workspace from a pre-loaded catalog."""
        artifacts = catalog.get('artifacts', {})
        return [a for a in artifacts.values() if a.get('workspace_id') == workspace_id]

    def _empty_profile(self, workspace_id: str) -> Dict[str, Any]:
        return {
            "workspace_id": workspace_id,
            "artifact_count": 0,
            "top_tools": [],
            "top_topics": [],
            "collaboration_patterns": {
                "total_artifacts": 0, "notebooks_count": 0,
                "scripts_count": 0, "avg_file_size": 0.0,
            },
            "last_updated": None,
            "file_types": {},
            "code_metrics": {"total_lines": 0, "avg_lines_per_file": 0.0, "python_files": 0},
            "recent_artifacts": [],
        }

    def _analyze_tools(self, artifacts: List[Dict]) -> List[Dict[str, Any]]:
        """Count tools from pre-extracted classification metadata."""
        tool_counter: Counter = Counter()
        for artifact in artifacts:
            tools = artifact.get('classification', {}).get('metadata', {}).get('tools', [])
            for tool in tools:
                if tool:
                    tool_counter[tool.lower()] += 1
        return [{"tool": t, "count": c} for t, c in tool_counter.most_common(10)]

    def _analyze_topics(self, artifacts: List[Dict]) -> List[Dict[str, Any]]:
        """Derive topics from tools detected in classification metadata."""
        topic_map = {
            "machine_learning": ["sklearn", "scikit", "xgboost", "lightgbm", "mlflow"],
            "deep_learning": ["tensorflow", "pytorch", "torch", "keras"],
            "data_analysis": ["pandas", "numpy", "matplotlib", "seaborn", "plotly"],
            "big_data": ["pyspark", "spark", "hadoop", "dask"],
            "nlp": ["nltk", "spacy", "transformers", "bert", "langchain"],
            "sql_analytics": ["sql", "postgres", "mysql", "snowflake", "bigquery"],
        }
        topic_scores: Counter = Counter()
        for artifact in artifacts:
            tools = {t.lower() for t in artifact.get('classification', {}).get('metadata', {}).get('tools', [])}
            for topic, keywords in topic_map.items():
                score = sum(1 for k in keywords if k in tools)
                if score:
                    topic_scores[topic] += score

        total = sum(topic_scores.values())
        if not total:
            return []
        return [
            {"topic": t.replace('_', ' ').title(), "relevance": round(score / total, 3)}
            for t, score in topic_scores.most_common(5)
        ]

    def _analyze_collaboration(self, artifacts: List[Dict]) -> Dict[str, Any]:
        """Summarise artifact composition and average file size."""
        total_bytes = sum(a.get('size_bytes', a.get('size', 0)) for a in artifacts)
        return {
            "total_artifacts": len(artifacts),
            "notebooks_count": sum(
                1 for a in artifacts if a.get('file_type', a.get('type', '')) == 'notebook'
            ),
            "scripts_count": sum(
                1 for a in artifacts if a.get('file_type', a.get('type', '')) in ('python', 'script')
            ),
            # Return in KB so the UI label "KB" is correct
            "avg_file_size": round(total_bytes / len(artifacts) / 1024, 2) if artifacts else 0.0,
        }

    def _get_last_updated(self, artifacts: List[Dict]) -> Optional[str]:
        timestamps = [a.get('last_modified_at') for a in artifacts if a.get('last_modified_at')]
        return max(timestamps) if timestamps else None

    def _analyze_file_types(self, artifacts: List[Dict]) -> Dict[str, int]:
        type_counter: Counter = Counter()
        for artifact in artifacts:
            t = artifact.get('file_type', artifact.get('type', 'unknown'))
            type_counter[t] += 1
        return dict(type_counter)

    def _analyze_code_metrics(self, artifacts: List[Dict]) -> Dict[str, Any]:
        """Count lines in Python/script files by reading from disk."""
        python_artifacts = [
            a for a in artifacts
            if a.get('file_type', a.get('type', '')) in ('python', 'script')
        ]
        total_lines = 0
        for artifact in python_artifacts:
            source_path = artifact.get('capture_source', {}).get('source_path', '')
            if source_path:
                try:
                    with open(source_path, 'r', encoding='utf-8', errors='ignore') as f:
                        total_lines += sum(1 for _ in f)
                except (OSError, IOError):
                    pass
        return {
            "total_lines": total_lines,
            "avg_lines_per_file": round(total_lines / len(python_artifacts), 1) if python_artifacts else 0.0,
            "python_files": len(python_artifacts),
        }

    def _get_recent_artifacts(self, workspace_id: str, artifacts: List[Dict], limit: int = 10) -> List[Dict]:
        """Return the most recently modified artifacts as ArtifactMetadata dicts."""
        sorted_arts = sorted(artifacts, key=lambda a: a.get('last_modified_at', ''), reverse=True)
        result = []
        for a in sorted_arts[:limit]:
            filename = a.get('file_name', '') or a.get('relative_path', '').split('/')[-1]
            result.append({
                'workspace_id': workspace_id,
                'workspace_name': workspace_id,
                'filename': filename,
                'file_path': a.get('relative_path', ''),
                'file_type': a.get('file_type', a.get('type', '')),
                'file_size': a.get('size_bytes', a.get('size', 0)),
                'modified_at': a.get('last_modified_at', ''),
                'created_at': a.get('last_modified_at', ''),
            })
        return result
