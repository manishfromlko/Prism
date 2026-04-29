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
        """Initialize profiler.

        Args:
            config: Retrieval configuration
            catalog_path: Path to ingestion catalog
        """
        self.config = config
        self.loader = DocumentLoader(catalog_path, config)

    def profile_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Generate comprehensive profile for a workspace.

        Args:
            workspace_id: Workspace identifier

        Returns:
            Profile dictionary with insights
        """
        try:
            # Load workspace artifacts
            artifacts = self._get_workspace_artifacts(workspace_id)
            if not artifacts:
                return self._empty_profile(workspace_id)

            # Analyze artifacts
            profile = {
                "workspace_id": workspace_id,
                "artifact_count": len(artifacts),
                "top_tools": self._analyze_tools(artifacts),
                "top_topics": self._analyze_topics(artifacts),
                "collaboration_patterns": self._analyze_collaboration(artifacts),
                "last_updated": self._get_last_updated(artifacts),
                "file_types": self._analyze_file_types(artifacts),
                "code_metrics": self._analyze_code_metrics(artifacts),
            }

            return profile

        except Exception as e:
            logger.error(f"Failed to profile workspace {workspace_id}: {e}")
            return self._empty_profile(workspace_id)

    def _get_workspace_artifacts(self, workspace_id: str) -> List[Dict]:
        """Get all artifacts for a workspace.

        Args:
            workspace_id: Workspace identifier

        Returns:
            List of artifact dictionaries
        """
        try:
            catalog = self.loader.load_catalog()
            artifacts = catalog.get('artifacts', {})
            return [
                artifact for artifact in artifacts.values()
                if artifact.get('workspace_id') == workspace_id
            ]
        except Exception:
            return []

    def _empty_profile(self, workspace_id: str) -> Dict[str, Any]:
        """Return empty profile structure.

        Args:
            workspace_id: Workspace identifier

        Returns:
            Empty profile dictionary
        """
        return {
            "workspace_id": workspace_id,
            "artifact_count": 0,
            "top_tools": [],
            "top_topics": [],
            "collaboration_patterns": {},
            "last_updated": None,
            "file_types": {},
            "code_metrics": {},
        }

    def _analyze_tools(self, artifacts: List[Dict]) -> List[Dict[str, Any]]:
        """Analyze tool and library usage.

        Args:
            artifacts: List of artifacts

        Returns:
            List of top tools with usage counts
        """
        tool_counter = Counter()

        for artifact in artifacts:
            content = artifact.get('content', '').lower()

            # Detect common tools/libraries
            tools = {
                'pandas': 'pandas' in content,
                'numpy': 'numpy' in content or 'np.' in content,
                'scikit-learn': 'sklearn' in content or 'scikit' in content,
                'tensorflow': 'tensorflow' in content or 'tf.' in content,
                'pytorch': 'torch' in content or 'pytorch' in content,
                'matplotlib': 'matplotlib' in content or 'plt.' in content,
                'seaborn': 'seaborn' in content,
                'jupyter': artifact.get('type') == 'notebook',
                'spark': 'spark' in content or 'pyspark' in content,
                'mlflow': 'mlflow' in content,
            }

            for tool, detected in tools.items():
                if detected:
                    tool_counter[tool] += 1

        # Return top 10 tools
        return [
            {"tool": tool, "count": count}
            for tool, count in tool_counter.most_common(10)
        ]

    def _analyze_topics(self, artifacts: List[Dict]) -> List[Dict[str, Any]]:
        """Analyze main topics/themes in the workspace.

        Args:
            artifacts: List of artifacts

        Returns:
            List of top topics with relevance scores
        """
        # Simple keyword-based topic analysis
        # In production, you'd use topic modeling or clustering

        topic_keywords = {
            "machine_learning": ["machine learning", "ml", "model", "training", "prediction"],
            "data_analysis": ["data analysis", "eda", "exploratory", "statistics", "visualization"],
            "deep_learning": ["neural network", "deep learning", "cnn", "rnn", "transformer"],
            "computer_vision": ["computer vision", "image", "opencv", "cnn", "detection"],
            "nlp": ["nlp", "natural language", "text", "bert", "transformer"],
            "time_series": ["time series", "forecasting", "temporal", "sequence"],
            "clustering": ["clustering", "unsupervised", "k-means", "pca"],
            "regression": ["regression", "linear", "prediction", "forecast"],
        }

        topic_scores = Counter()

        for artifact in artifacts:
            content = artifact.get('content', '').lower()

            for topic, keywords in topic_keywords.items():
                score = sum(1 for keyword in keywords if keyword in content)
                if score > 0:
                    topic_scores[topic] += score

        # Return top topics with normalized scores
        total_score = sum(topic_scores.values())
        if total_score == 0:
            return []

        return [
            {
                "topic": topic.replace('_', ' ').title(),
                "relevance": score / total_score
            }
            for topic, score in topic_scores.most_common(5)
        ]

    def _analyze_collaboration(self, artifacts: List[Dict]) -> Dict[str, Any]:
        """Analyze collaboration patterns.

        Args:
            artifacts: List of artifacts

        Returns:
            Dictionary with collaboration insights
        """
        patterns = {
            "total_artifacts": len(artifacts),
            "notebooks_count": sum(1 for a in artifacts if a.get('type') == 'notebook'),
            "scripts_count": sum(1 for a in artifacts if a.get('type') == 'python'),
            "avg_file_size": sum(a.get('size', 0) for a in artifacts) / len(artifacts) if artifacts else 0,
        }

        return patterns

    def _get_last_updated(self, artifacts: List[Dict]) -> Optional[str]:
        """Get the last updated timestamp for the workspace.

        Args:
            artifacts: List of artifacts

        Returns:
            Latest modification timestamp
        """
        timestamps = [
            artifact.get('modified_at')
            for artifact in artifacts
            if artifact.get('modified_at')
        ]

        return max(timestamps) if timestamps else None

    def _analyze_file_types(self, artifacts: List[Dict]) -> Dict[str, int]:
        """Analyze file type distribution.

        Args:
            artifacts: List of artifacts

        Returns:
            Dictionary with file type counts
        """
        type_counter = Counter()
        for artifact in artifacts:
            artifact_type = artifact.get('type', 'unknown')
            type_counter[artifact_type] += 1

        return dict(type_counter)

    def _analyze_code_metrics(self, artifacts: List[Dict]) -> Dict[str, Any]:
        """Analyze code quality metrics.

        Args:
            artifacts: List of artifacts

        Returns:
            Dictionary with code metrics
        """
        metrics = {
            "total_lines": 0,
            "avg_lines_per_file": 0,
            "python_files": 0,
        }

        python_artifacts = [a for a in artifacts if a.get('type') == 'python']
        if python_artifacts:
            total_lines = 0
            for artifact in python_artifacts:
                content = artifact.get('content', '')
                lines = len(content.split('\n'))
                total_lines += lines

            metrics.update({
                "total_lines": total_lines,
                "avg_lines_per_file": total_lines / len(python_artifacts),
                "python_files": len(python_artifacts),
            })

        return metrics