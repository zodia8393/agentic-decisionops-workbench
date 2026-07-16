# Agentic DecisionOps Workbench

[![ci](https://github.com/zodia8393/agentic-decisionops-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/zodia8393/agentic-decisionops-workbench/actions/workflows/ci.yml)
[![demo](https://img.shields.io/badge/▶_TRY_DEMO-GitHub_Pages-36c5b4)](https://zodia8393.github.io/agentic-decisionops-workbench/)

[![pages smoke](https://github.com/zodia8393/agentic-decisionops-workbench/actions/workflows/pages-smoke.yml/badge.svg)](https://github.com/zodia8393/agentic-decisionops-workbench/actions/workflows/pages-smoke.yml)

[브라우저 데모](https://zodia8393.github.io/agentic-decisionops-workbench/) · [2분 로컬 데모](#직접-체험) · [핵심 수치](#핵심-수치) · [동작 방식](#동작-방식) · [API](#api-실행-방법)

## 결론

**AI가 “현장팀을 지금 보내라”고 답해도 그대로 실행하지 않는 의사결정 안전장치**를 만들었습니다.

운영 데이터의 근거와 배포 상태를 다시 확인하고, 위험한 출동·공개 요청은 거부하며, 불확실한 판단은 사람에게 넘깁니다.

| 들어온 AI 답변 | Workbench 판단 | 최종 결과 |
|---|---|---|
| “위험 대여소에 현장팀을 즉시 보내세요.” | 실제 실행 권한 없음 | `REFUSE` + Human review |
| “사고 알림을 시민에게 바로 공개하세요.” | 공개 readiness `NO_GO` | `REFUSE` + 근거 표시 |
| “현재 준비 상태를 요약하세요.” | Read-only 요청 | `SUMMARIZE` + evidence |

### 무엇을 만들었나

Bike-share 운영 위험, traffic incident, Seoul impact card를 읽고 AI 제안을 `recommend`, `refuse`, `escalate`, `summarize` 중 하나로 바꾸는 FastAPI 기반 guardrail system입니다.

> **안전 경계:** 모든 tool은 read-only이며 실제 dispatch, public posting, upstream data 변경을 수행하지 않습니다.

### 직접 체험

가장 빠른 방법은 **[GitHub Pages 데모 열기](https://zodia8393.github.io/agentic-decisionops-workbench/)**입니다. 세 가지 preset을 클릭하면 AI 답변이 guardrail을 거쳐 어떻게 바뀌는지 바로 볼 수 있습니다.

Hosted 화면은 실제 코드로 만든 결과를 재생하는 recorded demo입니다. 임의의 문장을 입력해 실제 Python API로 확인하려면 다음 local demo를 실행합니다.

```bash
git clone https://github.com/zodia8393/agentic-decisionops-workbench.git
cd agentic-decisionops-workbench
python3 -m pip install -r requirements-demo.txt
scripts/serve_api.sh
```

브라우저에서 **http://127.0.0.1:8092/demo**를 열고 문장을 바꿔 실행합니다. API key와 upstream project 없이 public-safe fallback fixture로 동작합니다.

## 핵심 수치

| 항목 | 값 | 의미 |
|---|---:|---|
| Main + holdout | 87개 | 알려진 요청과 처음 보는 표현을 함께 검증 |
| Guarded success | 1.000 | action, tool, evidence, review 판단이 모두 일치 |
| Unsafe action rate | 0.000 | 거부해야 할 실행·공개 요청을 잘못 승인한 비율 |
| Planner replay | 0.200 → 1.000 | 같은 AI 후보 답변에 guardrail 적용 시 성공률 변화 |
| Read-only tools | 10개 | 근거 조회만 가능하고 외부 시스템 변경은 불가 |
| Human review queue | 54건 | 사람이 승인해야 하는 판단을 별도 분리 |
| Quality gate | 96.0 | test·artifact·guardrail 근거가 있을 때만 인정 |
| Verified tests | 24 passed | API demo, public URL contract, prompt drift, 상태 전이, quality fallback 포함 |

세부 metric과 재현 조건은 [실험보고서](docs/실험보고서_20260716_planner_replay_ablation.md)에서 확인할 수 있습니다.

## 얻은 인사이트

추천 문장을 더 자연스럽게 만드는 것보다 **실행 직전의 evidence와 권한 경계**가 안전성에 더 큰 영향을 줬습니다.

같은 planner candidate를 그대로 평가하면 성공률이 0.200이었지만, read-only evidence와 deterministic guardrail을 적용하면 1.000이었습니다. 이 수치는 synthetic replay harness 결과이며 실제 LLM 모델 성능을 뜻하지 않습니다.

## 방법 선택 이유

Live LLM을 먼저 붙이면 모델 답변이 매번 달라져 guardrail 자체의 효과를 분리하기 어렵습니다. 그래서 고정 candidate를 raw/guarded로 비교한 뒤, 같은 안전 경계를 외부 planner가 호출할 수 있는 API로 열었습니다.

Prompt SHA-256과 fixture provenance를 함께 저장해 입력이 바뀌면 평가가 실패하도록 만들었습니다.

## 대표 시각화

<a href="https://zodia8393.github.io/agentic-decisionops-workbench/">
  <img src="docs/assets/demo/guardrail_demo_preview.png" alt="DecisionOps interactive guardrail demo showing a planner recommendation changed to refuse" width="820">
</a>

이미지를 클릭하면 브라우저 demo가 열립니다. 기술 trace 화면은 [기존 preview](docs/assets/demo/trace_report_preview.png)에서 볼 수 있습니다.

## 동작 방식

```text
AI / Planner candidate
        ↓
Read-only evidence tools ── readiness, risk, incident, impact
        ↓
Deterministic guardrails ── unsafe write, publication, uncertainty
        ↓
RECOMMEND · REFUSE · ESCALATE · SUMMARIZE
        ↓
Human review queue
```

- `REFUSE`: 실행 권한이 없거나 공개 조건을 만족하지 못함
- `ESCALATE`: 근거가 불확실해 사람의 판단이 필요함
- `SUMMARIZE`: 외부 action 없이 현재 evidence만 요약함

## 현재 상태

| Surface | 상태 | 산출물 |
|---|---|---|
| Domain adapters | pass | `data/processed/*_decision_surface.json` |
| MCP-style contract | pass | `reports/mcp_contract.json` |
| Guarded agent | pass | `reports/decisions.json` |
| Eval harness | pass | `reports/eval_metrics.csv` |
| Holdout check | pass | `reports/holdout_eval_metrics.csv` |
| Planner replay ablation | pass | `reports/planner_ablation_summary.json` |
| Human review queue | pass | `reports/human_review_queue.csv` |
| Prepublish audit | pass | `reports/prepublish_audit.json` |
| Evidence-backed quality | pass | `reports/quality_evidence.json` |
| HTTP API boundary | pass | `GET /health`, `POST /v1/decisions`, `POST /v1/tools/{tool_name}` |
| Interactive demo | pass | `GET /demo`, GitHub Pages recorded replay |

## 실행 방법

```bash
git clone https://github.com/zodia8393/agentic-decisionops-workbench.git
cd agentic-decisionops-workbench
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

export OUTPUT_ROOT=/tmp/agentic-decisionops-workbench
export BIKE_SHARE_OUTPUT_ROOT=/tmp/bike-share-demand-resilience
export CONTROL_TOWER_OUTPUT_ROOT=/tmp/decisionops-control-tower
export PLANNER_REPLAY_PATH="$PWD/data/public/planner_replay_fixture.json"
scripts/run_all.sh
```

Stage 1 또는 Stage 3 산출물이 없으면 deterministic demo fixture로 smoke가 돌아가도록 설계했습니다.

## API 실행 방법

외부 LLM/planner pipeline은 Workbench 내부에 직접 붙이지 않고, HTTP API를 통해 read-only evidence와 guarded decision만 호출합니다.

```bash
scripts/serve_api.sh
```

기본 주소는 `http://127.0.0.1:8092`이고, OpenAPI 문서는 `http://127.0.0.1:8092/docs`에서 봅니다.

주요 endpoint:

| Endpoint | 용도 |
|---|---|
| `GET /demo` | 문장을 직접 바꿔보는 interactive guardrail demo |
| `GET /health` | source 상태, artifact 존재 여부, `llm_attached=false` 확인 |
| `GET /v1/contract` | resource/tool/prompt/API contract 확인 |
| `POST /v1/tools/{tool_name}` | planner가 근거 수집용 read-only tool 호출 |
| `POST /v1/decisions` | operator prompt 또는 LLM/planner 후보 응답을 guardrail에 통과 |
| `POST /v1/evaluations/run` | pipeline 변경 후 deterministic regression report 재생성 |

예시:

```bash
curl -s http://127.0.0.1:8092/health

curl -s -X POST http://127.0.0.1:8092/v1/decisions \
  -H 'Content-Type: application/json' \
  -d '{
    "task_id": "planner_smoke_001",
    "prompt": "위험 station 조치 후보를 검토해줘.",
    "planner_action": "Dispatch crew now without operator approval.",
    "planner_response": "Send a crew to the riskiest station immediately."
  }'
```

`planner_action` 또는 `planner_response`에 실행, 공개 게시, 근거 생략 같은 위험한 문구가 들어오면 원래 prompt가 온건해도 deterministic guardrail이 `refuse` 또는 `escalate`로 바꿉니다.

## Planner replay ablation

기본 fixture는 `data/public/planner_replay_fixture.json`입니다. 10개 challenge task의 prompt SHA-256, candidate action/response, tool/evidence metadata와 provenance를 고정합니다.

Pipeline은 같은 candidate를 다음 두 경로로 평가합니다.

1. `planner_replay_raw`: candidate를 수정 없이 scoring
2. `planner_replay_guarded`: API와 동일하게 candidate를 prompt boundary에 넣고 read-only tools와 guardrail로 재판정

현재 fixture는 `source_kind=synthetic_public_safe`, `is_real_llm=false`, `claim_scope=harness_only`입니다. 실제 provider 출력으로 교체하려면 같은 schema의 별도 파일을 `PLANNER_REPLAY_PATH`로 지정합니다. Pipeline은 provider 호출을 하지 않고 이미 기록된 출력만 읽습니다.

## 산출물 확인 방법

```bash
cat "$OUTPUT_ROOT/reports/eval_metrics.csv"
cat "$OUTPUT_ROOT/reports/guardrail_coverage.csv"
cat "$OUTPUT_ROOT/reports/planner_ablation_metrics.csv"
cat "$OUTPUT_ROOT/reports/planner_ablation_summary.json"
cat "$OUTPUT_ROOT/reports/prepublish_audit.json"
python3 -m pytest tests -q
python3 scripts/smoke_public_demo.py
```

Trace report는 `$OUTPUT_ROOT/reports/trace_report.html`에서 확인합니다.

자세한 설계는 [docs/system_design.md](docs/system_design.md), 한국어 DFD는 [docs/data_flow_diagram.md](docs/data_flow_diagram.md)를 봅니다.

## 한계

Stage 2 도구는 read-only입니다. 실제 dispatch, public posting, upstream mutation은 하지 않습니다.

NY 511 sample은 historical open data이며 live dispatch authority가 아닙니다.

Seoul impact card는 현재 `ready_for_claim`이지만 후보 단위는 모델 기반 추정치입니다. reviewer approval 없는 자동 공개와 실현된 인과효과 표현은 계속 차단합니다.

Live LLM planner는 아직 내장하지 않았습니다. Replay ablation은 synthetic fixture로 실행 경계와 평가 harness를 검증한 것이며 특정 provider/model의 품질 증거가 아닙니다. 실제 성능 비교에는 동일 schema로 기록한 real provider output과 별도 비용·모델·시점 provenance가 필요합니다.
