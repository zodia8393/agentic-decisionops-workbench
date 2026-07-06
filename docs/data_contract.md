# 데이터 및 Tool 계약

## 목적

운영 ML 산출물과 incident decision surface를 agent가 읽을 수 있는 public-safe MCP-style resources/tools/prompts 계약으로 변환한다.

## 원천

| 원천 | 역할 | 라이선스/공개성 |
|---|---|---|
| Station priority | station risk와 intervention 후보 | public-safe derived artifact |
| Inventory snapshot | bike/dock shortage evidence | public GBFS-derived aggregate |
| Snapshot readiness | prospective validation readiness | derived report |
| Deploy readiness | deploy `GO/NO_GO` gate | derived report |
| NY 511 traffic event sample | severity, evidence lag, source ambiguity | public/open data sample |
| Seoul Ddareungi impact cards | expected impact, confidence, validation blocker | Control Tower public-safe derived artifact |
| Synthetic task set | agent evaluation scenario | generated fixture |

## 결합 Join

Bike-share는 `station_short_name` 단위로 forecast, uncertainty, inventory, readiness를 결합한다. Traffic incident는 NY 511 event record를 `incident_id` 단위 decision surface로 변환해 severity, evidence lag, source ambiguity, publication gate를 결합한다. Seoul impact card는 `impact_card_id` 단위로 candidate units, confidence, validation status, public claim state를 결합한다.

세 도메인은 raw record join이 아니라 공통 decision schema로 join된다.

## 누수 및 안전

- Agent는 read-only tool만 호출한다.
- deploy `NO_GO`, high uncertainty, stale evidence, publication restriction은 자동 실행으로 이어지지 않는다.
- Seoul validation이 `READY`가 아니면 impact card는 public 성과 claim이 아니라 reviewer evidence다.
- 내부 데이터, 개인정보, SNS 원문, raw CCTV frame, token, `.env` 값은 source와 public artifact에 포함하지 않는다.
- NY 511 data는 public access source지만, 이 프로젝트의 incident action은 live dispatch authority가 아니므로 publication/dispatch는 human review로 제한한다.
