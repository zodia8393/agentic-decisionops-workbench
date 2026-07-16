# 시스템 설계

## Product Surface

현재 product surface는 CLI, FastAPI `/demo` interactive UI, GitHub Pages recorded replay, static trace dashboard, human review queue artifact다.

```bash
scripts/decisionops eval
scripts/run_all.sh
scripts/serve_api.sh
```

이번 weekday pass는 Stage 3 Control Tower의 서울 따릉이 impact card를 read-only tool로 읽어, 단순 추천이 아니라 expected impact, evidence, `NO_GO`, stale data, low-confidence, low-impact 여부를 함께 평가하는 impact-aware guardrail layer로 확장했다.

## Architecture

```text
decision artifacts
  -> domain adapters
  -> MCP-style resources/tools/prompts
  -> baseline and guarded agents
  -> eval metrics, trace JSONL, failure taxonomy
  -> human review queue
  -> static HTML trace report

Control Tower decision impact artifacts
  -> impact-aware guardrail
  -> expected impact evidence check
  -> validation-not-ready, low-impact, stale, weak-evidence refusal/escalation
  -> review queue with action rationale
```

데이터 흐름도(DFD): [data_flow_diagram.md](data_flow_diagram.md)

## API / Dashboard / Batch

Stage 2는 batch CLI, `/v1/decisions` FastAPI endpoint, `/demo` interactive guardrail UI, static trace dashboard를 제공한다. GitHub Pages는 같은 UI의 public-safe recorded result만 재생한다. Stage 3 `decisionops-control-tower`가 reviewer queue UI, SQLite persistence, local deployment surface로 확장한다.

## Deployment Runbook

Stage 2의 live API는 public deploy하지 않는다. GitHub Pages에는 write capability가 없는 recorded demo만 배포한다. Dockerfile과 authenticated reviewer write demo는 Stage 3 Control Tower에서 제공한다.

## Operations

- Healthcheck: `scripts/run_all.sh`
- Interactive demo: `scripts/serve_api.sh` 실행 후 `http://127.0.0.1:8092/demo`
- Regression: `pytest`
- Trace inspection: `reports/trace_report.html`
- Gate: deploy `NO_GO`, high uncertainty, unsafe write action, publication restriction, cross-source conflict, impact validation not ready, low confidence impact
