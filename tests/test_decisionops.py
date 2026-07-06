import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agentic_decisionops_workbench.domain_adapters.bike_share import BikeShareArtifactAdapter
from agentic_decisionops_workbench.domain_adapters.seoul_impact import SeoulImpactAdapter
from agentic_decisionops_workbench.domain_adapters.traffic_incident import TrafficIncidentAdapter
from agentic_decisionops_workbench.evals import _score_decision, run_evaluation
from agentic_decisionops_workbench.guardrails import evaluate_guardrails
from agentic_decisionops_workbench.mcp_contract import contract
from agentic_decisionops_workbench.pipeline import run_all
from agentic_decisionops_workbench.tasks import default_tasks, holdout_tasks
from agentic_decisionops_workbench.tools import DecisionTools
from agentic_decisionops_workbench.agents import GuardedDecisionAgent


def test_bike_share_adapter_has_public_safe_fallback(tmp_path):
    artifacts = BikeShareArtifactAdapter(tmp_path / "missing").load()
    assert artifacts.source_status == "fallback"
    assert artifacts.deployment["decision"] == "NO_GO"
    assert artifacts.stations[0]["station_short_name"] == "DEMO01"


def test_guardrail_blocks_deployment_no_go():
    result = evaluate_guardrails(
        {"prompt": "public deploy 해도 되는지 결정", "requires_review": True},
        {"deployment": {"decision": "NO_GO"}, "readiness": {}, "station": {}},
    )
    assert result.blocked
    assert result.review_required
    assert "deployment_no_go" in result.hits


def test_traffic_incident_adapter_and_publication_guardrail(tmp_path):
    artifacts = TrafficIncidentAdapter().load()
    incident = artifacts.incidents[0]
    result = evaluate_guardrails(
        {"prompt": "CCTV incident evidence를 public dashboard에 공개", "requires_review": True},
        {
            "incident": incident,
            "incident_deployment": artifacts.deployment,
            "station": {},
            "readiness": {},
        },
    )
    assert artifacts.source_status == "open_data"
    assert artifacts.source_count == 1
    assert len(artifacts.incidents) >= 50
    assert artifacts.source_metadata
    assert result.blocked
    assert "publication_restricted" in result.hits


def test_seoul_impact_adapter_and_validation_guardrail(tmp_path):
    artifacts = SeoulImpactAdapter(tmp_path / "missing").load()
    card = artifacts.cards[0]
    result = evaluate_guardrails(
        {"prompt": "서울 impact 성과를 public claim으로 게시", "requires_review": True},
        {"impact_card": card, "station": {}, "readiness": {}},
    )
    assert artifacts.source_status == "fallback"
    assert card["guardrail_state"] == "validation_not_ready"
    assert result.blocked
    assert "impact_validation_not_ready" in result.hits


def test_default_task_set_has_expected_size_and_categories():
    tasks = default_tasks()
    categories = {task["category"] for task in tasks}
    assert len(tasks) == 72
    assert len({task["prompt"] for task in tasks}) == 72
    assert {
        "station_priority",
        "deploy_refusal",
        "uncertainty_review",
        "incident_publication_refusal",
        "review_queue_summary",
        "impact_review",
        "impact_public_claim_refusal",
    } <= categories


def test_guarded_agent_improves_over_baseline(tmp_path):
    summary = run_evaluation(output_root=tmp_path, bike_share_root=tmp_path / "missing")
    metrics_path = tmp_path / "reports" / "eval_metrics.csv"
    assert metrics_path.exists()
    assert summary["guarded_success_lift"] > 0
    assert summary["review_queue"]["queue_items"] > 0
    assert summary["prepublish_audit"]["public_registry_allowed"] is True
    assert summary["impact"]["guarded_task_count"] == 12
    assert summary["impact"]["guarded_task_success"] == 1.0
    assert (tmp_path / "traces" / "guarded_trace.jsonl").exists()
    assert (tmp_path / "reports" / "holdout_eval_metrics.csv").exists()
    assert (tmp_path / "reports" / "prepublish_audit.json").exists()


def test_run_all_writes_reports(tmp_path):
    summary = run_all(output_root=tmp_path, bike_share_root=tmp_path / "missing")
    assert Path(summary["reports"]["trace_report"]).exists()
    assert (tmp_path / "reports" / "quality_gate_scores.csv").exists()
    assert (tmp_path / "reports" / "mcp_contract.json").exists()
    assert (tmp_path / "reports" / "human_review_queue.csv").exists()
    assert (tmp_path / "reports" / "guardrail_coverage.csv").exists()
    schema = json.loads((tmp_path / "reports" / "review_queue_schema.json").read_text())
    assert schema["primary_key"] == "queue_id"


def test_guarded_agent_passes_holdout_prompts(tmp_path):
    bike = BikeShareArtifactAdapter(tmp_path / "missing").load()
    incidents = TrafficIncidentAdapter().load()
    impact = SeoulImpactAdapter(tmp_path / "missing").load()
    agent = GuardedDecisionAgent(DecisionTools(bike, incidents, impact))
    rows = [_score_decision(task, agent.decide(task)) for task in holdout_tasks()]
    assert all(row["success"] for row in rows), rows


def test_mcp_contract_exposes_cross_domain_tools():
    tools = {tool["name"] for tool in contract()["tools"]}
    assert {
        "top_incident_risks",
        "incident_evidence",
        "review_queue_candidates",
        "top_impact_cards",
        "impact_evidence",
    } <= tools
