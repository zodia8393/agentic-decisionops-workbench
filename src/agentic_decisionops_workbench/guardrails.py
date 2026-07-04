"""Decision guardrails for agentic operations recommendations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GuardrailResult:
    blocked: bool
    review_required: bool
    hits: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)


def evaluate_guardrails(task: dict[str, Any], evidence: dict[str, Any]) -> GuardrailResult:
    prompt = str(task.get("prompt", "")).lower()
    hits: list[str] = []
    rationale: list[str] = []
    blocked = False
    review_required = bool(task.get("requires_review", False))
    summary_request = any(word in prompt for word in ["요약", "summary", "정리"])

    readiness = evidence.get("readiness", {})
    deployment = evidence.get("deployment", {})
    station = evidence.get("station", {})
    incident = evidence.get("incident", {})
    incident_deployment = evidence.get("incident_deployment", {})

    publication_request = any(
        word in prompt
        for word in [
            "deploy",
            "배포",
            "공개",
            "public",
            "publish",
            "release",
            "advisory",
            "alert",
            "게시",
            "시민 공개",
            "launch",
        ]
    )
    if publication_request and not summary_request:
        if deployment and deployment.get("decision") != "GO":
            blocked = True
            review_required = True
            hits.append("deployment_no_go")
            rationale.append("public deploy readiness is not GO")
        if incident_deployment and incident_deployment.get("decision") != "GO":
            blocked = True
            review_required = True
            hits.append("deployment_no_go")
            rationale.append("incident publication/deploy readiness is not GO")

    unsafe_execution_request = any(
        word in prompt
        for word in [
            "dispatch",
            "send a crew",
            "crew",
            "rebalance",
            "execute",
            "order",
            "실행",
            "자동 실행",
            "현장팀",
            "출동",
            "발행",
            "작업 완료",
        ]
    )
    if any(word in prompt for word in ["자동 실행 대신", "자동 실행하지", "자동 실행하지 말고"]):
        unsafe_execution_request = False
    if unsafe_execution_request:
        blocked = True
        review_required = True
        hits.append("unsafe_write_action")
        rationale.append("workbench exposes read-only recommendations, not execution tools")

    risk = float(station.get("risk_score", 0.0) or 0.0)
    pressure = float(station.get("inventory_pressure", 0.0) or 0.0)
    if risk >= 5.0 or pressure >= 0.9 or "불확실" in prompt:
        review_required = True
        hits.append("high_uncertainty_review")
        rationale.append("high station risk or uncertainty requires human review")

    severity = float(incident.get("severity_score", 0.0) or 0.0)
    conflict = float(incident.get("sensor_conflict_rate", 0.0) or 0.0)
    evidence_age = float(incident.get("evidence_age_minutes", 0.0) or 0.0)
    if severity >= 7.0 or conflict >= 0.2:
        review_required = True
        hits.append("cross_source_conflict_review")
        rationale.append("incident severity or cross-source conflict requires review")
    if evidence_age > 60:
        review_required = True
        hits.append("stale_evidence_review")
        rationale.append("incident evidence is stale")
    if incident and not incident.get("public_release_allowed", True):
        if publication_request:
            blocked = True
            review_required = True
            hits.append("publication_restricted")
            rationale.append("incident publication requires operator confirmation")

    missing_evidence_request = any(
        word in prompt
        for word in [
            "근거 없이",
            "without evidence",
            "without citations",
            "without citation",
            "근거는 숨기고",
            "출처는 숨기고",
            "출처를 빼고",
            "evidence citation 없이",
            "tool evidence는 생략",
            "근거 인용 없이",
        ]
    )
    if missing_evidence_request:
        blocked = True
        review_required = True
        hits.append("missing_evidence_request")
        rationale.append("recommendations must cite tool evidence")

    if readiness.get("ready_for_prospective_validation") is False and "확정" in prompt:
        review_required = True
        hits.append("prospective_validation_not_ready")
        rationale.append("prospective validation is not ready")

    return GuardrailResult(
        blocked=blocked,
        review_required=review_required,
        hits=sorted(set(hits)),
        rationale=rationale,
    )
