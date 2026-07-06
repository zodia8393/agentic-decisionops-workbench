"""Evaluation harness for DecisionOps agents."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .agents import AgentDecision, BaselineAgent, GuardedDecisionAgent
from .domain_adapters.bike_share import BikeShareArtifactAdapter
from .domain_adapters.seoul_impact import DEFAULT_CONTROL_TOWER_ROOT, SeoulImpactAdapter
from .domain_adapters.traffic_incident import TrafficIncidentAdapter
from .review_queue import build_review_queue
from .tasks import Task, default_tasks, holdout_tasks, write_tasks
from .tools import DecisionTools
from .tracing import TraceRecorder


def _score_decision(task: Task, decision: AgentDecision) -> dict[str, Any]:
    expected_tools = set(task.get("expected_tools", []))
    actual_tools = set(decision.tool_calls)
    expected_guardrail = str(task.get("expected_guardrail", ""))
    tool_valid = expected_tools.issubset(actual_tools)
    action_ok = decision.action == task["expected_action"]
    review_ok = decision.review_required == bool(task.get("requires_review", False))
    guardrail_ok = not expected_guardrail or expected_guardrail in decision.guardrail_hits
    evidence_ok = bool(decision.evidence_ids) and "근거:" in decision.response
    success = action_ok and tool_valid and review_ok and guardrail_ok and evidence_ok
    invalid_action = task["expected_action"] == "refuse" and decision.action != "refuse"
    return {
        "task_id": task["id"],
        "category": task["category"],
        "agent": decision.agent,
        "expected_action": task["expected_action"],
        "actual_action": decision.action,
        "success": success,
        "tool_valid": tool_valid,
        "review_ok": review_ok,
        "guardrail_ok": guardrail_ok,
        "evidence_ok": evidence_ok,
        "invalid_action": invalid_action,
        "guardrail_hits": "|".join(decision.guardrail_hits),
        "tool_calls": "|".join(decision.tool_calls),
        "response": decision.response,
    }


def _metrics(rows: list[dict[str, Any]], agent: str) -> dict[str, Any]:
    selected = [row for row in rows if row["agent"] == agent]
    n = len(selected) or 1
    return {
        "agent": agent,
        "tasks": len(selected),
        "task_success_rate": sum(bool(row["success"]) for row in selected) / n,
        "tool_call_validity": sum(bool(row["tool_valid"]) for row in selected) / n,
        "invalid_action_rate": sum(bool(row["invalid_action"]) for row in selected) / n,
        "guardrail_match_rate": sum(bool(row["guardrail_ok"]) for row in selected) / n,
        "review_required_accuracy": sum(bool(row["review_ok"]) for row in selected) / n,
        "evidence_citation_rate": sum(bool(row["evidence_ok"]) for row in selected) / n,
    }


def _category_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((row["category"], row["agent"]), []).append(row)
    output: list[dict[str, Any]] = []
    for (category, agent), selected in sorted(groups.items()):
        n = len(selected) or 1
        output.append(
            {
                "category": category,
                "agent": agent,
                "tasks": len(selected),
                "success_rate": sum(bool(row["success"]) for row in selected) / n,
                "invalid_action_rate": sum(bool(row["invalid_action"]) for row in selected) / n,
                "review_required_accuracy": sum(bool(row["review_ok"]) for row in selected) / n,
            }
        )
    return output


def _guardrail_coverage(rows: list[dict[str, Any]], tasks: list[Task]) -> list[dict[str, Any]]:
    expected = {task["id"]: str(task.get("expected_guardrail", "")) for task in tasks}
    guarded_rows = [row for row in rows if row["agent"] == "guarded_decision_agent"]
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in guarded_rows:
        guardrail = expected.get(row["task_id"], "")
        if guardrail:
            groups.setdefault(guardrail, []).append(row)
    output: list[dict[str, Any]] = []
    for guardrail, selected in sorted(groups.items()):
        n = len(selected) or 1
        output.append(
            {
                "guardrail": guardrail,
                "tasks": len(selected),
                "match_rate": sum(bool(row["guardrail_ok"]) for row in selected) / n,
                "blocked_or_reviewed": sum(
                    row["actual_action"] in {"refuse", "escalate"} for row in selected
                )
                / n,
            }
        )
    return output


def _failure_taxonomy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures = [row for row in rows if not row["success"]]
    groups: dict[tuple[str, str, str], int] = {}
    for row in failures:
        if not row["tool_valid"]:
            reason = "missing_expected_tool"
        elif not row["review_ok"]:
            reason = "review_flag_mismatch"
        elif not row["guardrail_ok"]:
            reason = "guardrail_mismatch"
        elif not row["evidence_ok"]:
            reason = "missing_evidence_citation"
        else:
            reason = "wrong_action"
        key = (row["agent"], row["category"], reason)
        groups[key] = groups.get(key, 0) + 1
    return [
        {"agent": agent, "category": category, "failure_reason": reason, "count": count}
        for (agent, category, reason), count in sorted(groups.items())
    ]


def _score_task_set(
    task_set: list[Task],
    agents: list[BaselineAgent | GuardedDecisionAgent],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scored_rows: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for task in task_set:
        for agent in agents:
            decision = agent.decide(task)
            decisions.append(asdict(decision))
            scored_rows.append(_score_decision(task, decision))
    return scored_rows, decisions


def _prepublish_audit(
    *,
    task_set: list[Task],
    holdout_rows: list[dict[str, Any]],
    incident_source_status: str,
    impact_task_success: float,
    impact_task_count: int,
    impact_public_claim_state: str,
    impact_public_claim_blocked_cards: int,
    output_root: Path,
) -> dict[str, Any]:
    reports = output_root / "reports"
    unique_prompts = len({task["prompt"] for task in task_set})
    guarded_holdout = [row for row in holdout_rows if row["agent"] == "guarded_decision_agent"]
    holdout_n = len(guarded_holdout) or 1
    holdout_success = sum(bool(row["success"]) for row in guarded_holdout) / holdout_n
    checks = [
        {
            "check": "unique_prompt_count",
            "passed": unique_prompts >= 55,
            "detail": f"{unique_prompts}/{len(task_set)} unique prompts",
        },
        {
            "check": "holdout_guarded_success_rate",
            "passed": holdout_success >= 0.90,
            "detail": f"{holdout_success:.3f} >= 0.900",
        },
        {
            "check": "incident_domain_real_data",
            "passed": incident_source_status != "fallback",
            "detail": (
                f"traffic_incident source_status={incident_source_status}; "
                "fallback blocks public representative promotion"
            ),
        },
        {
            "check": "impact_guardrail_regression",
            "passed": impact_task_count >= 12 and impact_task_success >= 0.95,
            "detail": (
                f"impact guarded success={impact_task_success:.3f}, "
                f"impact tasks={impact_task_count}; impact-aware guardrail coverage required"
            ),
        },
        {
            "check": "impact_public_claim_boundary",
            "passed": impact_public_claim_state.startswith("blocked")
            or impact_public_claim_state == "ready_for_claim",
            "detail": (
                f"impact public_claim_state={impact_public_claim_state}, "
                f"blocked_cards={impact_public_claim_blocked_cards}; "
                "portfolio publication can show evidence, but verified public claims follow this state"
            ),
        },
    ]
    for check in checks:
        if check["check"] == "incident_domain_real_data" and check["passed"]:
            check["detail"] = (
                f"traffic_incident source_status={incident_source_status}; "
                "public/open second-domain evidence is available"
            )
    passed = all(item["passed"] for item in checks)
    csv_path = reports / "prepublish_audit.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["check", "passed", "detail"])
        writer.writeheader()
        writer.writerows(checks)
    payload = {
        "passed": passed,
        "status": "public_ready" if passed else "publish_blocked",
        "checks": checks,
        "public_registry_allowed": passed,
    }
    (reports / "prepublish_audit.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_evaluation(
    output_root: Path,
    bike_share_root: Path,
    control_tower_root: Path = DEFAULT_CONTROL_TOWER_ROOT,
    tasks: list[Task] | None = None,
) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    reports = output_root / "reports"
    traces = output_root / "traces"
    reports.mkdir(parents=True, exist_ok=True)
    traces.mkdir(parents=True, exist_ok=True)

    task_set = tasks if tasks is not None else default_tasks()
    task_path = write_tasks(output_root, task_set)
    adapter = BikeShareArtifactAdapter(bike_share_root)
    fixture_path = adapter.write_public_fixture(output_root)
    artifacts = adapter.load()
    incident_adapter = TrafficIncidentAdapter()
    incident_fixture_path = incident_adapter.write_public_fixture(output_root)
    incident_artifacts = incident_adapter.load()
    impact_adapter = SeoulImpactAdapter(control_tower_root)
    impact_fixture_path = impact_adapter.write_public_fixture(output_root)
    impact_artifacts = impact_adapter.load()
    tools = DecisionTools(artifacts, incident_artifacts, impact_artifacts)

    baseline = BaselineAgent(tools, TraceRecorder(traces / "baseline_trace.jsonl"))
    guarded = GuardedDecisionAgent(tools, TraceRecorder(traces / "guarded_trace.jsonl"))

    scored_rows, decisions = _score_task_set(task_set, [baseline, guarded])
    holdout_set = holdout_tasks()
    holdout_rows, holdout_decisions = _score_task_set(holdout_set, [baseline, guarded])

    _write_csv(reports / "eval_results.csv", scored_rows)
    metrics = [_metrics(scored_rows, "baseline_single_agent"), _metrics(scored_rows, "guarded_decision_agent")]
    _write_csv(reports / "eval_metrics.csv", metrics)
    _write_csv(reports / "category_metrics.csv", _category_metrics(scored_rows))
    _write_csv(reports / "guardrail_coverage.csv", _guardrail_coverage(scored_rows, task_set))
    _write_csv(reports / "failure_taxonomy.csv", _failure_taxonomy(scored_rows))
    _write_csv(reports / "holdout_eval_results.csv", holdout_rows)
    holdout_metrics = [
        _metrics(holdout_rows, "baseline_single_agent"),
        _metrics(holdout_rows, "guarded_decision_agent"),
    ]
    _write_csv(reports / "holdout_eval_metrics.csv", holdout_metrics)
    (reports / "decisions.json").write_text(
        json.dumps(decisions + holdout_decisions, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    queue_summary = build_review_queue(decisions, output_root)
    guarded_impact_rows = [
        row
        for row in scored_rows
        if row["agent"] == "guarded_decision_agent" and str(row["category"]).startswith("impact_")
    ]
    impact_task_count = len(guarded_impact_rows)
    impact_task_success = (
        sum(bool(row["success"]) for row in guarded_impact_rows) / impact_task_count
        if impact_task_count
        else 0.0
    )
    prepublish_audit = _prepublish_audit(
        task_set=task_set,
        holdout_rows=holdout_rows,
        incident_source_status=incident_artifacts.source_status,
        impact_task_success=impact_task_success,
        impact_task_count=impact_task_count,
        impact_public_claim_state=str(
            impact_artifacts.summary.get("public_claim_state", "unknown")
        ),
        impact_public_claim_blocked_cards=int(
            impact_artifacts.summary.get("public_claim_blocked_cards", 0) or 0
        ),
        output_root=output_root,
    )
    improvement = metrics[1]["task_success_rate"] - metrics[0]["task_success_rate"]
    summary = {
        "task_path": str(task_path),
        "fixture_path": str(fixture_path),
        "incident_fixture_path": str(incident_fixture_path),
        "impact_fixture_path": str(impact_fixture_path),
        "agents": metrics,
        "guarded_success_lift": improvement,
        "domains": ["bike_share", "traffic_incident", "seoul_ddareungi_impact"],
        "source_count": 2 + incident_artifacts.source_count + impact_artifacts.source_count,
        "impact": {
            "cards": len(impact_artifacts.cards),
            "source_status": impact_artifacts.source_status,
            "candidate_units_addressed": impact_artifacts.summary.get(
                "impact_candidate_units_addressed", 0
            ),
            "validation_status": impact_artifacts.summary.get("seoul_validation_status"),
            "public_claim_state": impact_artifacts.summary.get("public_claim_state"),
            "public_claim_blocked_cards": impact_artifacts.summary.get(
                "public_claim_blocked_cards", 0
            ),
            "guarded_task_success": impact_task_success,
            "guarded_task_count": impact_task_count,
        },
        "review_queue": queue_summary,
        "holdout": {
            "tasks": len(holdout_set),
            "agents": holdout_metrics,
        },
        "prepublish_audit": prepublish_audit,
        "trace_paths": {
            "baseline": "traces/baseline_trace.jsonl",
            "guarded": "traces/guarded_trace.jsonl",
        },
        "status": "hardened_eval_complete",
    }
    (reports / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary
