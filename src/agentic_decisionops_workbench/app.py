"""FastAPI boundary for plugging planner pipelines into DecisionOps guardrails."""

from __future__ import annotations

from dataclasses import asdict
import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Literal
import uuid

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .agents import BaselineAgent, GuardedDecisionAgent
from .domain_adapters.bike_share import BikeShareArtifactAdapter
from .domain_adapters.seoul_impact import SeoulImpactAdapter
from .domain_adapters.traffic_incident import TrafficIncidentAdapter
from .mcp_contract import contract
from .pipeline import (
    DEFAULT_BIKE_SHARE_ROOT,
    DEFAULT_CONTROL_TOWER_ROOT,
    DEFAULT_OUTPUT_ROOT,
    run_all,
)
from .tools import DecisionTools
from .tracing import TraceRecorder


LOGGER = logging.getLogger("agentic_decisionops_workbench")
AgentName = Literal["guarded_decision_agent", "baseline_single_agent"]


class DecisionRequest(BaseModel):
    """Request from an external planner or direct operator prompt."""

    prompt: str = Field(..., min_length=1, max_length=4000)
    task_id: str = Field(default="api_request", min_length=1, max_length=120)
    category: str = Field(default="api_request", min_length=1, max_length=120)
    requires_review: bool = False
    agent: AgentName = "guarded_decision_agent"
    planner_action: str | None = Field(default=None, max_length=1000)
    planner_response: str | None = Field(default=None, max_length=4000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolCallRequest(BaseModel):
    """Read-only tool call request for planner evidence gathering."""

    arguments: dict[str, Any] = Field(default_factory=dict)


def _configure_logging() -> None:
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")
    LOGGER.setLevel(level)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def _env_path(name: str, default: Path) -> Path:
    return Path(os.environ.get(name, str(default))).expanduser()


def _artifact_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False, "size_bytes": 0, "mtime_utc": None}
    return {
        "path": str(path),
        "exists": True,
        "size_bytes": path.stat().st_size,
        "mtime_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(path.stat().st_mtime)),
    }


def _load_tools(
    bike_share_root: Path,
    control_tower_root: Path,
) -> tuple[DecisionTools, dict[str, Any]]:
    bike = BikeShareArtifactAdapter(bike_share_root).load()
    incidents = TrafficIncidentAdapter().load()
    impact = SeoulImpactAdapter(control_tower_root).load()
    tools = DecisionTools(bike, incidents, impact)
    source_summary = {
        "bike_share": {
            "source_status": bike.source_status,
            "station_count": len(bike.stations),
            "deployment_decision": bike.deployment.get("decision", "UNKNOWN"),
            "snapshot_count": bike.readiness.get("snapshot_count"),
            "target_snapshots": bike.readiness.get("target_snapshots"),
        },
        "traffic_incident": {
            "source_status": incidents.source_status,
            "incident_count": len(incidents.incidents),
            "source_count": incidents.source_count,
            "deployment_decision": incidents.deployment.get("decision", "UNKNOWN"),
        },
        "seoul_ddareungi_impact": {
            "source_status": impact.source_status,
            "impact_card_count": len(impact.cards),
            "source_count": impact.source_count,
            "validation_status": impact.summary.get("seoul_validation_status", "UNKNOWN"),
            "public_claim_state": impact.summary.get("public_claim_state", "UNKNOWN"),
        },
    }
    return tools, source_summary


def _request_task(payload: DecisionRequest) -> dict[str, Any]:
    prompt_parts = [payload.prompt]
    if payload.planner_action:
        prompt_parts.append(f"planner_action: {payload.planner_action}")
    if payload.planner_response:
        prompt_parts.append(f"planner_response: {payload.planner_response}")
    return {
        "id": payload.task_id,
        "category": payload.category,
        "prompt": "\n".join(prompt_parts),
        "requires_review": payload.requires_review,
        "metadata": payload.metadata,
    }


def _agent_for(
    name: AgentName,
    tools: DecisionTools,
    trace_path: Path,
) -> GuardedDecisionAgent | BaselineAgent:
    trace = TraceRecorder(trace_path)
    if name == "baseline_single_agent":
        return BaselineAgent(tools, trace)
    return GuardedDecisionAgent(tools, trace)


def _safe_tool_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    safe_args = dict(arguments)
    if "limit" in safe_args:
        try:
            safe_args["limit"] = max(1, min(int(safe_args["limit"]), 50))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="limit must be an integer") from exc
    return safe_args


