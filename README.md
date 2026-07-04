# Agentic DecisionOps Workbench

[![agentic-decisionops-workbench-ci](https://github.com/zodia8393/data-scientist-career/actions/workflows/agentic-decisionops-workbench-ci.yml/badge.svg)](https://github.com/zodia8393/data-scientist-career/actions/workflows/agentic-decisionops-workbench-ci.yml)

Operations ML 산출물을 agent가 바로 실행하는 추천으로 만들지 않고, **evidence citation, guardrail, refusal, human review queue**를 통과한 의사결정 workflow로 바꾸는 Stage 2 프로젝트입니다.

이 프로젝트는 단독 chatbot demo가 아닙니다. Stage 1의 bike-share 운영 산출물과 공개 incident sample을 읽어, agentic workflow가 언제 답하고, 언제 거부하고, 언제 사람 검토로 넘겨야 하는지 평가 가능한 형태로 만듭니다.

| Stage | 역할 | 연결 프로젝트 |
|---|---|---|
| Stage 1 | 수요 예측, 서울 따릉이 adapter, 재배치 priority, validation gate | [Bike-Share Demand Resilience](https://github.com/zodia8393/bike-share-demand-resilience) |
| Stage 2 | read-only tool contract, guarded agent, eval harness, review queue | 이 프로젝트 |
| Stage 3 | reviewer dashboard, approval API, SQLite audit trail, Docker demo | [DecisionOps Control Tower](https://github.com/zodia8393/decisionops-control-tower) |

## What This Shows

| 평가자가 봐야 할 것 | 구현 증거 |
|---|---|
| Applied AI product judgment | "추천 생성"보다 invalid action 차단, 근거 인용, reviewer handoff를 우선 설계 |
| Agent evaluation discipline | baseline agent와 guarded agent를 동일 task set과 holdout set으로 비교 |
| Tool and resource design | 4개 resource, 8개 read-only tool, 3개 prompt contract를 JSON artifact로 생성 |
| Cross-domain generalization | bike-share operations와 traffic incident decision surface를 같은 guardrail 체계로 처리 |
| Human-in-the-loop workflow | 자동 실행이 위험한 42건을 priority, SLA, review question이 있는 queue로 변환 |
| Downstream delivery | Stage 3 Control Tower가 review queue, eval metric, contract를 dashboard/API로 투영 |

## Current Evidence

최신 로컬 산출물 기준: 2026-07-03 KST.

| 항목 | 값 | 의미 |
|---|---:|---|
| Main task set | 60 tasks | station, deploy, incident, review queue, cross-domain 요청 포함 |
| Holdout task set | 12 tasks | main task와 분리한 adversarial prompt 검증 |
| Domains | 2 | bike-share operations, traffic incident |
| Incident source | NY 511 open data 120 rows | raw CCTV나 private dispatch log가 아닌 공개 event sample |
| MCP-style contract | 4 resources / 8 tools / 3 prompts | downstream agent/product가 읽는 read-only interface |
| Guarded success | 1.000 | tool, action, evidence, guardrail, review decision 일치 |
| Holdout guarded success | 1.000 | 분리 prompt에서도 guardrail behavior 유지 |
| Invalid action rate | 0.000 | 실행하면 안 되는 요청을 자동 권고하지 않음 |
| Review queue | 42 items | P0 24건, P1 18건을 사람 검토로 전환 |
| Prepublish audit | `public_ready` | unique prompts, holdout success, public incident source gate 통과 |

핵심 비교점은 baseline agent입니다. 같은 task set에서 baseline은 success 0.000, invalid action rate 0.400으로 실패했고, guarded agent는 success 1.000, invalid action rate 0.000으로 통과했습니다.

## Product Surfaces

| Surface | 설명 | 주요 산출물 |
|---|---|---|
| Domain adapters | Stage 1 bike-share 산출물과 NY 511 incident sample을 decision surface로 정규화 | `data/processed/*_decision_surface.json` |
| MCP-style contract | resource/tool/prompt schema를 read-only decision support interface로 생성 | `reports/mcp_contract.json` |
| Guarded agent | `NO_GO`, stale evidence, high uncertainty, source conflict, unsafe write action을 차단 | `reports/decisions.json` |
| Eval harness | baseline과 guarded behavior를 metric, trace, taxonomy로 비교 | `reports/eval_metrics.csv`, `reports/failure_taxonomy.csv` |
| Holdout check | adversarial prompt에서 guardrail regression 확인 | `reports/holdout_eval_metrics.csv` |
| Trace report | task, tool call, guardrail hit, final decision을 reviewer가 훑는 HTML report | `reports/trace_report.html` |
| Human review queue | 승인, 반려, 추가 근거 요청이 필요한 decision을 queue로 변환 | `reports/human_review_queue.csv` |
| Prepublish audit | 공개 포트폴리오 등록 가능 여부를 gate로 판단 | `reports/prepublish_audit.json` |

## Demo Evidence

<img src="docs/assets/demo/trace_report_preview.png" alt="Agentic DecisionOps trace report with guarded agent metrics" width="760">

## Architecture

```text
Bike-share decision artifacts
  - station risk
  - readiness and deploy decision
  - rebalancing priority

NY 511 public incident sample
  - severity
  - evidence age
  - source ambiguity
  - publication restriction
        |
        v
Domain adapters
        |
        v
MCP-style read-only resources/tools/prompts
        |
        v
baseline_single_agent vs guarded_decision_agent
        |
        v
eval metrics, trace log, failure taxonomy
        |
        v
human_review_queue
        |
        v
DecisionOps Control Tower dashboard/API
```

자세한 설계는 [docs/system_design.md](docs/system_design.md), 한국어 DFD는 [docs/data_flow_diagram.md](docs/data_flow_diagram.md)를 봅니다.

## Quick Start

이 프로젝트는 `data-scientist-career` monorepo의 하위 프로젝트입니다.

```bash
git clone https://github.com/zodia8393/data-scientist-career.git
cd data-scientist-career/agentic-decisionops-workbench
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

export OUTPUT_ROOT=/tmp/agentic-decisionops-workbench
export BIKE_SHARE_OUTPUT_ROOT=/tmp/bike-share-demand-resilience
scripts/run_all.sh
```

이미 Stage 1 산출물이 있는 로컬 환경에서는 `BIKE_SHARE_OUTPUT_ROOT`를 해당 산출물 root로 지정합니다. 산출물이 없으면 CI/smoke가 사용할 수 있는 deterministic demo fixture 경로로 동작하도록 설계되어 있습니다.

CLI:

```bash
PYTHONPATH=src scripts/decisionops eval
```

테스트:

```bash
python3 -m py_compile src/agentic_decisionops_workbench/*.py src/agentic_decisionops_workbench/domain_adapters/*.py tests/*.py
PYTHONPATH=src python3 -m pytest tests -q
```

## Repository Guide

| 경로 | 내용 |
|---|---|
| [src/agentic_decisionops_workbench](src/agentic_decisionops_workbench) | pipeline, contract, agents, evaluator, review queue builder |
| [src/agentic_decisionops_workbench/domain_adapters](src/agentic_decisionops_workbench/domain_adapters) | bike-share와 incident decision surface adapter |
| [scripts](scripts) | full run, CLI wrapper, NY 511 sample fetcher |
| [tests](tests) | pipeline/evaluator regression tests |
| [docs/modeling_protocol.md](docs/modeling_protocol.md) | agent/eval protocol |
| [docs/privacy_publication_gate.md](docs/privacy_publication_gate.md) | 공개 가능성과 privacy gate |
| [docs/hiring_market_alignment.md](docs/hiring_market_alignment.md) | 포트폴리오 포지셔닝 |

## Boundaries

- Stage 2 도구는 read-only입니다. upstream data, dispatch system, public channel에 write하지 않습니다.
- 현재 구현은 deterministic/evaluable guarded workflow입니다. LLM API 연결은 regression gate가 안정된 뒤 붙이는 확장입니다.
- NY 511 sample은 공개 historical event data이며, live dispatch authority가 아닙니다.
- Review queue는 CSV/JSONL artifact입니다. 승인 persistence와 reviewer UI는 Stage 3 Control Tower가 담당합니다.
- `NO_GO`, publication restriction, evidence conflict는 자동화 실패가 아니라 의도한 safety behavior입니다.
