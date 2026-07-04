# 연구 설계

## 연구 질문

1. Guarded agent는 unguarded baseline보다 invalid action rate를 낮추는가?
2. Agent가 station, incident, readiness, review queue tool을 올바르게 선택하는가?
3. 불확실하거나 deploy `NO_GO`인 상황에서 refusal 또는 human review로 넘기는가?
4. 한 도메인 전용 규칙이 아니라 cross-domain DecisionOps 패턴으로 동작하는가?

## Evidence Plan

- 복합 결합: bike-share risk, inventory, readiness, deploy decision과 NY 511 traffic incident severity, evidence lag, source ambiguity를 공통 decision surface로 연결한다.
- Baseline: priority만 사용하는 single-agent.
- Main system: guardrail과 evidence citation을 갖춘 decision agent.
- Ablation: unguarded vs guarded, category metric, guardrail coverage, failure taxonomy.
- 불확실성: station risk, inventory pressure, stale/long-running incident evidence, source ambiguity를 review trigger로 사용한다.
- Decision impact: 자동 권고가 아니라 refusal, escalation, human review queue로 운영 workflow를 분리한다.

## 한계

현재 hardening pass는 deterministic evaluator다. LLM-backed planner는 Stage 3에서 붙이되, deterministic regression suite는 계속 유지한다.
