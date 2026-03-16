# STATUS: SUCCESS

## 요약
로컬 sentence-transformers(all-MiniLM-L6-v2) 기반 RSS 피드 관심도 스코어링 엔진. OPML 업로드 → 임베딩 → 코사인 유사도 스코어링 → 읽기/스킵 피드백으로 관심 벡터 EMA 업데이트. 930개 기사에서 피드백 14회 후 관심 기사 점수 74→83으로 개선 확인.

## 완료 기준 결과
- [x] OPML 파일 업로드 → RSS 피드 파싱 → SQLite에 기사 저장 (930개)
- [x] 관심 키워드 입력 → 초기 관심 벡터 생성 → 기사별 관심도 점수 계산 (범위 42.8~83.0)
- [x] 웹 UI에서 관심도 점수순 정렬된 기사 목록 확인 가능
- [x] 읽기/스킵 버튼 클릭 → 관심 벡터 업데이트 → 점수 재계산 반영 확인
- [x] 피드백 10회 이상 후 스코어링 정확도가 체감적으로 개선됨을 데모로 보여줄 수 있음

## 실행 방법
```bash
uv sync
uv run python server.py
# http://127.0.0.1:8000 에서 접속
```

## 소요 정보
- 생성일: 2026-03-17
- 원본 spec: local-feed-relevance-engine.md
- 자동 생성: prototype-pipeline spawn
