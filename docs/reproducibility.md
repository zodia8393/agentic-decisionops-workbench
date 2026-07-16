# 재현 가이드

## 환경

- Python 3.10+
- `pytest`
- 산출물 root는 `OUTPUT_ROOT`로 지정
- Stage 3 impact card root는 `CONTROL_TOWER_OUTPUT_ROOT`로 지정

## 실행

```bash
pip install -r requirements.txt
OUTPUT_ROOT=/tmp/agentic-decisionops-workbench \
CONTROL_TOWER_OUTPUT_ROOT=/tmp/decisionops-control-tower \
scripts/run_all.sh
```

NY 511 public event sample을 갱신할 때만 다음을 실행한다.

```bash
scripts/fetch_ny511_sample.py
```

## 검증

```bash
PYTHONPATH=src python3 -m pytest tests -q
python3 ../scripts/validate_weekend_project.py --project . --stage saturday
python3 ../scripts/validate_weekend_project.py --project . --stage sunday --ratchet-mode floor
```

Sunday floor validator는 현재 active floor 보존 gate입니다. `strict` mode는 기존 floor를 초과해 portfolio 전체 ratchet을 올릴 때만 사용합니다. `reports/quality_evidence.json`의 JUnit·main/holdout·impact guardrail·prepublish·artifact checks가 모두 참이 아니면 score는 기존 94.9~95.4 범위로 복귀합니다.

## 산출물

- `reports/run_summary.json`
- `reports/eval_metrics.csv`
- `reports/category_metrics.csv`
- `reports/guardrail_coverage.csv`
- `reports/failure_taxonomy.csv`
- `reports/holdout_eval_metrics.csv`
- `reports/prepublish_audit.json`
- `reports/human_review_queue.csv`
- `reports/trace_report.html`
- `reports/mcp_contract.json`
- `data/processed/seoul_impact_decision_surface.json`

## 성공 기준

`run_all`, `pytest`, Saturday validator, Sunday floor validator가 모두 통과하면 기존 public registry packaging 상태를 유지한다. 단, incident data는 live dispatch authority가 아니고 Seoul impact card는 validation `READY` 전까지 public claim 근거가 아니다.
