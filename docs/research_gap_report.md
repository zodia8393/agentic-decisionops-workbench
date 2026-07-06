# Research Gap Report

이 문서는 hardening pass가 portfolio-ready로 과장되지 않도록 남기는 gap 추적표다.

| Gate | 현재 상태 | Gap | 다음 작업 |
|---|---|---|---|
| topic candidates >= 5 | pass | 없음 | 유지 |
| data/tool sources >= 3 | pass | bike-share + NY 511 public traffic events + Seoul impact cards + derived review queue | source refresh script 유지 |
| baseline vs guarded | pass | deterministic workflow + holdout 15/15 | LLM planner ablation 추가 |
| trace/eval report | pass | static report + prepublish audit + impact guardrail; Stage 3 Control Tower가 interactive review UI 제공 | trace-to-dashboard deep link는 후속 |
| uncertainty guardrail | pass | station, incident, impact-card heuristic rule 기반 | calibration-based threshold 추가 |
| privacy gate | pass | source 기준 | release artifact scan 자동화 유지 |
| deployable product | pass | Stage 2 자체는 CLI/report/queue이고 Stage 3 Control Tower가 API/Docker로 연결 | hosted demo hardening |
| prepublish audit | pass | unique prompt, holdout, real/open incident source 통과 | registry packaging 여부 결정 |
| quality floor >= 94.9 | pass | min score 94.9, presentation score 95.0 | active quality floor ratchet을 테스트로 고정 |

## 남은 리스크

- Traffic incident domain은 raw CCTV가 아니라 NY 511 public historical event sample이다.
- LLM-backed planner는 아직 붙이지 않았다.
- Review queue는 Stage 2에서는 CSV/JSONL artifact이고, persistence와 reviewer action은 Stage 3 `decisionops-control-tower`에서 처리한다.
- Incident data는 live dispatch authority가 아니므로 publication/dispatch는 계속 human review 범위다.
- Seoul impact card는 validation `READY`와 public deploy `GO`를 모두 만족하기 전까지 성과 claim이 아니라 reviewer evidence다.
