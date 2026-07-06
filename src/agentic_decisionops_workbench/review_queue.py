"""Human-review queue artifacts for guarded DecisionOps outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


QUEUE_FIELDS = [
    "queue_id",
    "task_id",
    "agent",
    "priority",
    "status",
    "requested_action",
    "guardrail_hits",
    "evidence_ids",
    "owner_role",
    "sla_hours",
    "review_question",
]


def _priority(decision: dict[str, Any]) -> tuple[str, int]:
    hits = set(decision.get("guardrail_hits", []))
    if decision.get("refused") or {"deployment_no_go", "publication_restricted"} & hits:
        return "P0", 4
    if {
        "high_uncertainty_review",
        "cross_source_conflict_review",
        "impact_validation_not_ready",
        "impact_low_confidence_review",
    } & hits:
        return "P1", 8
    return "P2", 24


def _row(idx: int, decision: dict[str, Any]) -> dict[str, Any]:
    priority, sla_hours = _priority(decision)
    hits = decision.get("guardrail_hits", [])
    evidence = decision.get("evidence_ids", [])
    return {
        "queue_id": f"HRQ-{idx:04d}",
        "task_id": decision["task_id"],
        "agent": decision["agent"],
        "priority": priority,
        "status": "open",
        "requested_action": decision["action"],
        "guardrail_hits": "|".join(hits),
        "evidence_ids": "|".join(evidence),
        "owner_role": "operations_reviewer",
        "sla_hours": sla_hours,
        "review_question": decision["response"][:500],
    }


def build_review_queue(decisions: list[dict[str, Any]], output_root: Path) -> dict[str, Any]:
    reports = output_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    guarded = [
        decision
        for decision in decisions
        if decision.get("agent") == "guarded_decision_agent"
        and (decision.get("review_required") or decision.get("refused"))
    ]
    rows = [_row(idx + 1, decision) for idx, decision in enumerate(guarded)]

    csv_path = reports / "human_review_queue.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=QUEUE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    jsonl_path = reports / "human_review_queue.jsonl"
    jsonl_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )

    schema_path = reports / "review_queue_schema.json"
    schema = {
        "name": "human_review_queue",
        "primary_key": "queue_id",
        "fields": {field: "string" for field in QUEUE_FIELDS},
        "sla_policy": {"P0": "4h", "P1": "8h", "P2": "24h"},
        "status_values": ["open", "approved", "rejected", "needs_more_evidence"],
    }
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

    priorities: dict[str, int] = {}
    for row in rows:
        priorities[row["priority"]] = priorities.get(row["priority"], 0) + 1
    return {
        "queue_csv": str(csv_path),
        "queue_jsonl": str(jsonl_path),
        "schema": str(schema_path),
        "queue_items": len(rows),
        "priority_counts": priorities,
    }
