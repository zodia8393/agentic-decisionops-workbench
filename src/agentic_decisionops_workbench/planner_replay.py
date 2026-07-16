"""Provider-neutral planner replay contract for deterministic ablation runs."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .agents import AgentDecision
from .tasks import Task


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLANNER_REPLAY_PATH = PROJECT_ROOT / "data" / "public" / "planner_replay_fixture.json"
RAW_PLANNER_AGENT = "planner_replay_raw"
GUARDED_PLANNER_AGENT = "planner_replay_guarded"


@dataclass(frozen=True)
class PlannerReplayRecord:
    """One previously captured or synthetic planner candidate output."""

    task_id: str
    task_prompt_sha256: str
    action: str
    response: str
    tool_calls: list[str]
    evidence_ids: list[str]
    review_required: bool


@dataclass(frozen=True)
class PlannerReplayDataset:
    """Replay metadata and records with claim-scope provenance."""

    schema_version: str
    fixture_id: str
    source_kind: str
    provider: str
    model: str
    captured_at_utc: str
    is_real_llm: bool
    claim_scope: str
    dataset_sha256: str
    records: list[PlannerReplayRecord]


def prompt_sha256(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _string_list(value: Any, field: str, task_id: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{task_id}: {field} must be a list of non-empty strings")
    return list(value)


def load_planner_replay(path: Path = DEFAULT_PLANNER_REPLAY_PATH) -> PlannerReplayDataset:
    """Load and validate a replay dataset without making provider calls."""

    raw = path.read_bytes()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("planner replay root must be an object")
    if payload.get("schema_version") != "1.0":
        raise ValueError("planner replay schema_version must be 1.0")

    metadata_fields = [
        "fixture_id",
        "source_kind",
        "provider",
        "model",
        "captured_at_utc",
        "claim_scope",
    ]
    for field in metadata_fields:
        if not isinstance(payload.get(field), str) or not payload[field]:
            raise ValueError(f"planner replay {field} must be a non-empty string")
    if not isinstance(payload.get("is_real_llm"), bool):
        raise ValueError("planner replay is_real_llm must be a boolean")
    if payload["is_real_llm"] and payload["source_kind"] != "recorded_llm":
        raise ValueError("real LLM replay must use source_kind=recorded_llm")
    if not payload["is_real_llm"] and payload["claim_scope"] != "harness_only":
        raise ValueError("non-LLM replay must use claim_scope=harness_only")

    rows = payload.get("records")
    if not isinstance(rows, list) or not rows:
        raise ValueError("planner replay records must be a non-empty list")

    records: list[PlannerReplayRecord] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("planner replay record must be an object")
        task_id = str(row.get("task_id", ""))
        if not task_id:
            raise ValueError("planner replay task_id must be non-empty")
        if task_id in seen:
            raise ValueError(f"duplicate planner replay task_id: {task_id}")
        seen.add(task_id)
        task_hash = str(row.get("task_prompt_sha256", ""))
        if len(task_hash) != 64 or any(ch not in "0123456789abcdef" for ch in task_hash):
            raise ValueError(f"{task_id}: task_prompt_sha256 must be lowercase SHA-256")
        action = str(row.get("action", ""))
        response = str(row.get("response", ""))
        if not action or not response:
            raise ValueError(f"{task_id}: action and response must be non-empty")
        if not isinstance(row.get("review_required"), bool):
            raise ValueError(f"{task_id}: review_required must be a boolean")
        records.append(
            PlannerReplayRecord(
                task_id=task_id,
                task_prompt_sha256=task_hash,
                action=action,
                response=response,
                tool_calls=_string_list(row.get("tool_calls"), "tool_calls", task_id),
                evidence_ids=_string_list(row.get("evidence_ids"), "evidence_ids", task_id),
                review_required=row["review_required"],
            )
        )

    return PlannerReplayDataset(
        schema_version="1.0",
        fixture_id=payload["fixture_id"],
        source_kind=payload["source_kind"],
        provider=payload["provider"],
        model=payload["model"],
        captured_at_utc=payload["captured_at_utc"],
        is_real_llm=payload["is_real_llm"],
        claim_scope=payload["claim_scope"],
        dataset_sha256=hashlib.sha256(raw).hexdigest(),
        records=records,
    )


def validate_replay_alignment(dataset: PlannerReplayDataset, tasks: list[Task]) -> None:
    """Fail on task-set drift so replay comparisons remain reproducible."""

    task_by_id = {str(task["id"]): task for task in tasks}
    record_by_id = {record.task_id: record for record in dataset.records}
    missing = sorted(set(task_by_id) - set(record_by_id))
    unknown = sorted(set(record_by_id) - set(task_by_id))
    if missing or unknown:
        raise ValueError(f"planner replay task mismatch: missing={missing}, unknown={unknown}")
    for task_id, task in task_by_id.items():
        actual_hash = prompt_sha256(str(task["prompt"]))
        if record_by_id[task_id].task_prompt_sha256 != actual_hash:
            raise ValueError(f"planner replay prompt drift: {task_id}")


def raw_planner_decision(record: PlannerReplayRecord) -> AgentDecision:
    """Convert a replay record into the unguarded candidate decision."""

    return AgentDecision(
        task_id=record.task_id,
        agent=RAW_PLANNER_AGENT,
        action=record.action,
        response=record.response,
        tool_calls=record.tool_calls,
        evidence_ids=record.evidence_ids,
        review_required=record.review_required,
        refused=record.action == "refuse",
    )


def task_with_planner_output(
    task: Task,
    planner_action: str | None,
    planner_response: str | None,
) -> Task:
    """Expose planner candidates to the same deterministic boundary as the API."""

    prompt_parts = [str(task.get("prompt", ""))]
    if planner_action:
        prompt_parts.append(f"planner_action: {planner_action}")
    if planner_response:
        prompt_parts.append(f"planner_response: {planner_response}")
    augmented = dict(task)
    augmented["prompt"] = "\n".join(prompt_parts)
    return augmented
