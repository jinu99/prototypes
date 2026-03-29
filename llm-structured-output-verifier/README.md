# LLM 구조화 출력 검증기

> 2-pass 파이프라인으로 LLM 추출 결과의 hallucination을 사전 식별하는 CLI 도구

## Architecture

```
┌──────────────┐     ┌────────────────────┐     ┌─────────────────────┐
│  Source Text  │────▶│  Pass 1: Extract   │────▶│  Structured Output  │
│  (.txt file)  │     │  (Mock LLM/Regex)  │     │  (Pydantic Model)   │
└──────────────┘     └────────────────────┘     └─────────┬───────────┘
                                                          │
                     ┌────────────────────┐               │
                     │  Pass 2: Verify    │◀──────────────┘
                     │  (Field × Source)  │
                     └────────┬───────────┘
                              │
                     ┌────────▼───────────┐
                     │  Evidence Report   │
                     │  • evidence span   │
                     │  • confidence score│
                     │  • hallucination?  │
                     └────────────────────┘
```

## Demo

```
$ uv run python -m src.cli verify test_docs/person_01.txt -s person

╭──────────────────────────── Verification Summary ────────────────────────────╮
│ Schema: person  |  Fields: 7  |  Verified: 5  |  Hallucination candidates: 2 │
│ |  Rate: 29%                                                                 │
╰──────────────────────────────────────────────────────────────────────────────╯

  Field            Value                Confidence   Status
  name             Sarah Chen           0.95         ✓ OK
  age              34                   0.10         ✗ HALLU  ← 원본에 나이 없음
  occupation       Senior ML Engineer   0.95         ✓ OK
  company          DeepMind             0.95         ✓ OK
  education        MIT ... 2018         0.95         ✓ OK
  achievements[0]  Over 20 Papers...    0.95         ✓ OK
  achievements[1]  National Science...  0.10         ✗ HALLU  ← 가짜 수상
```

1-pass vs 2-pass 비교 (5개 문서):
```
$ uv run python -m src.cli compare -d test_docs

  1-pass hallucination detections: 0 (검증 없음)
  2-pass hallucination detections: 4 (age, fake award, fake brand, fake company)
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 단일 문서 2-pass 검증
uv run python -m src.cli verify test_docs/person_01.txt -s person

# 1-pass 추출만 (검증 없음)
uv run python -m src.cli extract test_docs/product_01.txt -s product

# 전체 테스트 문서 1-pass vs 2-pass 비교
uv run python -m src.cli compare -d test_docs
```

스키마 타입: `person`, `product`, `event`

## 구조

```
llm-structured-output-verifier/
├── src/
│   ├── __init__.py
│   ├── models.py      # Pydantic 추출/검증 모델
│   ├── mock_llm.py    # Mock LLM (regex 추출 + 의도적 hallucination)
│   ├── pipeline.py    # 1-pass / 2-pass 파이프라인
│   └── cli.py         # CLI (verify, extract, compare)
├── test_docs/         # 테스트 문서 5개
├── BUILD_LOG.md       # 빌드 일지
├── STATUS.md          # 완료 상태
└── pyproject.toml     # uv 프로젝트 설정
```

## 원본
prototype-pipeline spec: llm-structured-output-verifier
