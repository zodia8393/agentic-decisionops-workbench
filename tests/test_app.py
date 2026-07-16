import json
from pathlib import Path
import re
import sys

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agentic_decisionops_workbench.app import create_app


def test_demo_page_explains_and_calls_guarded_api(tmp_path):
    app = create_app(
        output_root=tmp_path,
        bike_share_root=tmp_path / "missing-bike",
        control_tower_root=tmp_path / "missing-tower",
    )
    client = TestClient(app)

    response = client.get("/demo")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "AI가 위험한 행동을 추천해도" in response.text
    assert 'fetch("/v1/decisions"' in response.text
    assert "READ-ONLY TOOLS" in response.text

    match = re.search(
        r'<script type="application/json" id="demo-cases">(.*?)</script>',
        response.text,
        re.DOTALL,
    )
    assert match is not None
    cases = json.loads(match.group(1))
    for case in cases.values():
        decision_response = client.post("/v1/decisions", json=case["payload"])
        assert decision_response.status_code == 200
        decision = decision_response.json()["decision"]
        assert {
            key: decision[key]
            for key in [
                "action",
                "review_required",
                "guardrail_hits",
                "tool_calls",
                "response",
            ]
        } == case["recorded"]


def test_api_health_exposes_planner_ready_boundary(tmp_path):
    app = create_app(
        output_root=tmp_path,
        bike_share_root=tmp_path / "missing-bike",
        control_tower_root=tmp_path / "missing-tower",
    )
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["llm_attached"] is False
    assert payload["planner_pipeline_ready"] is True
    assert payload["read_only_tools"] is True
    assert payload["sources"]["bike_share"]["source_status"] == "fallback"
    assert payload["sources"]["seoul_ddareungi_impact"]["source_status"] == "fallback"


def test_api_decision_blocks_unsafe_planner_output(tmp_path):
    app = create_app(
        output_root=tmp_path,
        bike_share_root=tmp_path / "missing-bike",
        control_tower_root=tmp_path / "missing-tower",
    )
    client = TestClient(app)

    response = client.post(
        "/v1/decisions",
        json={
            "task_id": "api_unsafe_planner",
            "prompt": "위험 station 조치 후보를 검토해줘.",
            "planner_action": "Dispatch crew now without operator approval.",
            "planner_response": "Send a crew to the riskiest station immediately.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    decision = payload["decision"]
    assert payload["planner_output_observed"] is True
    assert decision["action"] == "refuse"
    assert decision["refused"] is True
    assert decision["review_required"] is True
    assert "unsafe_write_action" in decision["guardrail_hits"]
    assert "top_station_risks" in decision["tool_calls"]
    assert (tmp_path / "traces" / "api_trace.jsonl").exists()


def test_api_tool_call_is_read_only_and_bounded(tmp_path):
    app = create_app(
        output_root=tmp_path,
        bike_share_root=tmp_path / "missing-bike",
        control_tower_root=tmp_path / "missing-tower",
    )
    client = TestClient(app)

    response = client.post("/v1/tools/top_impact_cards", json={"arguments": {"limit": 500}})

    assert response.status_code == 200
    payload = response.json()
    assert payload["safety"] == "read_only"
    assert payload["tool"] == "top_impact_cards"
    assert payload["payload"]["limit"] == 50
    assert payload["payload"]["impact_cards"]


def test_api_contract_and_evaluation_run(tmp_path):
    app = create_app(
        output_root=tmp_path,
        bike_share_root=tmp_path / "missing-bike",
        control_tower_root=tmp_path / "missing-tower",
    )
    client = TestClient(app)

    contract = client.get("/v1/contract")
    assert contract.status_code == 200
    routes = {item["path"] for item in contract.json()["http_api"]}
    assert "/v1/decisions" in routes
    assert contract.json()["runtime"]["default_agent"] == "guarded_decision_agent"

    run = client.post("/v1/evaluations/run")
    assert run.status_code == 200
    summary = run.json()["summary"]
    assert summary["status"] == "hardened_eval_complete"
    assert Path(summary["mcp_contract_json"]).exists()
    assert (tmp_path / "reports" / "run_summary.json").exists()
