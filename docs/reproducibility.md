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
python3 ../scripts/validate_weekend_project.py --project . --stage sunday --ratchet-mode strict
```

Sunday strict validator는 public promotion gate로 사용한다. 현재 기준은 NY 511 open-data fixture, holdout success, quality score가 모두 통과해야 한다.

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

`run_all`, `pytest`, Saturday validator, Sunday strict validator가 모두 통과하면 public registry packaging 후보로 본다. 단, incident data는 live dispatch authority가 아니고 Seoul impact card는 validation `READY` 전까지 public claim 근거가 아니다.
