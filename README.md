# Agentic DecisionOps Workbench

AI의 운영 제안을 바로 실행하지 않고, 근거·정책·사람 검토를 거쳐 `recommend`, `refuse`, `escalate`, `summarize`로 재판단하는 read-only guardrail 서비스입니다.

[공개 데모](https://zodia8393.github.io/agentic-decisionops-workbench/) · [Control Tower](https://github.com/zodia8393/decisionops-control-tower) · [문서](docs/README.md)

## 확인할 수 있는 것

| 입력 | 판단 | 결과 |
|---|---|---|
| 운영 위험에 즉시 대응하라는 제안 | 권한·근거·공개 readiness 확인 | `REFUSE` 또는 human review |
| 시민 공개·현장 출동 요청 | 실제 실행 권한 없음 | `REFUSE` |
| 현재 상태 요약 요청 | read-only evidence 조회 | `SUMMARIZE` |

## 경계

- 외부 시스템에 dispatch, public posting, 데이터 변경을 수행하지 않습니다.
- 데모는 recorded snapshot이며 실제 API는 로컬에서만 실행합니다.
- deterministic policy gate가 최종 판단 기준이고, agent는 보조 역할입니다.

## 빠른 실행

```bash
git clone https://github.com/zodia8393/agentic-decisionops-workbench.git
cd agentic-decisionops-workbench
python3 -m pip install -r requirements.txt
scripts/run_all.sh
```

API 데모:

```bash
scripts/serve_api.sh
curl http://127.0.0.1:8000/health
```

## 검증 범위

- tool contract, guardrail, human-review queue, evaluation trace의 단위·smoke 테스트
- public demo smoke
- source data와 deployment claim의 freshness·publication gate

세부 data contract, 실행 재현, system design은 [docs](docs/README.md)에 있습니다.
