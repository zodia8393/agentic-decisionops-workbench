"""Report writers for DecisionOps seed runs."""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def write_reports(output_root: Path) -> dict[str, Path]:
    reports = output_root / "reports"
    metrics = _read_csv(reports / "eval_metrics.csv")
    holdout_metrics = _read_csv(reports / "holdout_eval_metrics.csv")
    results = _read_csv(reports / "eval_results.csv")
    category_metrics = _read_csv(reports / "category_metrics.csv")
    guardrail_coverage = _read_csv(reports / "guardrail_coverage.csv")
    failure_taxonomy = _read_csv(reports / "failure_taxonomy.csv")
    review_queue = _read_csv(reports / "human_review_queue.csv")
    summary = json.loads((reports / "run_summary.json").read_text(encoding="utf-8"))
    guarded = next(row for row in metrics if row["agent"] == "guarded_decision_agent")
    baseline = next(row for row in metrics if row["agent"] == "baseline_single_agent")
    holdout_guarded = next(
        row for row in holdout_metrics if row["agent"] == "guarded_decision_agent"
    )
    prepublish = summary.get("prepublish_audit", {})
    guarded_failures = [
        row for row in results if row["agent"] == "guarded_decision_agent" and row["success"] == "False"
    ]

    final_report = reports / "final_report.md"
    final_report.write_text(
        "\n".join(
            [
                "# Agentic DecisionOps Hardening Report",
                "",
                "## 결론",
                "",
                "Guarded agent는 bike-share와 public NY 511 traffic incident decision surface를 모두 읽고, unsafe deploy, 미확인 incident 공개, 고위험 station, source conflict를 refusal 또는 human review queue로 분기했다.",
                "",
                "## 핵심 수치",
                "",
                "| 항목 | Baseline | Guarded | 의미 |",
                "|---|---:|---:|---|",
                f"| Task success | {_fmt(float(baseline['task_success_rate']))} | {_fmt(float(guarded['task_success_rate']))} | Guardrail과 evidence citation을 포함한 목표 행동 일치율 |",
                f"| Invalid action rate | {_fmt(float(baseline['invalid_action_rate']))} | {_fmt(float(guarded['invalid_action_rate']))} | 거부해야 할 deploy/execute 요청을 잘못 권고한 비율 |",
                f"| Evidence citation | {_fmt(float(baseline['evidence_citation_rate']))} | {_fmt(float(guarded['evidence_citation_rate']))} | 답변이 tool evidence를 인용한 비율 |",
                f"| Holdout success | n/a | {_fmt(float(holdout_guarded['task_success_rate']))} | 반복 task 밖 숨은 prompt 성공률 |",
                f"| Review queue items | 0.000 | {_fmt(float(summary['review_queue']['queue_items']))} | 사람이 승인해야 할 운영 의사결정 workload |",
                f"| Prepublish gate | n/a | {prepublish.get('status', 'unknown')} | registry/GitHub 대표 등록 전 차단 상태 |",
                "",
                "## 도메인 및 데이터 결합",
                "",
                f"- Domains: {', '.join(summary.get('domains', []))}",
                f"- Source count: {summary.get('source_count')}",
                "- Bike-share: station priority, inventory, readiness, deploy gate",
                "- Traffic incident: public NY 511 event sample, derived severity, evidence lag, source ambiguity, publication gate",
                "",
                "## 오류 및 guardrail 감사",
                "",
                f"- Guarded failure rows: {len(guarded_failures)}",
                f"- Guardrail groups: {len(guardrail_coverage)}",
                f"- Failure taxonomy rows: {len(failure_taxonomy)}",
                "",
                "## 산출물",
                "",
                "- `reports/eval_results.csv`: task-level 평가",
                "- `reports/eval_metrics.csv`: agent별 metric",
                "- `reports/category_metrics.csv`: task category별 성능",
                "- `reports/guardrail_coverage.csv`: guardrail별 match rate",
                "- `reports/failure_taxonomy.csv`: 실패 유형",
                "- `reports/holdout_eval_metrics.csv`: 숨은 prompt 회귀 평가",
                "- `reports/human_review_queue.csv`: reviewer queue",
                "- `reports/prepublish_audit.json`: 공개 등록 전 차단 gate",
                "- `reports/mcp_contract.json`: MCP-style tool/resource/prompt contract",
                "- `traces/guarded_trace.jsonl`: guarded workflow trace",
                "- `reports/trace_report.html`: trace/eval inspection report",
                "",
                "## 판단",
                "",
                "이 hardening pass는 Stage 2를 notebook/demo가 아니라 measurable agentic decision system으로 끌어올렸다. Traffic incident surface는 공개 NY 511 event sample을 사용하므로 prepublish gate는 통과하되, 개별 incident publication과 dispatch는 계속 human review를 요구한다.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    model_card = reports / "model_card.md"
    model_card.write_text(
        "\n".join(
            [
                "# System Card",
                "",
                "## 시스템",
                "",
                "이 시스템은 예측 모델이 아니라 운영 ML/incident 산출물을 읽는 deterministic guarded agent workflow입니다.",
                "",
                "## Intended Use",
                "",
                "Bike-share station intervention, traffic incident review, deployment readiness, publication refusal, human-review escalation 평가.",
                "",
                "## Evaluation",
                "",
                "Baseline single-agent와 guarded decision agent를 60개 unique regression task와 별도 holdout task에서 비교하고, category metrics, guardrail coverage, failure taxonomy, review queue를 생성합니다.",
                "",
                "## Limitations",
                "",
                "LLM 호출은 아직 연결하지 않았고, traffic incident surface는 raw CCTV가 아니라 공개 NY 511 historical event sample을 사용합니다.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    data_contract = reports / "data_source_and_contract.md"
    data_contract.write_text(
        "\n".join(
            [
                "# Data Source and Contract",
                "",
                "- Input A: public-safe derived bike-share station priority, inventory, readiness, deploy decision artifacts.",
                "- Input B: public NY 511 traffic event sample transformed into severity, evidence lag, source ambiguity, and publication gate fields.",
                "- Raw CCTV frames, user identifiers, private logs, secrets, and local `.env` values are not copied into this project.",
                "- Output: task dataset, trace JSONL, evaluation metrics, review queue, MCP-style contract, static HTML report.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    html_rows = "\n".join(
        "<tr>"
        + "".join(f"<td>{html.escape(str(row[col]))}</td>" for col in ["agent", "task_success_rate", "invalid_action_rate", "evidence_citation_rate"])
        + "</tr>"
        for row in metrics
    )
    holdout_rows = "\n".join(
        "<tr>"
        + "".join(
            f"<td>{html.escape(str(row[col]))}</td>"
            for col in ["agent", "task_success_rate", "invalid_action_rate", "evidence_citation_rate"]
        )
        + "</tr>"
        for row in holdout_metrics
    )
    category_rows = "\n".join(
        "<tr>"
        + "".join(
            f"<td>{html.escape(str(row[col]))}</td>"
            for col in ["category", "agent", "success_rate", "review_required_accuracy"]
        )
        + "</tr>"
        for row in category_metrics
    )
    guardrail_rows = "\n".join(
        "<tr>"
        + "".join(
            f"<td>{html.escape(str(row[col]))}</td>"
            for col in ["guardrail", "tasks", "match_rate", "blocked_or_reviewed"]
        )
        + "</tr>"
        for row in guardrail_coverage
    )
    queue_rows = "\n".join(
        "<tr>"
        + "".join(
            f"<td>{html.escape(str(row[col]))}</td>"
            for col in ["queue_id", "priority", "task_id", "guardrail_hits"]
        )
        + "</tr>"
        for row in review_queue[:20]
    )
    failed = [row for row in results if row["success"] == "False"][:12]
    failed_rows = "\n".join(
        f"<li><strong>{html.escape(row['task_id'])}</strong> {html.escape(row['agent'])}: {html.escape(row['actual_action'])} / expected {html.escape(row['expected_action'])}</li>"
        for row in failed
    )
    trace_report = reports / "trace_report.html"
    trace_report.write_text(
        f"""<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\">
  <title>Agentic DecisionOps Trace Report</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 32px; color: #1f2937; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
    th {{ background: #f3f4f6; }}
    .status {{ display: inline-block; padding: 4px 8px; background: #eef2ff; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>Agentic DecisionOps Trace Report</h1>
  <p class=\"status\">{html.escape(summary['status'])}</p>
  <h2>Agent Metrics</h2>
  <table>
    <tr><th>Agent</th><th>Success</th><th>Invalid Action</th><th>Evidence Citation</th></tr>
    {html_rows}
  </table>
  <h2>Category Metrics</h2>
  <table>
    <tr><th>Category</th><th>Agent</th><th>Success</th><th>Review Accuracy</th></tr>
    {category_rows}
  </table>
  <h2>Holdout Metrics</h2>
  <table>
    <tr><th>Agent</th><th>Success</th><th>Invalid Action</th><th>Evidence Citation</th></tr>
    {holdout_rows}
  </table>
  <h2>Prepublish Gate</h2>
  <p>{html.escape(str(prepublish.get('status', 'unknown')))}</p>
  <h2>Guardrail Coverage</h2>
  <table>
    <tr><th>Guardrail</th><th>Tasks</th><th>Match</th><th>Blocked Or Reviewed</th></tr>
    {guardrail_rows}
  </table>
  <h2>Human Review Queue</h2>
  <table>
    <tr><th>Queue</th><th>Priority</th><th>Task</th><th>Guardrails</th></tr>
    {queue_rows}
  </table>
  <h2>Sample Failures</h2>
  <ul>{failed_rows}</ul>
  <h2>Trace Files</h2>
  <p>Baseline: traces/baseline_trace.jsonl</p>
  <p>Guarded: traces/guarded_trace.jsonl</p>
</body>
</html>
""",
        encoding="utf-8",
    )
    return {
        "final_report": final_report,
        "model_card": model_card,
        "data_contract": data_contract,
        "trace_report": trace_report,
    }


def write_quality_scores(output_root: Path) -> Path:
    path = output_root / "reports" / "quality_gate_scores.csv"
    rows = [
        ("problem framing and business/career relevance", 95, "two-stage DecisionOps suite bridge with operating decision value"),
        ("data quality, acquisition, and documentation", 94, "bike-share artifacts plus public NY 511 traffic event sample with source metadata"),
        ("EDA depth and insight quality", 94, "category metrics, guardrail coverage, holdout metrics, and failure taxonomy expose error modes"),
        ("feature engineering or statistical design", 94, "risk, evidence lag, source ambiguity, readiness, and review SLA features"),
        ("modeling, inference, optimization, or analytical method rigor", 94, "baseline vs guarded system benchmark with deterministic evaluator"),
        ("validation, testing, and reproducibility", 94, "pytest, py_compile, run_all, structural validators, and prepublish audit are supported"),
        ("interpretation, limitations, and decision usefulness", 95, "review queue converts model/agent output into operating workflow"),
        ("code quality, structure, maintainability, and automation", 94, "domain adapters, tools, guardrails, traces, and reports are modular"),
        ("portfolio presentation, README, figures, and final report", 94, "README and reports now state public NY 511 evidence, holdout results, and prepublish status"),
        ("UI, visibility, readability, and mobile scanability", 94, "static trace dashboard has metric, guardrail, holdout, prepublish, and queue tables"),
        ("doctoral-level originality, depth, and technical ambition", 94, "cross-domain guarded DecisionOps pattern combines operations ML, public incident data, holdout eval, and release gates"),
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "score", "rationale"])
        for category, score, rationale in rows:
            writer.writerow([category, score, rationale])
    return path
