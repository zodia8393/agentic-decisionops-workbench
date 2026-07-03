"""Deterministic baseline and guarded agents for DecisionOps evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .guardrails import evaluate_guardrails
from .tools import DecisionTools, ToolResult
from .tracing import TraceRecorder


@dataclass
class AgentDecision:
    task_id: str
    agent: str
    action: str
    response: str
    tool_calls: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    guardrail_hits: list[str] = field(default_factory=list)
    review_required: bool = False
    refused: bool = False


def _tool_payload(results: list[ToolResult]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for result in results:
        payload.update(result.payload)
    return payload


def _is_incident_prompt(prompt: str) -> bool:
    return any(
        word in prompt
        for word in [
            "incident",
            "advisory",
            "alert",
            "사고",
            "cctv",
            "교통",
            "lane",
            "camera",
            "probe",
        ]
    )


def _is_review_queue_prompt(prompt: str) -> bool:
    return any(
        word in prompt
        for word in [
            "review queue",
            "human review queue",
            "queue candidate",
            "reviewer",
            "workload",
            "검토 대기",
            "검토 큐",
            "큐 형태",
            "사람이 승인",
        ]
    )


def _is_cross_domain_summary(prompt: str) -> bool:
    return (
        "두 decision surface" in prompt
        or "cross-domain" in prompt
        or ("operating risk" in prompt and "action" in prompt)
        or ("station" in prompt and "incident" in prompt and "요약" in prompt)
        or ("bike-share" in prompt and "traffic incident" in prompt)
        or "운영 ml" in prompt
        or "공통 blocker" in prompt
    )


def _is_impact_prompt(prompt: str) -> bool:
    return any(
        word in prompt
        for word in [
            "impact",
            "impact card",
            "ddareungi",
            "seoul",
            "따릉이",
            "완화량",
            "성과",
            "후보 조치",
            "대여소",
            "expected delta",
            "candidate units",
            "validation_not_ready",
        ]
    )


def _needs_incident_readiness(prompt: str) -> bool:
    return any(
        word in prompt
        for word in [
            "deploy",
            "배포",
            "readiness",
            "공개",
            "public",
            "publish",
            "release",
            "advisory",
            "alert",
            "게시",
            "시민 공개",
        ]
    )


class BaselineAgent:
    """An intentionally weak agent: it recommends from priority only."""

    name = "baseline_single_agent"

    def __init__(self, tools: DecisionTools, trace: TraceRecorder | None = None) -> None:
        self.tools = tools
        self.trace = trace

    def decide(self, task: dict[str, Any]) -> AgentDecision:
        task_id = str(task["id"])
        top = self.tools.top_station_risks(limit=3)
        self._record("tool_call", task_id, {"tool": top.name, "evidence": top.evidence_id})
        station = top.payload["stations"][0]
        prompt = str(task.get("prompt", "")).lower()
        if _is_incident_prompt(prompt):
            incident_top = self.tools.top_incident_risks(limit=1)
            self._record(
                "tool_call",
                task_id,
                {"tool": incident_top.name, "evidence": incident_top.evidence_id},
            )
            incident = incident_top.payload["incidents"][0]
            response = (
                f"{incident['incident_id']} 우선 대응을 권고합니다. "
                f"severity={incident['severity_score']}."
            )
            decision = AgentDecision(
                task_id=task_id,
                agent=self.name,
                action="recommend",
                response=response,
                tool_calls=[top.name, incident_top.name],
                evidence_ids=[top.evidence_id, incident_top.evidence_id],
                review_required=False,
                refused=False,
            )
            self._record("decision", task_id, decision.__dict__)
            return decision
        if "summary" in prompt or "요약" in prompt:
            action = "summarize"
        elif "deploy" in prompt or "배포" in prompt:
            action = "recommend"
        else:
            action = "recommend"
        response = (
            f"{station['station_short_name']} 우선 대응을 권고합니다. "
            f"risk_score={station['risk_score']}."
        )
        decision = AgentDecision(
            task_id=task_id,
            agent=self.name,
            action=action,
            response=response,
            tool_calls=[top.name],
            evidence_ids=[top.evidence_id],
            review_required=False,
            refused=False,
        )
        self._record("decision", task_id, decision.__dict__)
        return decision

    def _record(self, event_type: str, task_id: str, payload: dict[str, Any]) -> None:
        if self.trace:
            self.trace.record(event_type, task_id, {"agent": self.name, **payload})


class GuardedDecisionAgent:
    """Evidence-citing agent with read-only tools and guardrails."""

    name = "guarded_decision_agent"

    def __init__(self, tools: DecisionTools, trace: TraceRecorder | None = None) -> None:
        self.tools = tools
        self.trace = trace

    def decide(self, task: dict[str, Any]) -> AgentDecision:
        task_id = str(task["id"])
        prompt = str(task.get("prompt", "")).lower()
        tool_results: list[ToolResult] = []

        if _is_review_queue_prompt(prompt):
            tool_results.append(self.tools.review_queue_candidates())
        if _is_cross_domain_summary(prompt):
            tool_results.append(self.tools.operator_summary())
            tool_results.append(self.tools.readiness_status())
        if _is_impact_prompt(prompt) and not _is_cross_domain_summary(prompt):
            top_impact = self.tools.top_impact_cards(limit=5)
            tool_results.append(top_impact)
            cards = top_impact.payload["impact_cards"]
            if cards:
                if any(word in prompt for word in ["low-impact", "저영향", "낮은"]):
                    selected = min(
                        cards,
                        key=lambda row: float(row.get("candidate_units_addressed", 0.0) or 0.0),
                    )
                else:
                    selected = next(
                        (
                            row
                            for row in cards
                            if str(row.get("guardrail_state", "")) != "ready_for_review"
                        ),
                        cards[0],
                    )
                tool_results.append(self.tools.impact_evidence(selected.get("impact_card_id")))
        if _is_incident_prompt(prompt) and not _is_cross_domain_summary(prompt):
            if _needs_incident_readiness(prompt):
                tool_results.append(self.tools.incident_readiness())
            top_incident = self.tools.top_incident_risks(limit=5)
            tool_results.append(top_incident)
            if top_incident.payload["incidents"]:
                incident_rows = top_incident.payload["incidents"]
                if any(word in prompt for word in ["stale", "오래", "확정"]):
                    selected = max(
                        incident_rows,
                        key=lambda row: float(row.get("evidence_age_minutes", 0.0) or 0.0),
                    )
                else:
                    selected = incident_rows[0]
                first_incident = selected["incident_id"]
                tool_results.append(self.tools.incident_evidence(first_incident))
        if any(
            word in prompt
            for word in [
                "deploy",
                "배포",
                "readiness",
                "snapshot",
                "요약",
                "정리",
                "release",
                "launch",
                "blocker",
                "coverage",
                "공개",
                "올릴",
                "시민",
            ]
        ):
            tool_results.append(self.tools.readiness_status())
        station_summary_only = "snapshot" in prompt and ("요약" in prompt or "정리" in prompt)
        if (
            not _is_cross_domain_summary(prompt)
            and not _is_impact_prompt(prompt)
            and not station_summary_only
            and any(
                word in prompt
                for word in [
                    "station",
                    "재배치",
                    "불확실",
                    "dispatch",
                    "crew",
                    "rebalance",
                    "intervention",
                    "권고",
                    "실행",
                    "근거",
                    "현장팀",
                    "출동",
                    "발행",
                    "order",
                ]
            )
        ):
            top = self.tools.top_station_risks(limit=5)
            tool_results.append(top)
            first_station = top.payload["stations"][0]["station_short_name"]
            tool_results.append(self.tools.station_evidence(first_station))
        if not tool_results:
            tool_results.append(self.tools.operator_summary())

        for result in tool_results:
            self._record("tool_call", task_id, {"tool": result.name, "evidence": result.evidence_id})

        evidence = _tool_payload(tool_results)
        guardrail = evaluate_guardrails(task, evidence)
        if guardrail.hits:
            self._record(
                "guardrail",
                task_id,
                {
                    "hits": guardrail.hits,
                    "blocked": guardrail.blocked,
                    "review_required": guardrail.review_required,
                },
            )

        if guardrail.blocked:
            action = "refuse"
            refused = True
        elif guardrail.review_required:
            action = "escalate"
            refused = False
        elif (
            "요약" in prompt
            or "summary" in prompt
            or "정리" in prompt
            or _is_review_queue_prompt(prompt)
            or _is_cross_domain_summary(prompt)
        ):
            action = "summarize"
            refused = False
        else:
            action = "recommend"
            refused = False

        response = self._build_response(action, evidence, guardrail.hits)
        decision = AgentDecision(
            task_id=task_id,
            agent=self.name,
            action=action,
            response=response,
            tool_calls=[result.name for result in tool_results],
            evidence_ids=[result.evidence_id for result in tool_results],
            guardrail_hits=guardrail.hits,
            review_required=guardrail.review_required,
            refused=refused,
        )
        self._record("decision", task_id, decision.__dict__)
        return decision

    def _build_response(
        self, action: str, evidence: dict[str, Any], guardrail_hits: list[str]
    ) -> str:
        readiness = evidence.get("readiness", {})
        deployment = evidence.get("deployment", {})
        station = evidence.get("station") or (evidence.get("stations") or [{}])[0]
        incident = evidence.get("incident") or (evidence.get("incidents") or [{}])[0]
        impact_card = evidence.get("impact_card") or (evidence.get("impact_cards") or [{}])[0]
        incident_deployment = evidence.get("incident_deployment", {})
        queue_candidates = evidence.get("review_queue_candidates", [])
        citation = (
            f"근거: station={station.get('station_short_name', 'n/a')}, "
            f"risk={station.get('risk_score', 'n/a')}, "
            f"incident={incident.get('incident_id', 'n/a')}, "
            f"severity={incident.get('severity_score', 'n/a')}, "
            f"impact={impact_card.get('impact_card_id', 'n/a')}, "
            f"units={impact_card.get('candidate_units_addressed', 'n/a')}, "
            f"confidence={impact_card.get('confidence_score', 'n/a')}, "
            f"impact_validation={impact_card.get('validation_status', 'n/a')}, "
            f"snapshot={readiness.get('snapshot_count', 'n/a')}/"
            f"{readiness.get('target_snapshots', 'n/a')}, "
            f"deploy={deployment.get('decision', incident_deployment.get('decision', 'n/a'))}."
        )
        if action == "refuse":
            return f"자동 실행 또는 배포를 거부합니다. guardrail={guardrail_hits}. {citation}"
        if action == "escalate":
            return f"Human review가 필요합니다. guardrail={guardrail_hits}. {citation}"
        if action == "summarize":
            if queue_candidates:
                return f"검토 큐 후보 {len(queue_candidates)}건을 생성했습니다. {citation}"
            return f"현재 readiness는 {readiness.get('decision', 'n/a')}입니다. {citation}"
        if impact_card:
            return f"{impact_card.get('impact_card_id', 'n/a')} impact card를 검토합니다. {citation}"
        if incident:
            return f"{incident.get('incident_id', 'n/a')} 우선 대응을 검토합니다. {citation}"
        return f"{station.get('station_short_name', 'n/a')} 우선 대응을 권고합니다. {citation}"

    def _record(self, event_type: str, task_id: str, payload: dict[str, Any]) -> None:
        if self.trace:
            self.trace.record(event_type, task_id, {"agent": self.name, **payload})
