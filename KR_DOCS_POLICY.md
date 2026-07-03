# 문서 언어 정책

이 프로젝트의 사용자-facing 문서는 한국어를 기본으로 작성합니다. code identifier, command, model name, metric, path는 English를 유지합니다.

- `README.md`, `final_report.md`, `model_card.md`, `data_source_and_contract.md`는 한국어 설명 중심으로 작성합니다.
- 큰 데이터, 모델, 중간 산출물은 Git에 넣지 않고 `/DATA/HJ/prj/data-scientist-career/projects/<slug>`에 둡니다.
- 수치와 판단 근거는 파일 경로, row count, metric 단위와 함께 기록합니다.
- raw 내부 데이터, 개인정보, SNS 원문, 사용자 ID, token, `.env` 값은 공개 repo에 저장하지 않습니다.
