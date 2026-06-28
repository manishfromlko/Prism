"""Response-quality critic specialist agent."""

from __future__ import annotations

from typing import Dict

from .types import AgentContext


class CriticAgent:
    """Applies lightweight guardrails before an answer leaves the orchestrator."""

    name = "critic"
    evidence_intents = {"DOC_QA", "ARTIFACT_SEARCH", "USER_SEARCH", "HYBRID"}

    def review(self, context: AgentContext, result: Dict) -> Dict:
        intent = result.get("intent")
        if intent not in self.evidence_intents:
            context.add_step(self.name, "skip", reason="non_retrieval_intent")
            return result

        evidence_count = (
            len(result.get("artifacts", []))
            + len(result.get("users", []))
            + len(result.get("sources", []))
        )
        answer = result.get("answer", "").lower()
        looks_empty = "couldn't find" in answer or "could not find" in answer

        if evidence_count == 0 and looks_empty and result.get("confidence", 0) > 0.7:
            result["confidence"] = 0.65
            context.add_step(
                self.name,
                "lower_confidence",
                reason="empty_retrieval_answer",
                evidence_count=evidence_count,
            )
            return result

        context.add_step(self.name, "approve", evidence_count=evidence_count)
        return result
