# RAG Document Quality Diagnosis & Preprocessing Tool

> PDF 문서의 OCR 노이즈(워터마크, 반복 헤더/푸터, 아티팩트)를 자동 감지·제거하여 RAG 파이프라인에 투입할 정제 텍스트를 생성합니다.

## 실행 방법

```bash
# 의존성 설치
uv sync

# 샘플 PDF 생성 (선택)
uv run python generate_samples.py

# 진단 — 노이즈 감지 결과를 JSON으로 출력
uv run rag-doc-cleaner diagnose samples/report_with_watermark.pdf

# 정제 — 노이즈 제거 후 정제 텍스트 출력
uv run rag-doc-cleaner clean samples/report_with_watermark.pdf

# 정제 텍스트를 파일로 저장
uv run rag-doc-cleaner clean samples/report_with_watermark.pdf -o cleaned.txt

# 청킹 통계
uv run rag-doc-cleaner stats samples/report_with_watermark.pdf

# 진단 + 청킹 통계 함께 출력
uv run rag-doc-cleaner diagnose samples/report_with_watermark.pdf --stats
```

## 예시 출력

### `diagnose` — JSON 리포트

```json
{
  "summary": {
    "total_pages": 4,
    "total_blocks": 24,
    "watermarks_found": 1,
    "headers_footers_found": 2,
    "ocr_artifacts_found": 0
  },
  "watermarks": [
    {
      "text": "DRAFT",
      "pages": [1, 2, 3, 4],
      "avg_font_size": 72.0,
      "is_light_color": true
    }
  ],
  "headers_footers": [
    {
      "text_sample": "Acme Corp · Annual Report 2025",
      "zone": "header",
      "pages": [1, 2, 3, 4],
      "pattern": "Acme Corp · Annual Report 2025"
    },
    {
      "text_sample": "Confidential · Do Not Distribute · Page 1",
      "zone": "footer",
      "pages": [1, 2, 3, 4],
      "pattern": "Confidential · Do Not Distribute · Page {n}"
    }
  ],
  "ocr_artifacts": []
}
```

### `clean` — Diff 리포트 + 정제 텍스트

```
Cleaning: samples/report_with_watermark.pdf

--- Changes ---

  Page 1:
    - [watermark] DRAFT
    - [header_footer] Acme Corp · Annual Report 2025
    - [header_footer] Confidential · Do Not Distribute · Page 1
    → 15.7% reduction (504 → 425 chars)

Total items removed: 12

--- Cleaned Text ---

Executive Summary
This report outlines the strategic direction and financial performance of Acme Corp...
```

### `stats` — 청킹 통계

```json
{
  "total_chunks": 4,
  "total_chars": 1481,
  "avg_size": 370.2,
  "min_size": 304,
  "max_size": 425,
  "median_size": 388,
  "size_distribution": {
    "0-100": 0,
    "101-250": 0,
    "251-500": 4,
    "501-1000": 0,
    "1000+": 0
  },
  "duplicate_count": 0,
  "duplicate_rate": 0.0,
  "unique_chunks": 4
}
```

## 구조

```
rag-doc-cleaner/
├── src/rag_doc_cleaner/
│   ├── __init__.py
│   ├── cli.py          # CLI 진입점 (diagnose, clean, stats)
│   ├── extractor.py    # PDF → 위치 정보 포함 텍스트 블록 추출
│   ├── detector.py     # 워터마크·헤더/푸터·OCR 아티팩트 감지
│   ├── cleaner.py      # 노이즈 제거 + diff 리포트
│   └── chunker.py      # 청킹 통계 (크기 분포, 중복률)
├── samples/            # 테스트용 샘플 PDF 3종
├── generate_samples.py # 샘플 PDF 생성 스크립트
├── pyproject.toml
├── BUILD_LOG.md
└── STATUS.md
```

## 감지 방식

| 노이즈 유형 | 감지 전략 |
|---|---|
| 워터마크 | 큰 폰트(≥36pt) + 페이지 중앙 + 다수 페이지 반복 |
| 반복 헤더/푸터 | 페이지 상단/하단 영역 + 페이지 번호 정규화 후 패턴 매칭 |
| OCR 아티팩트 | 특수문자 연속(garbled), UTF-8 깨짐, 스캔 라인 패턴 |

## 원본

prototype-pipeline spec: rag-doc-cleaner
