# 모델링 및 평가 프로토콜

## 목표

이 프로젝트의 핵심은 새 예측 모델이 아니라 agentic decision system benchmark다. Baseline single-agent와 guarded decision agent를 같은 task set에서 비교한다.

## Split

현재 hardening pass는 deterministic public-safe task set 72개를 고정 regression set으로 사용하고, 별도 holdout 15개를 adversarial prompt 검증에 사용한다. Planner replay는 이 두 set과 분리된 10개 challenge set을 사용하며 prompt SHA-256으로 fixture drift를 차단한다.

## Baseline

Baseline agent는 priority evidence만 읽고 deploy/readiness/uncertainty/publication guardrail을 고려하지 않는다.

## Main Method

Guarded agent는 station risk, incident severity, evidence lag, source ambiguity, impact units, confidence, validation status, readiness, deploy decision을 읽고 `recommend`, `refuse`, `escalate`, `summarize`로 분기한다.

## Metric

| 지표 | 의미 |
|---|---|
| task success | action, tool, review, guardrail, evidence 기준 통합 성공 |
| tool-call validity | expected tool subset을 호출했는지 |
| invalid action rate | 거부해야 할 요청을 잘못 권고한 비율 |
| review-required accuracy | human review 필요 여부 판단 |
| evidence citation rate | 답변이 tool evidence를 인용했는지 |

## Ablation

첫 ablation은 baseline vs guarded다. 두 번째 ablation은 동일한 planner candidate output을 `planner_replay_raw`와 `planner_replay_guarded`로 비교한다. 기본 candidate는 synthetic fixture이므로 guardrail harness 검증에만 사용하며 실제 LLM 성능을 주장하지 않는다. 추가로 category metric, guardrail coverage, failure taxonomy를 생성해 readiness rule, uncertainty rule, publication rule, impact validation rule 제거 실험으로 확장할 수 있게 했다.

## Planner replay provenance

- 기본 입력: `data/public/planner_replay_fixture.json`
- 입력 계약: provider/model/source kind, capture time, claim scope, task prompt hash, action/response, tool/evidence metadata
- 기본 claim scope: `harness_only`
- 실제 LLM 비교 조건: provider가 기록한 출력, `is_real_llm=true`, `source_kind=recorded_llm`, 별도 `model_evaluation` claim scope
- 실행 특성: replay-only, network/API 호출 없음, random sampling 없음

## 불확실성 및 오류 감사

Station risk, inventory pressure, deploy readiness `NO_GO`, incident evidence lag, source ambiguity, publication restriction, impact validation `NOT_READY`, low confidence를 high-risk condition으로 다룬다. 실패 task는 `failure_taxonomy.csv`로 분류한다.
