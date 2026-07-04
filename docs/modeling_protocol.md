# 모델링 및 평가 프로토콜

## 목표

이 프로젝트의 핵심은 새 예측 모델이 아니라 agentic decision system benchmark다. Baseline single-agent와 guarded decision agent를 같은 task set에서 비교한다.

## Split

현재 hardening pass는 deterministic public-safe task set 60개를 고정 regression set으로 사용하고, 별도 holdout 12개를 adversarial prompt 검증에 사용한다. 이후 LLM-backed planner를 붙일 때는 `development`, `holdout`, `regression`을 더 엄격히 분리한다.

## Baseline

Baseline agent는 priority evidence만 읽고 deploy/readiness/uncertainty/publication guardrail을 고려하지 않는다.

## Main Method

Guarded agent는 station risk, incident severity, evidence lag, source ambiguity, readiness, deploy decision을 읽고 `recommend`, `refuse`, `escalate`, `summarize`로 분기한다.

## Metric

| 지표 | 의미 |
|---|---|
| task success | action, tool, review, guardrail, evidence 기준 통합 성공 |
| tool-call validity | expected tool subset을 호출했는지 |
| invalid action rate | 거부해야 할 요청을 잘못 권고한 비율 |
| review-required accuracy | human review 필요 여부 판단 |
| evidence citation rate | 답변이 tool evidence를 인용했는지 |

## Ablation

초기 ablation은 baseline vs guarded다. 추가로 category metric, guardrail coverage, failure taxonomy를 생성해 readiness rule, uncertainty rule, publication rule 제거 실험으로 확장할 수 있게 했다.

## 불확실성 및 오류 감사

Station risk, inventory pressure, deploy readiness `NO_GO`, incident evidence lag, source ambiguity, publication restriction을 high-risk condition으로 다룬다. 실패 task는 `failure_taxonomy.csv`로 분류한다.
