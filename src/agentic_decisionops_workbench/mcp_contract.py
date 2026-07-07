"""MCP-style resource, tool, and prompt contract for DecisionOps."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def contract() -> dict[str, Any]:
    return {
        "name": "agentic-decisionops-workbench",
        "version": "0.4.0",
        "resources": [
            {
                "name": "bike_share_decision_surface",
                "description": "Public-safe derived forecast, uncertainty, inventory, readiness, and priority artifacts.",
                "mime_type": "application/json",
            },
            {
                "name": "decision_trace_log",
                "description": "JSONL trace events for task, tool call, guardrail, and final decision inspection.",
                "mime_type": "application/jsonl",
            },
            {
                "name": "traffic_incident_decision_surface",
                "description": "Public NY 511 incident severity, evidence lag, source ambiguity, and publication gate artifacts.",
                "mime_type": "application/json",
            },
            {
                "name": "human_review_queue",
                "description": "Queue of guarded decisions that require reviewer approval, refusal, or more evidence.",
                "mime_type": "text/csv",
            },
            {
                "name": "seoul_impact_decision_surface",
                "description": "Control Tower Seoul Ddareungi impact cards with validation, confidence, blocker, and public-claim state.",
                "mime_type": "application/json",
            },
        ],
        "tools": [
            {
                "name": "top_station_risks",
                "input_schema": {"limit": "integer"},
                "output_schema": {"stations": "array"},
                "safety": "read_only",
            },
            {
                "name": "station_evidence",
                "input_schema": {"station_short_name": "string"},
                "output_schema": {"station": "object"},
                "safety": "read_only",
            },
            {
                "name": "readiness_status",
                "input_schema": {},
                "output_schema": {"readiness": "object", "deployment": "object"},
                "safety": "read_only",
            },
            {
                "name": "operator_summary",
                "input_schema": {},
                "output_schema": {"summary": "string"},
                "safety": "read_only",
            },
            {
                "name": "top_incident_risks",
                "input_schema": {"limit": "integer"},
                "output_schema": {"incidents": "array"},
                "safety": "read_only",
            },
            {
                "name": "incident_evidence",
                "input_schema": {"incident_id": "string"},
                "output_schema": {"incident": "object"},
                "safety": "read_only",
            },
            {
                "name": "incident_readiness",
                "input_schema": {},
                "output_schema": {"incident_readiness": "object", "incident_deployment": "object"},
                "safety": "read_only",
            },
            {
                "name": "review_queue_candidates",
                "input_schema": {},
                "output_schema": {"review_queue_candidates": "array"},
                "safety": "read_only",
            },
            {
                "name": "top_impact_cards",
                "input_schema": {"limit": "integer"},
                "output_schema": {"impact_cards": "array", "impact_summary": "object"},
                "safety": "read_only",
            },
            {
                "name": "impact_evidence",
                "input_schema": {"impact_card_id": "string"},
                "output_schema": {"impact_card": "object"},
                "safety": "read_only",
            },
        ],
        "prompts": [
            {
                "name": "guarded_decision_recommendation",
                "description": "Use evidence, cite tool outputs, and escalate when readiness or uncertainty blocks automation.",
            },
            {
                "name": "human_review_brief",
                "description": "Summarize blocker, evidence, and requested human decision.",
            },
            {
                "name": "cross_domain_ops_summary",
                "description": "Summarize risk across station and incident decision surfaces without exposing raw private evidence.",
            },
        ],
        "http_api": [
            {
                "method": "GET",
                "path": "/health",
                "description": "Runtime health, source status, artifact availability, and LLM attachment state.",
            },
            {
                "method": "GET",
                "path": "/v1/contract",
                "description": "This read-only resource/tool/prompt/API contract for external planner pipelines.",
            },
            {
                "method": "POST",
                "path": "/v1/tools/{tool_name}",
                "description": "Read-only evidence tool call with bounded arguments.",
            },
            {
                "method": "POST",
                "path": "/v1/decisions",
                "description": "Guarded decision endpoint for operator prompts or external planner outputs.",
            },
            {
                "method": "POST",
                "path": "/v1/evaluations/run",
                "description": "Run deterministic regression evaluation and write reports before/after planner changes.",
            },
        ],
    }


def write_contract(output_root: Path) -> tuple[Path, Path]:
    reports = output_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    payload = contract()
    json_path = reports / "mcp_contract.json"
    md_path = reports / "mcp_contract.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# MCP-style DecisionOps Contract", ""]
    for section in ["resources", "tools", "prompts", "http_api"]:
        lines.append(f"## {section.title()}")
        for item in payload[section]:
            if section == "http_api":
                lines.append(
                    f"- `{item['method']} {item['path']}`: {item['description']}"
                )
            else:
                lines.append(
                    f"- `{item['name']}`: {item.get('description', item.get('safety', ''))}"
                )
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
