# Privacy / Publication Gate

## 공개 금지

- 내부 raw data
- 개인정보와 재식별 가능한 user identifier
- SNS 원문, profile, 댓글 원문
- raw CCTV frame 또는 영상 클립
- 민감 좌표 원본
- token, API key, cookie, `.env` 값
- destructive write tool
- credential, 개인 prompt, 내부 문서가 남은 raw planner/LLM response

## 공개 허용

- synthetic task fixture
- public-safe synthetic planner replay fixture와 aggregate ablation metric
- public-safe derived bike-share metrics
- NY 511 public traffic event sample and derived incident decision surface
- Control Tower derived Seoul Ddareungi impact cards with validation blockers
- tool schema and MCP-style contract
- anonymized trace examples
- aggregate eval metrics and review queue schema

## Gate Result

| 항목 | 상태 | 근거 |
|---|---|---|
| 내부 원문 제외 | pass | source에는 derived schema와 fixture만 포함 |
| 개인정보 제외 | pass | ride_id/user identifier 미사용 |
| SNS 원문 제외 | pass | social source 없음 |
| CCTV 원본 제외 | pass | incident surface는 NY 511 open data sample, raw CCTV 미사용 |
| secret scan | pass | token assignment 없음 |
| unsafe write action | blocked | guardrail `unsafe_write_action` |
| publication restriction | blocked | guardrail `publication_restricted` |
| validation 전 impact claim | blocked | guardrail `impact_validation_not_ready` |
| planner replay provenance | pass | `harness_only`, `is_real_llm=false`, prompt SHA-256 고정 |
| prepublish audit | pass | real/open second-domain source와 holdout gate 통과 |
