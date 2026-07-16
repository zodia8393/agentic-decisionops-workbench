# Planner Replay Ablation 실험보고서

## 목적

외부 planner가 만든 동일한 candidate output을 그대로 사용할 때와 DecisionOps의 deterministic read-only tool/guardrail boundary에 통과시킬 때의 안전성 차이를 재현 가능하게 측정한다.

이 실험은 live LLM 또는 특정 provider/model의 성능 평가가 아니다. 기본 입력은 의도적으로 위험 응답을 포함한 public-safe synthetic fixture이며 claim scope는 `harness_only`다.

## 방법

- Main regression 72개와 holdout 15개에서 분리한 planner challenge 10개를 사용했다.
- Challenge category는 execution 2개, publication 2개, evidence omission 2개, review 2개, safe summary 2개다.
- `planner_replay_raw`는 fixture action/response/tool/evidence metadata를 수정 없이 평가했다.
- `planner_replay_guarded`는 같은 action/response를 HTTP API와 동일한 prompt boundary에 넣고 `GuardedDecisionAgent`가 evidence를 다시 읽어 action을 재판정했다.
- Task ID와 prompt SHA-256을 fixture에 고정하고 하나라도 달라지면 평가를 중단한다.
- Network/API 호출과 random sampling은 사용하지 않았다.

## 파라미터와 입력

| 항목 | 값 |
|---|---|
| Fixture | `data/public/planner_replay_fixture.json` |
| Schema | `1.0` |
| Fixture ID | `public_safe_scripted_planner_v1` |
| Source kind | `synthetic_public_safe` |
| Provider / model | `fixture` / `scripted_candidate_v1` |
| Real LLM | `false` |
| Claim scope | `harness_only` |
| Tasks | 10 |
| Random seed | 해당 없음; deterministic replay |

## 결과

| Metric | Raw planner | Guarded replay | 변화 |
|---|---:|---:|---:|
| Task success | 0.200 | 1.000 | +0.800 |
| Tool-call validity | 1.000 | 1.000 | 0.000 |
| Invalid action rate | 0.600 | 0.000 | -0.600 |
| Guardrail match | 0.200 | 1.000 | +0.800 |
| Review-required accuracy | 0.200 | 1.000 | +0.800 |
| Evidence citation | 0.800 | 1.000 | +0.200 |

Main 72개와 holdout 15개의 guarded success는 모두 1.000을 유지했다. Replay prompt drift 회귀 테스트를 포함한 test suite는 20개가 통과했다.

## 판단

동일한 candidate를 고정했을 때 deterministic boundary가 unsafe execution/publication, evidence omission, missed review를 교정하는 평가 경로는 동작한다. 이 결과는 guardrail integration harness의 회귀 근거이며, synthetic candidate가 실제 모델 분포를 대표한다는 뜻은 아니다.

실제 provider/model 비교로 승격하려면 같은 schema에 `source_kind=recorded_llm`, `is_real_llm=true`, `claim_scope=model_evaluation`을 명시하고 모델명, capture 시점, 비용, sampling parameter를 별도로 보존해야 한다.

## 재현

```bash
PLANNER_REPLAY_PATH="$PWD/data/public/planner_replay_fixture.json" \
scripts/run_all.sh

cat "$OUTPUT_ROOT/reports/planner_ablation_metrics.csv"
cat "$OUTPUT_ROOT/reports/planner_ablation_summary.json"
```

핵심 산출물은 `planner_ablation_results.csv`, `planner_ablation_metrics.csv`, `planner_ablation_category_metrics.csv`, `planner_ablation_decisions.json`, `planner_ablation_summary.json`, `planner_replay_guarded_trace.jsonl`이다.
