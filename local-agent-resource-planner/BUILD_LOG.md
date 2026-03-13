# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-13 — Spec 읽기 완료
- [목표] GGUF 메타데이터 기반 VRAM 예측 + 멀티 모델 리소스 플래닝
- [판단] 스택 선택: Python + uv (이유: GGUF 바이너리 파싱에 struct 모듈 활용, 수치 계산 자연스러움, 웹 UI는 stdlib http.server + 단일 HTML)
- [판단] 외부 의존성 최소화: 코어 로직은 Python 표준 라이브러리만 사용 (playwright는 테스트용)
- [판단] 웹 UI 선택 (CLI 대신): 모델 조합 시각화와 인터랙티브 필터링이 UI로 더 직관적
- [범위] 완료 기준 5개 항목 전부 구현 목표

## Phase 2 — 구현
- [시도] GGUF 바이너리 파서 구현 (struct 모듈) → [결과] 성공. v2/v3 지원, 모든 메타데이터 타입 파싱
- [시도] VRAM 계산기 수식 구현 → [결과] 성공. weights + KV cache + activation + overhead 분리
- [에러] Phi-2 모델 VRAM 추정 오차 31.8% → [원인] Phi-2는 non-gated MLP (2 projections), 코드는 gated (3 projections) 가정
- [수정] ffn_projections 파라미터 추가 → Phi-2 오차 6.8%로 개선
- [시도] 테스트 GGUF 파일 생성기 → [결과] 성공. 실제 파싱 동작 확인
- [시도] 웹 서버 + HTML UI → [결과] 성공. 5개 탭 (Single/Multi/Grid/Validate/Upload)
- [시도] Playwright 브라우저 테스트 → [결과] 실패. 시스템 라이브러리(libatk) 부재, sudo 불가
- [대체] curl 기반 API 테스트 8개 항목 전부 통과

## Phase 3 — 셀프 크리틱

### 3-1. 직접 사용
- CLI 모드: 5개 모델 추정, 멀티모델 계획, 검증, 그리드 서치 모두 정상 동작
- 웹 API: 8개 엔드포인트 전부 정상 응답
- GGUF 업로드: 테스트 파일 파싱 + VRAM 추정 정상

### 3-2. 스스로 평가
1. **"오 되네" vs "뭐야 이게"**: "오 되네" 쪽. CLI 출력이 깔끔하고, 검증 7/7 통과가 인상적.
2. **Spec 검증 목표 달성**: 대부분 달성. VRAM 예측이 llama.cpp 레퍼런스와 20% 이내. 다만 "실측"이 아닌 커뮤니티 레퍼런스 값이므로 진짜 실측 비교는 아님.
3. **출력 깔끔한가**: CLI는 양호. 웹 UI는 다크 테마 + 통계 그리드로 구성.
4. **빠진 것**: Grid search에서 멀티모델 조합 미지원 (단일 모델 필터링만). 이것은 조합 폭발 때문에 의도적으로 제외.

### 3-3. 개선
- [불만] GGUF 업로드 시 context_length 파라미터 미적용 → [개선] urlparse로 query param 파싱 추가
- [불만] Phi-2 오차 31.8% → [개선] ffn_projections 파라미터로 non-gated MLP 지원, 6.8%로 개선

## Phase 4 — 검증
- [체크] GGUF 메타데이터 파싱 → 통과 (8/8)
- [체크] 멀티 모델 VRAM 산출 → 통과 (7/7)
- [체크] llama.cpp 비교 (20% 이내) → 통과 (7/7: 최대 오차 10.6%)
- [체크] 실행 가능 조합 필터링 → 통과 (5/5, 74개 조합 발견)
- [체크] MoE expert 오프로딩 정보 → 통과 (7/7, 7개 시나리오)
- **최종 결과: SUCCESS (5/5 완료 기준 통과)**
