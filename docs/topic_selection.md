# 주제 선정 기록

## 선정된 주제

`Agentic DecisionOps Workbench`를 2번째 대표 프로젝트 hardening 대상으로 선정했다. 목표는 운영 ML 산출물과 incident decision surface를 AI agent가 안전하게 해석하고, tool-use evaluation, guardrail, human review queue, trace로 평가하는 것이다.

## 후보 평가

| 후보 | 데이터/도메인 | 운영 가치 | 채용 신호 | 판단 |
|---|---|---|---|---|
| Agentic DecisionOps | bike-share + incident surface | 모델 결과를 agent decision으로 연결 | AI/ML Product DS, Applied AI | 선정 |
| Generic AgentOps dashboard | synthetic trace only | 운영 도메인 약함 | Agent Engineer | 보류 |
| MTA ridership disruption | public transit data | 전통 DS 강함 | DS/Analytics | 최신 AI 신호 약함 |
| RAG evaluation workbench | public docs | LLM eval 강함 | Applied AI | 운영 ML 연결 약함 |
| Control Tower capstone | model+agent+API | 납품 신호 강함 | MLE/Product | Stage 2 이후 착수 |

## 선정 이유

- 1번 프로젝트와 직접 연결되므로 포트폴리오 서사가 끊기지 않는다.
- 단순 챗봇이 아니라 tool-call validity, invalid action, evidence citation으로 평가한다.
- 두 번째 domain adapter로 패턴 일반화 가능성을 보여준다.
- `decisionops-control-tower` capstone으로 자연스럽게 확장된다.