def create_app(
    output_root: Path | str | None = None,
    bike_share_root: Path | str | None = None,
    control_tower_root: Path | str | None = None,
) -> FastAPI:
    _configure_logging()
    root = Path(output_root) if output_root is not None else _env_path("OUTPUT_ROOT", DEFAULT_OUTPUT_ROOT)
    bike_root = (
        Path(bike_share_root)
        if bike_share_root is not None
        else _env_path("BIKE_SHARE_OUTPUT_ROOT", DEFAULT_BIKE_SHARE_ROOT)
    )
    tower_root = (
        Path(control_tower_root)
        if control_tower_root is not None
        else _env_path("CONTROL_TOWER_OUTPUT_ROOT", DEFAULT_CONTROL_TOWER_ROOT)
    )

    app = FastAPI(
        title="Agentic DecisionOps Workbench API",
        version="0.3.0",
        description=(
            "Read-only tool and guarded decision API for plugging planner or LLM "
            "pipelines into DecisionOps evaluation boundaries."
        ),
    )
    app.state.output_root = root
    app.state.bike_share_root = bike_root
    app.state.control_tower_root = tower_root
    app.state.started_at = time.time()

    @app.middleware("http")
    async def structured_request_log(request: Request, call_next):
        request_id = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            LOGGER.exception(
                json.dumps(
                    {
                        "event": "request_error",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": duration_ms,
                    },
                    ensure_ascii=False,
                )
            )
            raise
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        LOGGER.info(
            json.dumps(
                {
                    "event": "request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
                ensure_ascii=False,
            )
        )
        return response

    def surface_summary() -> dict[str, Any]:
        _, sources = _load_tools(app.state.bike_share_root, app.state.control_tower_root)
        return sources

    @app.get("/")
    def read_root() -> dict[str, str]:
        return {
            "service": "agentic-decisionops-workbench",
            "health": "/health",
            "contract": "/v1/contract",
            "decision": "/v1/decisions",
            "tool_call": "/v1/tools/{tool_name}",
            "evaluation": "/v1/evaluations/run",
            "openapi": "/docs",
        }

    @app.get("/health")
    def health() -> dict[str, Any]:
        reports = app.state.output_root / "reports"
        return {
            "status": "ok",
            "project": "agentic-decisionops-workbench",
            "mode": "deterministic_guarded_api",
            "llm_attached": False,
            "planner_pipeline_ready": True,
            "read_only_tools": True,
            "uptime_seconds": round(time.time() - app.state.started_at, 3),
            "output_root": str(app.state.output_root),
            "bike_share_root": str(app.state.bike_share_root),
            "control_tower_root": str(app.state.control_tower_root),
            "sources": surface_summary(),
            "artifacts": {
                "run_summary": _artifact_status(reports / "run_summary.json"),
                "mcp_contract": _artifact_status(reports / "mcp_contract.json"),
                "decisions": _artifact_status(reports / "decisions.json"),
                "human_review_queue": _artifact_status(reports / "human_review_queue.csv"),
            },
        }

    @app.get("/v1/contract")
    def api_contract() -> dict[str, Any]:
        payload = contract()
        payload["runtime"] = {
            "llm_attached": False,
            "default_agent": "guarded_decision_agent",
            "read_only_tools": True,
            "review_gate": "human_review_required_before_execution_or_public_claim",
        }
        return payload

    @app.post("/v1/tools/{tool_name}")
    def call_tool(tool_name: str, payload: ToolCallRequest | None = None) -> dict[str, Any]:
        tools, sources = _load_tools(app.state.bike_share_root, app.state.control_tower_root)
        arguments = _safe_tool_arguments((payload.arguments if payload else {}) or {})
        try:
            result = tools.call(tool_name, **arguments)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "status": "ok",
            "safety": "read_only",
            "tool": result.name,
            "evidence_id": result.evidence_id,
            "payload": result.payload,
            "sources": sources,
        }

    @app.post("/v1/decisions")
    def decide(payload: DecisionRequest) -> dict[str, Any]:
        tools, sources = _load_tools(app.state.bike_share_root, app.state.control_tower_root)
        task = _request_task(payload)
        trace_path = app.state.output_root / "traces" / "api_trace.jsonl"
        agent = _agent_for(payload.agent, tools, trace_path)
        decision = agent.decide(task)
        return {
            "status": "ok",
            "mode": "deterministic_guarded_api",
            "llm_attached": False,
            "planner_output_observed": bool(payload.planner_action or payload.planner_response),
            "task": {
                "id": task["id"],
                "category": task["category"],
                "requires_review": task["requires_review"],
            },
            "decision": asdict(decision),
            "sources": sources,
            "trace_path": str(trace_path),
        }

    @app.post("/v1/evaluations/run")
    def run_evaluation() -> dict[str, Any]:
        summary = run_all(
            output_root=app.state.output_root,
            bike_share_root=app.state.bike_share_root,
            control_tower_root=app.state.control_tower_root,
        )
        return {"status": "ok", "summary": summary}

    return app


app = create_app()
