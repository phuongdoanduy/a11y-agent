"""Custom eval metrics for the a11y-agent.

Registers ``audit_plan_quality`` as a code-based custom metric that ADK eval
can invoke via ``codeConfig.name = "tests.eval.custom_metrics.audit_plan_quality"``.

The metric is a heuristic scorer (no LLM call) that checks 5 criteria:
  1. Platform detected (ios / android / web / cross-platform)
  2. File glob patterns present
  3. At least 3 WCAG 2.1 AA criteria listed
  4. Tool use evidence in intermediate_data
  5. At least 2 platform-specific priority areas

Score is normalised to 0–1 (raw 0–5 divided by 5).
"""

from __future__ import annotations

from typing import Optional

from google.adk.evaluation.eval_case import Invocation
from google.adk.evaluation.eval_metrics import EvalMetric
from google.adk.evaluation.evaluator import (
    EvalStatus,
    EvaluationResult,
    PerInvocationResult,
)


async def audit_plan_quality(
    eval_metric: EvalMetric,
    actual_invocations: list[Invocation],
    expected_invocations: Optional[list[Invocation]],
    conversation_scenario: Optional[object] = None,
) -> EvaluationResult:
    """Evaluate the quality of an accessibility audit plan.

    ADK calls this async function when the metric name matches the
    ``codeConfig.name`` entry in the eval config JSON.
    """
    scores: list[float] = []
    per_inv: list[PerInvocationResult] = []

    for idx, actual in enumerate(actual_invocations):
        response_text = _text_from_invocation(actual)
        raw = _score_plan(response_text)
        norm = raw / 5.0
        scores.append(norm)
        per_inv.append(
            PerInvocationResult(
                actual_invocation=actual,
                expected_invocation=(
                    expected_invocations[idx]
                    if expected_invocations and idx < len(expected_invocations)
                    else None
                ),
                score=norm,
                eval_status=EvalStatus.PASSED if raw >= 3 else EvalStatus.FAILED,
            )
        )

    overall = sum(scores) / len(scores) if scores else 0.0
    return EvaluationResult(
        overall_score=overall,
        overall_eval_status=(
            EvalStatus.PASSED if overall >= eval_metric.threshold else EvalStatus.FAILED
        ),
        per_invocation_results=per_inv,
    )


# ── helpers ──────────────────────────────────────────────────────────

def _text_from_invocation(inv: Invocation) -> str:
    """Extract all text parts from an invocation's final_response."""
    if inv.final_response and inv.final_response.parts:
        return "\n".join(p.text for p in inv.final_response.parts if p.text)
    return ""


def _score_plan(text: str) -> float:
    """Score plan quality on a 0–5 scale."""
    score = 0.0
    low = text.lower()

    # 1. Platform detection
    if any(p in low for p in ("ios", "android", "web", "cross-platform")):
        score += 1

    # 2. File glob patterns
    if any(
        g in low
        for g in ("*.tsx", "*.ts", "*.swift", "*.kt", "*.xml", "**/*", "*.xib", "*.storyboard")
    ):
        score += 1

    # 3. At least 3 WCAG 2.1 AA criteria
    wcag_hits = sum(
        1
        for c in (
            "1.1.1", "1.3.1", "1.4.3", "1.4.6", "1.4.11",
            "2.1.1", "2.4.3", "2.4.6", "2.4.7", "2.5.8",
            "3.1.1", "3.2.3", "3.3.1", "3.3.2",
            "4.1.2", "4.1.3",
        )
        if c in low
    )
    if wcag_hits >= 3:
        score += 1

    # 4. Tool use evidence (scope_analyzer mentioned)
    if "scope_analyzer" in low or "scope analyzer" in low:
        score += 1

    # 5. At least 2 platform-specific priority areas
    priority_hits = sum(
        1
        for kw in (
            "voiceover", "talkback", "keyboard", "aria",
            "contrast", "focus", "form", "image", "label",
            "dynamic type", "touch target", "alt text",
        )
        if kw in low
    )
    if priority_hits >= 2:
        score += 1

    return score
