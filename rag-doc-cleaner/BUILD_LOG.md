# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-01 — Spec 파일 확인 완료
- [판단] 스택 선택: Python + uv + PyMuPDF + argparse
  - 이유: Spec에서 Python + uv 명시. PyMuPDF(fitz)는 PDF 텍스트 블록을 좌표 포함하여 추출 가능 — 워터마크/헤더 위치 기반 감지에 필수. argparse는 표준 라이브러리라 의존성 최소화.
- [판단] 아키텍처: extractor → detector → cleaner → chunker 파이프라인 구조
  - 이유: 각 단계가 독립적이어서 테스트/디버깅 용이. 300줄 제한도 자연스럽게 충족.
- [판단] 테스트 PDF는 PyMuPDF로 직접 생성 (generate_samples.py)
  - 이유: 실제 워터마크/헤더/OCR 아티팩트가 포함된 PDF가 필요하나 외부 파일 의존 불가. 직접 생성하면 감지 로직도 정확히 검증 가능.

## Phase 2 — 구현
- [시도] uv init + uv add pymupdf → [결과] 성공
- [시도] generate_samples.py로 3개 PDF 생성 → [결과] 성공
- [시도] extractor.py 구현 후 테스트 → [결과] 성공 — TextBlock의 y좌표, font_size, color 정확히 추출됨
- [시도] detector.py 구현 → [결과] 성공 — watermark(DRAFT, CONFIDENTIAL), header/footer, OCR artifacts 모두 감지
- [에러] ■□■□■□ 문자가 PyMuPDF에서 ?????? 으로 변환됨 → [수정] RE_REPEATED_QMARK 패턴 추가, scan_line 패턴에 ? 포함
- [시도] cleaner.py + chunker.py + cli.py 구현 → [결과] 성공

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → 솔직히 "오 되네" 수준은 됨. diagnose가 JSON으로 깔끔하게 나오고, clean이 diff 리포트와 정제 텍스트를 잘 분리함.
- [불만 1] JSON 출력에 page 번호가 0-indexed (watermarks.pages)와 1-indexed (ocr_artifacts.page)로 혼재됨 → 통일 필요
- [불만 2] clean 명령의 diff 리포트가 stderr, 정제 텍스트가 stdout으로 분리되긴 했지만, 파일 저장 없이 실행하면 두 스트림이 섞여 보임 — 사용감이 약간 어색
- [불만 3] header의 pattern 필드에서 "X-200"의 200이 {n}으로 치환됨 — 페이지 번호가 아닌데 치환되는 false positive
- [개선] 위 3가지 수정 후 Phase 2로 복귀
- [수정 1] to_dict()에서 pages를 1-indexed로 변환 → 통일됨
- [수정 2] stderr/stdout 분리는 Unix 관례에 부합 — 유지. clean --output 옵션으로 파일 저장 가능.
- [수정 3] _normalize_for_comparison()의 정규식을 개선 — 알파벳/하이픈에 인접한 숫자는 치환하지 않도록 수정. "X-200" 보존, "Page 1" → "Page {n}" 정확히 동작
- [재평가] 3가지 수정 후 전체 재테스트 통과. JSON 깔끔, 패턴 정확, 출력 일관.

## Phase 4 — 기능 검증
- [체크] diagnose 명령 → JSON 리포트 (watermark, header/footer, OCR artifacts) → 통과
- [체크] clean 명령 → 정제 텍스트 + diff 리포트 → 통과
- [체크] 3개 PDF 샘플 감지 정확도 → report(WM+HF), invoice(HF+OCR×6), manual(WM+HF) → 전부 통과
- [체크] 청킹 통계 (크기 분포, 중복률) → stats 명령 및 --stats 플래그 모두 동작 → 통과
- [체크] README 사용법 + 예시 출력 → Phase 5에서 생성 예정
- [결과] 5/5 통과 → SUCCESS
